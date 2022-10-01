from kucoin.client import Client
from keys import keys

API_NAME = 'news_trading'
SPOT_API_KEY = keys.get('SPOT_API_KEY') 
SPOT_API_SECRET = keys.get('SPOT_API_SECRET') 
SPOT_API_PASSPHRASE = keys.get('SPOT_API_PASSPHRASE') 

FUTURES_API_KEY = keys.get('FUTURES_API_KEY') 
FUTURES_API_SECRET = keys.get('FUTURES_API_SECRET') 

class KuCoinClient(object):
    
    def __init__(self):
        self.spot_client = Client(api_key=SPOT_API_KEY, api_secret=SPOT_API_KEY, passphrase=SPOT_API_PASSPHRASE)
        
    def get_spot_currencies(self):
        currencies = self.spot_client.get_currencies()
        return dict([ (c.get('name'), c) for c in currencies])
    
    def get_usdt_price(self, ticker : str) -> float:
        res = self.spot_client.get_ticker(f"{ticker}-USDT")
        return float(res.get('price'))
        
    