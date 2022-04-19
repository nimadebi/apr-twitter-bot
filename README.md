# apr-twitter-bot

Tweets daily APR of Tempus pools. Fetches deployed contracts from https://docs.tempus.finance/docs/deployed-contracts  
  
Requirements can be found in requirements.txt.  
  
  
To initialize:
  
- Generate all twitter api keys/secrets from https://developer.twitter.com/ on the account you want the tweets to be shown. User authentication settings need "OAuth 1.0a" turned on.  
- Fill a .env file with the keys/secrets according to main.py.  
- Change the time at which the tweet should be sent at the bottom of main.py "schedule.every().day.at("20:00").do(toot)".
  
  
To run:  

Files should be sent to AWS, or any server with python.  
Run with python3 main.py  
  
  
  
Notes:  
The maximum character limit of a tweet is 280 characters. So if the amount of pools grow bigger, the tweet text should be changed according to likings, which can also be done easily in main.py.  
Current generated tweet has 225 characters, with every pool being +- 18 chars. So there is still some room left. Next step would be to stop showing the pool names (Lido/Yearn) in the tweet, so only token + percentage. This significantly reduces the tweet length.
