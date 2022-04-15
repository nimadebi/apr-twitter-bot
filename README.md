# apr-twitter-bot

Tweets daily APR of some pools.

Requirements can be found in requirements.txt.  
  
  
To initialize:
- Change the time at which the tweet should be sent at the bottom of main.py "schedule.every().day.at("20:00").do(toot)".
- Add/Remove active pools from the 2D array in main.py "token_contract_addresses = ..".  
  
  
To run:  

Files should be sent to AWS, or any server with python.  
Run with python3 main.py  
  
  
  
Notes:  
The maximum character limit of a tweet is 280 characters. So if the amount of pools grow bigger, the tweet text should be changed according to likings, which can also be done easily in main.py.
