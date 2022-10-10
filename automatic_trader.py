from ast import Str
from exchange_client import MARKET_TYPE, PositionItem, TradeStreamItem, Exchange
import dynamic_config
import logging
from clock import Clock
import time


class AutomaticTrader(object):
    
    def __init__(self, clock : Clock, exchange : Exchange, currency : Str) -> None:
        self.clock = clock
        self.exchange = exchange
        self.currency = currency
        self.market_type : MARKET_TYPE = None
        self.entry_time : int = None
        self.entry_price : float = None
        self.current_price : float = None
        self.max_price : float = None
        self.notifier = None
        self.price_log_interval_s = 5
        self.last_price_log_ts = 0
        
    def log(self, msg : str):
        logging.info(f"{self.exchange.exchange}_{self.market_type.name}({self.currency}): {msg}")
        
        
    def notify(self, msg : str):
        if self.notifier != None:
            m = f"{self.exchange.exchange}_{self.market_type.name}({self.currency}): {msg}"
            self.notifier(m)
    
    
    def price_watcher(self, item : TradeStreamItem):
        price = item.price
        self.current_price = price
        if self.max_price == None or price > self.max_price:
            self.max_price = price
        
        if self.clock.now_s() - self.price_log_interval_s  > self.last_price_log_ts:
            self.log(f"Handling new item. Current price is {price}. Max price is {self.max_price}.") 
            self.last_price_log_ts = self.clock.now_s()
            
        
    def close_position(self, msg : str, stop_loss_id : str):
        self.log(msg)
        self.notify(msg)
        position = self.exchange.get_position(self.currency, self.market_type)
        while position.volume > 0:
            sell_price = self.current_price * dynamic_config.close_position_price_percent()
            sell_order_id = self.exchange.new_sell_order(self.currency, self.market_type, position.volume, sell_price)
            time.sleep(1)
            self.exchange.cancel_order(self.currency, self.market_type, sell_order_id)
            position = self.exchange.get_position(self.currency, self.market_type)
            
        self.log(f"position closed.")
        self.notify(f"pozycja zamknięta.")
        self.exchange.cancel_order(self.currency, self.market_type, stop_loss_id)
        
        
    def up_and_to_the_right(self):
        start_time = self.clock.now_s()
        if self.exchange.has_currency(self.currency, MARKET_TYPE.FUTURES):
            self.market_type = MARKET_TYPE.FUTURES
        elif self.exchange.has_currency(self.currency, MARKET_TYPE.MARGIN):
            self.market_type = MARKET_TYPE.MARGIN
        elif self.exchange.has_currency(self.currency, MARKET_TYPE.SPOT):
            self.market_type = MARKET_TYPE.SPOT
        else:
            logging.info(f"{self.currency} not availabe on {self.exchange.exchange}.")
            return
        
        self.log(f"Running news trade.")
        self.current_price = self.exchange.get_current_price(self.currency, self.market_type)
        self.log(f"Initial price is {self.current_price} USDT")
        if self.market_type != MARKET_TYPE.SPOT:
            self.exchange.transfer_funds(MARKET_TYPE.SPOT, self.market_type)
        initial_funds = min(dynamic_config.max_funds_percentage_per_trade() * self.exchange.get_balance(self.market_type), 
                            dynamic_config.max_initial_funds_per_trade())
        self.notify(f"cena początkowa {self.current_price} USDT. Dostępny kapitał to {initial_funds:.2f} USDT.")

        
        leverage = self.exchange.get_max_leverage(self.currency, self.market_type, initial_funds)
        if leverage > dynamic_config.max_leverage():
            leverage = dynamic_config.max_leverage()
        funds = initial_funds * leverage
        if funds < 10:
            self.log(f"Low funds: {funds}. Bailing.")
            self.notify(f"Za mało środków na koncie: {funds}")
            self.exchange.transfer_funds(self.market_type, MARKET_TYPE.SPOT)
            
        self.log(f"Going to invest up to {funds} USD on trade.")
        limit_price = dynamic_config.open_position_price_percent() * self.current_price
        stop_price = dynamic_config.close_position_price_percent() * self.current_price
        volume = funds / self.current_price
        [limit_order_id, stop_order_id] = self.exchange.new_buy_order(
            self.currency, self.market_type, leverage, volume, limit_price, stop_price)
        self.notify(f"kupuję maksymalnie za {funds:.0f} USDT po cenie {limit_price} USD za sztukę.")
        self.log(f"Sent trades. Limit price = {limit_price}. Stop price = {stop_price}. Waiting 1s for trade to settle.")
        self.exchange.register_market_watcher(self.currency, self.market_type, self.price_watcher)
        time.sleep(1)
        position = self.exchange.get_position(self.currency, self.market_type)
        self.exchange.cancel_order(self.currency, self.market_type, limit_order_id)
        self.log(f"Initial order cancelled.")
        if position.volume > 0:
            self.log(f"Current position is {position}")
            self.notify(f"Udało się kupić za {position.value():.0f} USDT przy cenie {position.open_price} USDT za sztukę.")
        else:
            self.log(f"Position not opened. We are done here.")
            self.notify(f"Nie udało się nic kupić. KONIEC.")
            self.exchange.transfer_funds(self.market_type, MARKET_TYPE.SPOT)
            return
        self.log(f"Waiting {dynamic_config.wait_time_after_initial_trade_s()} seconds for price action")
        time.sleep(dynamic_config.wait_time_after_initial_trade_s())
        
        if self.current_price < position.open_price * dynamic_config.min_percentage_for_the_moon():
            self.close_position(f"KAPISZON. Zamykam pozycje przy cenie {self.current_price}.", stop_order_id)
        else:
            self.log(f"positive price movement. Keeping position.")
            self.notify(f"RAKIETA. Cena wzrosła do {self.current_price}. Wzrost o {(self.current_price / position.open_price - 1) * 100.}%.")
            while self.clock.now_s() - dynamic_config.max_hold_position_duration_s() < start_time:
                gain_percentage = 0
                if (self.max_price - position.open_price) > 0:
                    gain_percentage = (self.current_price - position.open_price) / (self.max_price - position.open_price)
                if gain_percentage < dynamic_config.gain_percentage_to_keep():
                    break
                time.sleep(1)
                
            self.close_position(f"Zamykam pozycje przy cenie {self.current_price}. Wzrost o {(self.current_price / position.open_price - 1) * 100.}%.", 
                                stop_order_id)
            
        self.exchange.transfer_funds(self.market_type, MARKET_TYPE.SPOT)

