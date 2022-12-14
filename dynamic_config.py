import yaml
import threading
import os
import logging
from typing import List

class DynamicConfig(object):
    
    def __init__(self) -> None:
        self.config = {}
        self.__refresh()
        
    def get(self, key : str, default = None):
        return self.config.get(key, default)
        
    def __refresh(self) -> None:
        try:
            with open(os.path.dirname(os.path.abspath(__file__)) + '/dynamic_config.yaml', 'r') as f:
                config = yaml.load(f, Loader=yaml.Loader)
                if f"{self.config}" != f"{config}":
                    logging.info(f"Dynamic config has changed. New config is: {config}")
                self.config = config
        except Exception as e:
            logging.warning(f"Error when reading dynamic config: {e}")
        
        threading.Timer(self.get('config_refresh_interval_s', 60), self.__refresh).start()
        
        
config = DynamicConfig()

def close_position_price_percent() -> float:
    return float(get('close_position_price_percent', 0.995))

def open_position_price_percent() -> float:
    return float(get('open_position_price_percent', 1.02))

def max_funds_per_trade() -> float:
    return float(get('max_funds_per_trade', 10))

def max_funds_percentage_per_trade() -> float:
    return float(get('max_funds_percentage_per_trade', 0.75))

def max_leverage() -> int:
    return int(get('max_leverage', 10))

def wait_time_after_initial_trade_s() -> float:
    return float(get('wait_time_after_initial_trade_s', 30))

def max_hold_position_duration_s() -> float:
    return float(get('max_hold_position_duration_s', 3600))

def gain_percentage_to_keep() -> float:
    return float(get('gain_percentage_to_keep', 0.75))

def min_percentage_for_the_moon() -> float:
    return float(get('min_percentage_for_the_moon', 1.01))

def binance_fetcher_refresh_interval_s() -> float:
    return float(get('binance_fetcher_refresh_interval_s', 0.2))

def coin_info_refresh_interval_s() -> float:
    return float(get('coin_info_refresh_interval_s', 3600))

def top_marketcaps_to_skip() -> int:
    return int(get('top_marketcaps_to_skip', 8))

def token_blacklist() -> List[str]:
    return get('token_blacklist', [])

def get(key : str, default = None):
    return config.get(key, default)
    