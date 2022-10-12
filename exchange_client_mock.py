from mimetypes import init
from threading import Thread
from turtle import pos, position
from exchange_client import Exchange, MARKET_TYPE, PositionItem, TradeStreamItem
import logging
import random
import time
import os


class ExchangeClientMock(Exchange):
    
    def __init__(self) -> None:
        self.balance_per_market_type = {}
        self.market_type = None
        self.currency = None
        self.prices = []
        self.price_cb = None
        self.start_time = None
        self.max_leverage = None
        self.position = None
        self.fill_buy = True
        self.fill_sell_attempts = 1
    
    def run(self):
        
        def background():
            self.start_time = time.time()
            while True:
                elapsed = time.time() - self.start_time
                while len(self.prices) > 1 and self.prices[0][0] < elapsed:
                    if self.price_cb != None:
                        self.price_cb(TradeStreamItem(self.prices[0][1], 122, time.time()))
                    self.prices.pop(0)
                time.sleep(0.1 * random.random())
                
        Thread(target=background).start()
                
                
    
    def set_balance(self, balance_per_market_type):
        self.balance_per_market_type = balance_per_market_type
        
    def set_market_type(self, market_type):
        self.market_type = market_type
        
    def set_currency(self, currency):
        self.currency = currency
        
    def set_prices(self, prices):
        self.prices = prices
        
    def set_max_leverage(self, leverage):
        self.max_leverage = leverage


    @property
    def exchange(self) -> str:
        return "MOCK"
    
    def get_balance(self, market_type : MARKET_TYPE) -> float:
        res = self.balance_per_market_type[market_type]
        logging.info(f"get_balance({market_type})= {res}")
        return res

    def has_currency_in_market_type(self, currency : str, market_type : MARKET_TYPE) -> bool:
        res = currency == self.currency and market_type == self.market_type
        logging.info(f"has_currency_in_market_type({currency}, {market_type}) = {res}")
        return res
    
    def get_current_price(self, currency : str, market : MARKET_TYPE) -> float:
        res = self.prices[0][1]
        logging.info(f"get_current_price({currency}, {market}) = {res}")
        return res
    
    def register_market_watcher(self, currency : str, market : MARKET_TYPE, cb):
        logging.info(f"register_market_watcher({currency}, {market})")
        self.price_cb = cb
    
    def stop_market_watcher(self):
        logging.info(f"stop_market_watcher()")
        self.price_cb = None
    
    def get_max_leverage(self, currency : str, market_type : MARKET_TYPE, initial_funds : float) -> int:
        res = self.max_leverage
        logging.info(f"get_max_leverage({currency}, {market_type}, {initial_funds}) = {res}")
        return res
    
    def new_buy_order(self, currency : str, market_type : MARKET_TYPE, 
                   leverage : int, volume : float, limit_price : float):
        order_id = random.randint(1, 1000)
        order_price = self.prices[0][1] + (limit_price - self.prices[0][1]) * random.random()
        fill_volume = volume
        if not self.fill_buy:
            fill_volume *= 0.5
        self.position = PositionItem(order_price, fill_volume)
        logging.info(f"new_buy_order({currency}, {market_type}, {leverage}, {volume}, {limit_price}) = {self.position}")
        return order_id
    
    def new_sell_order(self, currency : str, market_type : MARKET_TYPE, volume : float, limit_price : float) -> str:
        if volume > self.position.volume:
            logging.warning(f"new_sell_order, position({self.position.volume}) smaller than sell volume({volume})")
            os.abort()
        fill_volume = volume
        if self.fill_sell_attempts > 1:
            fill_volume *= 0.5
            self.fill_sell_attempts -= 1
        fill_price = self.prices[0][1] + (limit_price - self.prices[0][1]) * random.random()
        self.position.volume -= fill_volume
        order_id = random.randint(1, 1000)
        logging.info(f"new_sell_order({currency}, {market_type}, {volume}, {limit_price}) = {self.position}")
        return order_id
    
    def cancel_order(self, currency : str, market_type : MARKET_TYPE, order_id : str):
        logging.info(f"cancel_order({currency}, {market_type}, {order_id})")
    
    def get_position(self, currency : str, market_type : MARKET_TYPE, open_order_id : str) -> PositionItem:
        logging.info(f"get_position({currency}, {market_type}, {open_order_id}) = {self.position}")
        return self.position
    
    def transfer_funds(self, from_market : MARKET_TYPE, to_market : MARKET_TYPE):
        logging.info(f"transfer_funds({from_market}, {to_market})")
        self.balance_per_market_type[to_market] += self.balance_per_market_type[from_market]
    