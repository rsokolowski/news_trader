from kucoin.client import Client
from keys import keys

API_NAME = 'news_trading'
SPOT_API_KEY = keys.get('SPOT_API_KEY') #'6335828f25e651000131fd89'
SPOT_API_SECRET = keys.get('SPOT_API_SECRET') # '5831f0a1-e8ce-4d98-bf03-c894aa19fa3a'
SPOT_API_PASSPHRASE = keys.get('SPOT_API_PASSPHRASE') #'EERGmqdrpfDA7ZV'

FUTURES_API_KEY = keys.get('FUTURES_API_KEY') # '633585d48209b100011843e8'
FUTURES_API_SECRET = keys.get('FUTURES_API_SECRET') # 'a261919f-b327-4374-8db2-caa3c3f875f3'

class KuCoinClient(object):
    
    def __init__(self):
        self.spot_client = Client(api_key=SPOT_API_KEY, api_secret=SPOT_API_KEY, passphrase=SPOT_API_PASSPHRASE)
        
    def get_spot_currencies(self):
        currencies = self.spot_client.get_currencies()
        return dict([ (c.get('name'), c) for c in currencies])
    
    def get_usdt_price(self, ticker : str) -> float:
        res = self.spot_client.get_ticker(f"{ticker}-USDT")
        return float(res.get('price'))
        
    