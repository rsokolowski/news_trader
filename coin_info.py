import keys

from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import logging
from threading import Timer
import dynamic_config


class CoinInfo(object):
    
    def __init__(self) -> None:
        self.coins = {}
        self.__refresh_coins()
        
    def __refresh_coins(self):
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        parameters = {
        'start':'1',
        'limit':'5000',
        'convert':'USD'
        }
        headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': keys.keys.get('coinmarketcap_api_key'),
        }
        session = Session()
        session.headers.update(headers)

        try:
            logging.info(f"Refreshing CoinInfo.")
            response = session.get(url, params=parameters)
            data = json.loads(response.text)
            coins = {}
            for item in data['data']:
                symbol : str = item.get('symbol', None)
                rank = item.get('cmc_rank', 0)
                usd_data = item.get('quote', {}).get('USD', {})
                market_cap = usd_data.get('market_cap', 0)
                if symbol != None and rank != 0 and market_cap != 0 and rank < coins.get(symbol.upper(), {}).get('rank', 10000):
                    coins[symbol.upper()] = {
                        'rank': rank,
                        'market_cap': market_cap
                    }
            self.coins = coins
            logging.info(f"CoinInfo refreshed.")
        except Exception as e:
            logging.warning(f"Error in CoinInfo: {e}")
            
        Timer(dynamic_config.coin_info_refresh_interval_s(), self.__refresh_coins).start()
        
        
info = CoinInfo()
            
        
