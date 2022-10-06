from enum import Enum
import datetime

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
        
    def value(self) -> float:
        return self.volume * self.open_price
        
    def __repr__(self) -> str:
        return f"POSITION: {self.volume}@{self.open_price} USD. Value = {self.value()} USD"
        