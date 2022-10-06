from cmath import log
from re import L
from turtle import pos, position
from keys import keys
import logging
from exchange_client import MARKET_TYPE, TradeStreamItem, PositionItem
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

import binance.error
from binance.um_futures import UMFutures
from binance.spot import Spot
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
import threading
import random
import time
import clock


def convert_binance_trade_stream_item_to_trade_stream_item(item) -> TradeStreamItem:
    return TradeStreamItem(price=float(item['p']), volume=float(item['q']), timestamp=int(item['T'] / 1000))

def convert_binance_position_item_to_position_item(item) -> PositionItem:
    return PositionItem(float(item['entryPrice']), float(item['positionAmt']))

def round_to_precision(v: float, precision : str) -> str:
    tokens = precision.split('.')
    p = float(precision)
    if len(tokens) == 1:
        return str(int(int(v / p) * p))
    dec_points = len(tokens[1])
    v = int(v / p) * p
    v_str = str(v)
    v_str_tokens = v_str.split('.')
    if len(v_str_tokens) == 1:
        return v_str
    else:
        return v_str_tokens[0] + "." + v_str_tokens[1][0:dec_points]
    
    
    
    
    

class BinanceClient(object):
    
    def __init__(self) -> None:
        self.futures_api = UMFutures(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        self.spot_api = Spot(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        self.futures_ws_client = UMFuturesWebsocketClient()
        self.futures_ws_client.start()
        self.available_symbols = {}
        self.futures_leverage_brackets = {}
        self.__refresh_available_symbols()
        
    def exchange(self) -> str:
        return "BINANCE"
        
    def has_symbol(self, symbol : str, market_type = None) -> bool:
        if market_type == None:
            for market_type in MARKET_TYPE:
                if self.has_symbol(symbol, market_type):
                    return True
        else:
            return symbol in self.available_symbols.get(market_type, {}).keys()
        return False
    
    def get_current_price(self, symbol : str, market : MARKET_TYPE) -> float:
        if market == MARKET_TYPE.FUTURES:
            price_item = self.futures_api.mark_price(self.available_symbols[MARKET_TYPE.FUTURES][symbol]['symbol'])
            return float(price_item['indexPrice'])
    
    def register_market_watcher(self, market : MARKET_TYPE, symbol : str, cb):
        def cb_wrapper(item):
            if item.get('e', "") == 'aggTrade':
                cb(convert_binance_trade_stream_item_to_trade_stream_item(item))
            
        if market == MARKET_TYPE.FUTURES:
            self.futures_ws_client.agg_trade(self.available_symbols[MARKET_TYPE.FUTURES][symbol]['symbol'], 10, cb_wrapper)
            
    def get_balance(self):
        
        account = self.futures_api.account()
        return account
        
    def get_max_leverage(self, market_type : MARKET_TYPE, symbol : str, initial_funds : float) -> int:
        if market_type == MARKET_TYPE.FUTURES:
            brackets = self.futures_leverage_brackets.get(symbol, [])
            for bracket in brackets:
                leverage = bracket['initialLeverage']
                cap = initial_funds * leverage
                if cap <= bracket['notionalCap']:
                    return leverage
            return 1
        
    def new_open_trade(self, market_type : MARKET_TYPE, curr : str, leverage : int, volume : float, limit_price : float, stop_price : float):
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][curr]
            symbol = item['symbol']
            tick_size = None
            volume_step = None
            for filter in item['filters']:
                if filter['filterType'] == 'PRICE_FILTER':
                    tick_size = filter['tickSize']
                elif filter['filterType'] == 'LOT_SIZE':
                    volume_step = filter['stepSize']
            volume = round_to_precision(volume, volume_step)
            limit_price = round_to_precision(limit_price, tick_size)
            stop_price = round_to_precision(stop_price, tick_size)
            resp = self.futures_api.change_leverage(symbol, leverage)
            limit_order_id = f"{symbol}_initial_trade"
            stop_order_id = f"{symbol}_stop_loss"
            limit_order = self.futures_api.new_order(symbol, "BUY", "LIMIT", timeInForce="GTC", 
                 quantity=volume, price=limit_price, newClientOrderId=limit_order_id)
            stop_order = self.futures_api.new_order(symbol, "SELL", "STOP_MARKET", timeInForce="GTE_GTC", 
                 quantity=volume, stopPrice=stop_price, newClientOrderId=stop_order_id,
                 workingType="MARK_PRICE", reduceOnly=True)
            return [limit_order_id, stop_order_id]
        
        
    def new_close_trade(self, market_type : MARKET_TYPE, curr : str, volume : float, limit_price : float):
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][curr]
            symbol = item['symbol']
            tick_size = None
            volume_step = None
            for filter in item['filters']:
                if filter['filterType'] == 'PRICE_FILTER':
                    tick_size = filter['tickSize']
                elif filter['filterType'] == 'LOT_SIZE':
                    volume_step = filter['stepSize']
            volume = round_to_precision(volume, volume_step)
            limit_price = round_to_precision(limit_price, tick_size)
            close_trade_id = f"{symbol}_close_trade"
            limit_order = self.futures_api.new_order(symbol, "SELL", "LIMIT", timeInForce="GTC", 
                 quantity=volume, price=limit_price, newClientOrderId=close_trade_id, reduceOnly=True)
            return close_trade_id
        
    def cancel_order(self, market_type : MARKET_TYPE, curr : str, order_id : str):
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][curr]
            symbol = item['symbol']
            try:
                resp = self.futures_api.cancel_order(symbol=symbol, origClientOrderId=order_id)
            except binance.error.ClientError as e:
                if e.error_code != -2011 and e.error_message != "'Unknown order sent.'":
                    raise(e)
                else:
                    return None
            return resp
            
        
        
    def get_position(self, market_type : MARKET_TYPE, curr : str) -> PositionItem:
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][curr]
            symbol = item['symbol']
            resp = self.futures_api.get_position_risk(symbol=symbol)
            return convert_binance_position_item_to_position_item(resp[0])
            

        
    def __refresh_available_symbols(self) -> None:
        logging.info(f"Refreshing available symbols in Binance")
        futures_symbols = {}
        exchange_info = self.futures_api.exchange_info()
        for symbol in exchange_info.get('symbols', []):
            if symbol['status'] == 'TRADING' and symbol['contractType'] == 'PERPETUAL' and symbol['pair'].endswith('USDT'):
                s = symbol['pair'][0:-4]
                futures_symbols[s] = symbol
        leverage_brackets = self.futures_api.leverage_brackets()
        futures_leverage_brackets = {}
        for item in leverage_brackets:
            symbol = item['symbol']
            if symbol.endswith('USDT') and symbol[0:-4] in futures_symbols.keys():
                futures_leverage_brackets[symbol[0:-4]] = item['brackets']
        self.futures_leverage_brackets = futures_leverage_brackets
        
        self.available_symbols[MARKET_TYPE.FUTURES] = futures_symbols
        
        logging.info(f"Available symbols in Binance have been refreshed")
        
        threading.Timer(interval=10 * 60, function=self.__refresh_available_symbols).start()
        
        
