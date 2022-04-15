from dotenv import load_dotenv
from web3 import Web3
import schedule
import tweepy
import json
import time
import os

load_dotenv()

infura_url = os.getenv("INFURA")
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

web3_eth = Web3(Web3.HTTPProvider(infura_url))
web3_ftm = Web3(Web3.HTTPProvider("https://rpc.ftm.tools/"))

# [Chain, Pool name (starting with ticker), pool address, AMM address]
# https://docs.tempus.finance/docs/deployed-contracts
token_contract_addresses = [["ETH", "$ETH Lido Pool", "0x0697B0a2cBb1F947f51a9845b715E9eAb3f89B4F", "0x200e41BE620928351F98Da8031BAEB7BD401a129"],
                            ["ETH", "$USDC Yearn Pool", "0x443297DE16C074fDeE19d2C9eCF40fdE2f5F62C2", "0x811f4F0241A9A4583C052c08BDA7F6339DBb13f7"],
                            ["ETH", "$DAI Yearn Pool", "0x7e0fc07280f47bac3D55815954e0f904c86f642E", "0x7cA043143C6e30bDA28dDc7322d7951F538D75e8"],
                            ["FTM", "$DAI Yearn Pool", "0x9c0273E4abB665ce156422a75F5a81db3c264A23", "0x354090dd4f695D7dc5ad492e48d0f30042Ed7BbE"],
                            ["FTM", "$USDT Yearn Pool", "0xE9b557f9766Fb20651E3685374cd1DF6f977d36B", "0x54b28166026e8dd13bf07c46da6ef754a6b80989"],
                            ["FTM", "$USDC Yearn Pool", "0x943B73d3B7373de3e5Dd68f64dbf85E6F4f56c9E", "0x8DCf7e47d7c285e11E48a78dFDDaEc5c48887AF8"],
                            ["FTM", "$WETH Yearn Pool", "0xA9C549aeFa21ee6e79bEFCe91fa0E16a9C7d585a", "0x51B21368396cb76A348E995D698960F8fe44DeF1"],
                            ["FTM", "$YFI Yearn Pool", "0xAE7E5242eb52e8a592605eE408268091cC8794b8", "0x4B137DD01a7Dc7c3Bc12d51b42a00030B6561340"]]

with open("abi/TempusPool.json") as f:
    ABI_pool = json.load(f)

with open("abi/Stats.json") as f:
    ABI_stats = json.load(f)

stats_address_ethereum = Web3.toChecksumAddress('0xe552369a1b109b1eeebf060fcb6618f70f9131f7')
stats_contract_ethereum = web3_eth.eth.contract(stats_address_ethereum, abi=ABI_stats)

stats_address_fantom = Web3.toChecksumAddress('0x7008d1f94088c8AA012B4F370A4fe672ad592Ee3')
stats_contract_fantom = web3_ftm.eth.contract(stats_address_fantom, abi=ABI_stats)

def toot():
    txt_top = "Current fixed APR's on app.tempus.finance\n"
    txt_eth = "\nEthereum: \n"
    txt_ftm = "\nFantom: \n"

    tweet = ""

    for i in token_contract_addresses:
        chain = i[0]
        pool_name = i[1]
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
            txt_eth += pool_name + ": " + str(round(apr, 2)) + "%\n"
        else:
            txt_ftm += pool_name + ": " + str(round(apr, 2)) + "%\n"

    tweet += txt_top + txt_eth + txt_ftm
    print(tweet)
    response = client.create_tweet(text=tweet, user_auth=True)
    print(f"https://twitter.com/user/status/{response.data['id']}")

    return

  
schedule.every().day.at("20:00").do(toot)

while True:
    schedule.run_pending()
    time.sleep(60)

