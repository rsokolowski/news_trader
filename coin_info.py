import keys

from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import logging
from threading import Timer
import dynamic_config
import os
from pathlib import Path

COIN_INFO_JSON = Path(os.path.dirname(os.path.abspath(__file__))).joinpath('coin_info.json')


class CoinInfo(object):
    
    def __init__(self) -> None:
        self.coins = {}
        try:
            with open(COIN_INFO_JSON) as d:
                self.coins = json.load(d) 
                Timer(dynamic_config.coin_info_refresh_interval_s(), self.__refresh_coins).start()
                logging.info("CoinInfo read from file.")
        except Exception as e:
            logging.info("Failed to read CoinInfo from file. Fetching from coinamrketcap.")
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
                if symbol != None and rank != 0 and rank < coins.get(symbol.upper(), {}).get('rank', 10000):
                    coins[symbol.upper()] = {
                        'rank': rank,
                        'market_cap': market_cap
                    }
            self.coins = coins
            with open(COIN_INFO_JSON, "w") as d:
                json.dump(self.coins, d)
            
            logging.info(f"CoinInfo refreshed.")
        except Exception as e:
            logging.warning(f"Error in CoinInfo: {e}")
            
        Timer(dynamic_config.coin_info_refresh_interval_s(), self.__refresh_coins).start()
        
        
info = CoinInfo()
            
        