def market_watcher(item : TradeStreamItem):
    logging.info(f"ITEM: {item}")


MAX_BASE_FUNDS_PER_TRADE = 500
INITIAL_WAIT_TIME_AFTER_OPEN_TRADE_SECONDS = 30
GAIN_PERCENTAGE_TO_KEEP = 0.8 # 80% do zatrzymania
MAX_POSITION_HOLD_DURATION_S = 3600 # 1h

class PositionManager(object):
    
    def __init__(self, clk : clock.Clock, symbol : str, market_type : MARKET_TYPE, client : BinanceClient):
        self.clk = clk
        self.symbol = symbol
        self.client = client
        self.market_type : MARKET_TYPE = market_type
        self.entry_time : int = None
        self.entry_price : float = None
        self.current_price : float = None
        self.max_price : float = None
        self.notifier = None
        self.price_log_interval_s = 5
        self.last_price_log_ts = 0
        
    def notify(self, msg : str):
         if self.notifier != None:
             self.notifier(msg)
        
        
    
    def symbol_watcher(self, item : TradeStreamItem):
        price = item.price
        self.current_price = price
        if self.max_price == None or price > self.max_price:
            self.max_price = price
        
        if self.clk.now() - self.price_log_interval_s * 1000 > self.last_price_log_ts:
            logging.info(f"Handling new item. Current price is {price}. Max price is {self.max_price}.") 
            self.last_price_log_ts = self.clk.now()
            
        
    def close_position(self):
        position = self.client.get_position(self.market_type, self.symbol)
        while position.volume > 0:
            sell_price = self.current_price * 0.995
            close_trade_id = self.client.new_close_trade(self.market_type, self.symbol, position.volume, sell_price)
            time.sleep(1)
            self.client.cancel_order(self.market_type, self.symbol, close_trade_id)
            position = self.client.get_position(self.market_type, self.symbol)


        
        
    def up_and_to_the_right(self):
        start_time = self.clk.now()
        ref = f"{self.client.exchange()}_{self.market_type.name}"
        if self.client.has_symbol(self.symbol, market_type=self.market_type):
            logging.info(f"{ref}: Running news trade.")
            self.current_price = self.client.get_current_price(self.symbol, self.market_type)
            logging.info(f"{ref}: Initial price is {self.current_price}")
            self.notify(f"{ref}({self.symbol}): cena początkowa {self.current_price} USDT.")
            leverage = self.client.get_max_leverage(self.market_type, self.symbol, MAX_BASE_FUNDS_PER_TRADE)
            if leverage > 10:
                leverage = 10
            funds = MAX_BASE_FUNDS_PER_TRADE * leverage
            logging.info(f"{ref}: Going to invest up to {funds} USD on {self.symbol} trade.")
            limit_price = 1.02 * self.current_price
            stop_price = 0.99 * self.current_price
            volume = funds / self.current_price
            [limit_order_id, stop_order_id] = self.client.new_open_trade(
                MARKET_TYPE.FUTURES, self.symbol, leverage, volume, limit_price, stop_price)
            self.notify(f"{ref}: kupuję maksymalnie za {funds} USDT po cenie {limit_price} USD za sztukę.")
            logging.info(f"{ref}: Sent trades. Limit price = {limit_price}. Stop price = {stop_price}. Waiting 1s for trade to settle.")
            self.client.register_market_watcher(MARKET_TYPE.FUTURES, self.symbol, self.symbol_watcher)
            time.sleep(1)
            position = self.client.get_position(MARKET_TYPE.FUTURES, self.symbol)
            self.client.cancel_order(MARKET_TYPE.FUTURES, self.symbol, limit_order_id)
            logging.info(f"{ref}: Initial order cancelled.")
            if position.volume > 0:
                logging.info(f"{ref}: Current position is {position}")
                self.notify(f"{ref}: Udało się kupić za {position.value()} USDT przy cenie {position.open_price} USDT za sztukę.")
            else:
                logging.info(f"{ref}: Position not opened. We are done here.")
                self.notify(f"{ref}: Nie udało się nic kupić. KONIEC.")
                return
            logging.info(f"{ref}: Waiting {INITIAL_WAIT_TIME_AFTER_OPEN_TRADE_SECONDS} seconds for price action")
            time.sleep(INITIAL_WAIT_TIME_AFTER_OPEN_TRADE_SECONDS)
            
            if self.current_price < position.open_price * 1.01:
                logging.info(f"{ref}: Slow price action. Closing position at price {self.current_price}.")
                self.notify(f"{ref}: KAPISZON. Zamykam pozycje przy cenie {self.current_price}.")
                self.close_position()
                logging.info(f"{ref}: position closed.")
                self.notify(f"{ref}: pozycja zamknięta.")
                self.client.cancel_order(MARKET_TYPE.FUTURES, self.symbol, stop_order_id)
                return
            
            logging.info(f"{ref}: positive price movement. Keeping position.")
            self.notify(f"{ref}: RAKIETA. Cena wzrosła do {self.current_price}. Wzrost o {(self.current_price / position.open_price - 1) * 100.}%.")
            while self.clk.now() - MAX_POSITION_HOLD_DURATION_S * 1000 < start_time:
                max_gain_percentage = 0
                if (self.max_price - position.open_price) > 0:
                    max_gain_percentage = (self.current_price - position.open_price) / (self.max_price - position.open_price)
                if max_gain_percentage < GAIN_PERCENTAGE_TO_KEEP:
                    logging.info(f"{ref}: closing position due to rebound.")
                    self.notify(f"{ref}: Zamykam pozycje przy cenie {self.current_price}. Wzrost o {(self.current_price / position.open_price - 1) * 100.}%.")
                    self.close_position()
                    logging.info(f"{ref}: position closed.")
                    self.notify(f"{ref}: pozycja zamknięta.")
                    self.client.cancel_order(MARKET_TYPE.FUTURES, self.symbol, stop_order_id)
                    return
                time.sleep(1)
                
            logging.info(f"{ref}: closing position due to expiry.")
            self.notify(f"{ref}: Zamykam pozycje przy cenie {self.current_price}. Wzrost o {(self.current_price / position.open_price - 1) * 100.}%.")
            self.close_position()
            logging.info(f"{ref}: position closed.")
            self.notify(f"{ref}: pozycja zamknięta.")
            self.client.cancel_order(MARKET_TYPE.FUTURES, self.symbol, stop_order_id)

        else:
            self.notify(f"{ref}: {self.symbol} jest niedostępny do tradingu.")
            logging.info(f"{self.symbol} not available on {ref}.")
            
            
            
            
        
        
        

