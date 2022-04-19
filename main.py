from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from web3 import Web3
import schedule
import requests
import tweepy
import json
import time
import os

load_dotenv()

alchemy_url = os.getenv("ALCHEMY")
bearer = os.getenv("BEARER")
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token_key = os.getenv("ACCESS_TOKEN_KEY")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

client = tweepy.Client(bearer_token=bearer,
                       access_token=access_token_key,
                       access_token_secret=access_token_secret,
                       consumer_key=consumer_key,
                       consumer_secret=consumer_secret,
                       wait_on_rate_limit=True)

SECONDS_IN_A_DAY = 86400
DAYS_IN_A_YEAR = 365

web3_eth = Web3(Web3.HTTPProvider(alchemy_url))
web3_ftm = Web3(Web3.HTTPProvider("https://rpc.ftm.tools/"))

def fetch_addresses():
    """
        https://docs.tempus.finance/docs/deployed-contracts

        data-block-content = 4b73fba9d14642158569f01e4e46b4f3 = ethereum
        data-block-content = a9c94bb382644c6dac4dcd369d0a8d25 = fantom

        We're first fetching the table blocks (all rows) and then iterating through the columns.
        Format addresses as: [Chain, Pool name (starting with ticker), pool address, AMM address]
    """
    page = requests.get("https://docs.tempus.finance/docs/deployed-contracts")
    soup = BeautifulSoup(page._content, 'html.parser')

    eth_table = soup.select('div[data-block-content="4b73fba9d14642158569f01e4e46b4f3"] '
                            'div[data-rnw-int-class="table-row____"]')
    ftm_table = soup.select('div[data-block-content="a9c94bb382644c6dac4dcd369d0a8d25"] '
                            'div[data-rnw-int-class="table-row____"]')

    addresses = get_data_from_table(eth_table, "ETH") + get_data_from_table(ftm_table, "FTM")

    addresses = remove_matured_pools(addresses)

    return addresses

def get_data_from_table(table, chain):
    data = []
    for row in table:
        column_data = []
        column_data.append(chain)
        for column in row:
            column_data.append(column.text)

        data.append(column_data)

    return data

def remove_matured_pools(addresses):
    add = addresses
    today = datetime.now().date()
    for i in add:
        parsed_date = i[1].split("(")[1].split(")")[0].replace("matures", "").strip()
        maturity_date = datetime.strptime(parsed_date, "%d %B %Y").date()
        if maturity_date < today:
            add.remove(i)

    return add

with open("abi/TempusPool.json") as f:
    ABI_pool = json.load(f)

with open("abi/Stats.json") as f:
    ABI_stats = json.load(f)

token_contract_addresses = fetch_addresses()

stats_address_ethereum = Web3.toChecksumAddress('0xe552369a1b109b1eeebf060fcb6618f70f9131f7')
stats_contract_ethereum = web3_eth.eth.contract(stats_address_ethereum, abi=ABI_stats)

stats_address_fantom = Web3.toChecksumAddress('0x7008d1f94088c8AA012B4F370A4fe672ad592Ee3')
stats_contract_fantom = web3_ftm.eth.contract(stats_address_fantom, abi=ABI_stats)

def toot():
    txt_top = "Current fixed APR's on app.tempus.finance\n"
    txt_eth = "\nEthereum Pools: \n"
    txt_ftm = "\nFantom Pools: \n"

    tweet = ""

    for i in token_contract_addresses:
        chain = i[0]
        pool_name = i[1].split('Pool')[0]  # Removing maturity date to shorten the pool name so it fits in one tweet.
        tempus_pool_address = Web3.toChecksumAddress(i[2])
        tempus_amm_address = Web3.toChecksumAddress(i[3])

        if chain == "ETH":
            tempus_pool_contract = web3_eth.eth.contract(tempus_pool_address, abi=ABI_pool)
        else:
            tempus_pool_contract = web3_ftm.eth.contract(tempus_pool_address, abi=ABI_pool)

        tempus_pool_start_time = tempus_pool_contract.functions.startTime().call()
        tempus_pool_maturity_time = tempus_pool_contract.functions.maturityTime().call()
        pool_duration_in_seconds = (tempus_pool_maturity_time - tempus_pool_start_time)

        scale_factor = (SECONDS_IN_A_DAY * DAYS_IN_A_YEAR) / pool_duration_in_seconds

        token_amount = tempus_pool_contract.functions.backingTokenONE().call()
        is_backing_token = True
        if chain == "ETH":
            principals = stats_contract_ethereum.functions.estimatedDepositAndFix\
                (tempus_amm_address, token_amount, is_backing_token).call()

            estimated_minted_shares = stats_contract_ethereum.functions.estimatedMintedShares\
                (tempus_pool_address, token_amount, is_backing_token).call()
        else:
            principals = stats_contract_fantom.functions.estimatedDepositAndFix\
                (tempus_amm_address, token_amount, is_backing_token).call()

            estimated_minted_shares = stats_contract_fantom.functions.estimatedMintedShares\
                (tempus_pool_address, token_amount, is_backing_token).call()

        ratio = principals / estimated_minted_shares
        pure_interest = ratio - 1

        apr = (pure_interest * scale_factor)*100
        if chain == "ETH":
            txt_eth += "$" + pool_name + ": " + str(round(apr, 2)) + "%\n"
        else:
            txt_ftm += "$" + pool_name + ": " + str(round(apr, 2)) + "%\n"

    tweet += txt_top + txt_eth + txt_ftm
    print(tweet)
    response = client.create_tweet(text=tweet, user_auth=True)
    print(f"https://twitter.com/user/status/{response.data['id']}")

    return


schedule.every().day.at("20:00").do(toot)
#schedule.every(1).minutes.do(toot)

while True:
    schedule.run_pending()
    time.sleep(60)

