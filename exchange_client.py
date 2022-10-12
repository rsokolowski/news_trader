from enum import Enum
import datetime
from abc import ABC, abstractmethod
from typing import List

class MARKET_TYPE(Enum):
    SPOT = 1
    MARGIN = 2
    FUTURES = 3
    
class TradeStreamItem(object):
    
    def __init__(self, price : float, volume : float, timestamp : int):
        self.price = price
        self.volume = volume
        self.timestamp = timestamp
        
    def __repr__(self) -> str:
        return f"TRADE({datetime.datetime.fromtimestamp(self.timestamp)}): {self.volume}@{self.price} USD"
    
class PositionItem(object):
    
    def __init__(self, open_price : float, volume : float):
        self.open_price = open_price
        self.volume = volume
    
    @property  
    def value(self) -> float:
        return self.volume * self.open_price
        
    def __repr__(self) -> str:
        return f"POSITION: {self.volume}@{self.open_price} USD. Value = {self.value} USD"
    
    
class Exchange(ABC):
    
    @property
    @abstractmethod
    def exchange(self) -> str:
        pass
    
    @abstractmethod
    def get_balance(self, market_type : MARKET_TYPE) -> float:
        pass
    
    
    def has_currency(self, currency : str, market_type = None) -> bool:
        if market_type == None:
            for market_type in MARKET_TYPE:
                if self.has_currency(currency, market_type):
                    return True
            return False
        else:
            return self.has_currency_in_market_type(currency, market_type)
    
    
    @abstractmethod
    def has_currency_in_market_type(self, currency : str, market_type : MARKET_TYPE) -> bool:
        pass
    
    @abstractmethod
    def get_current_price(self, currency : str, market : MARKET_TYPE) -> float:
        pass
    
    @abstractmethod
    def register_market_watcher(self, currency : str, market : MARKET_TYPE, cb):
        pass
    
    @abstractmethod
    def stop_market_watcher(self):
        pass
    
    @abstractmethod
    def get_max_leverage(self, currency : str, market_type : MARKET_TYPE, initial_funds : float) -> int:
        pass
    
    @abstractmethod
    def new_buy_order(self, currency : str, market_type : MARKET_TYPE, 
                   leverage : int, volume : float, limit_price : float) -> str:
        pass
    
    @abstractmethod
    def new_sell_order(self, currency : str, market_type : MARKET_TYPE, volume : float, limit_price : float) -> str:
        pass
    
    @abstractmethod
    def cancel_order(self, currency : str, market_type : MARKET_TYPE, order_id : str):
        pass
    
    @abstractmethod
    def get_position(self, currency : str, market_type : MARKET_TYPE, open_order_id : str) -> PositionItem:
        pass
    
    @abstractmethod
    def transfer_funds(self, from_market : MARKET_TYPE, to_market : MARKET_TYPE):
        pass
    
    

        