from cmath import log
from re import L
from turtle import pos, position
from keys import keys
import logging
from exchange_client import MARKET_TYPE, TradeStreamItem, PositionItem, Exchange
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

import binance.error
from binance.um_futures import UMFutures
from binance.spot import Spot
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
import threading
from typing import List
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
    
    


    

class BinanceClient(Exchange):
    
    def __init__(self) -> None:
        self.futures_api = UMFutures(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        self.spot_api = Spot(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        self.futures_ws_client = UMFuturesWebsocketClient()
        self.futures_ws_client.start()
        self.available_symbols = {}
        self.futures_leverage_brackets = {}
        self.__refresh_available_symbols()
        
        
    def get_balance(self, market_type : MARKET_TYPE) -> float:
        if market_type == MARKET_TYPE.FUTURES:
            account = self.futures_api.account()
            for asset in account['assets']:
                if asset['asset'] == "USDT":
                    return float(asset['availableBalance'])
        elif market_type == MARKET_TYPE.MARGIN:
            account = self.spot_api.margin_account()
            for asset in account['userAssets']:
                if asset['asset'] == 'USDT':
                    return float(asset['free'])
        elif market_type == MARKET_TYPE.SPOT:
            account = self.spot_api.account()
            for balance in account['balances']:
                if balance['asset'] == "USDT":
                    return float(balance['free'])

        return 0
    
    
    def transfer_funds(self, from_market : MARKET_TYPE, to_market : MARKET_TYPE):
        if from_market == MARKET_TYPE.SPOT and to_market == MARKET_TYPE.FUTURES:
            self.spot_api.futures_transfer('USDT', int(self.get_balance(from_market)), 1)
        elif from_market == MARKET_TYPE.SPOT and to_market == MARKET_TYPE.MARGIN:
            self.spot_api.margin_transfer('USDT', int(self.get_balance(from_market)), 1)
        if from_market == MARKET_TYPE.FUTURES and to_market == MARKET_TYPE.SPOT:
            self.spot_api.futures_transfer('USDT', int(self.get_balance(from_market)), 2)
        elif from_market == MARKET_TYPE.MARGIN and to_market == MARKET_TYPE.SPOT:
            self.spot_api.margin_transfer('USDT', int(self.get_balance(from_market)), 2)      
        
          
        
    @property
    def exchange(self) -> str:
        return "BINANCE"
    
    def has_currency_in_market_type(self, currency : str, market_type : MARKET_TYPE) -> bool:
        return currency in self.available_symbols.get(market_type, {}).keys()

    def get_current_price(self, currency : str, market : MARKET_TYPE) -> float:
        if market == MARKET_TYPE.FUTURES:
            price_item = self.futures_api.mark_price(self.available_symbols[MARKET_TYPE.FUTURES][currency]['symbol'])
            return float(price_item['indexPrice'])
    
    def register_market_watcher(self, currency : str, market : MARKET_TYPE, cb):
        def cb_wrapper(item):
            if item.get('e', "") == 'aggTrade':
                cb(convert_binance_trade_stream_item_to_trade_stream_item(item))
            
        if market == MARKET_TYPE.FUTURES:
            self.futures_ws_client.agg_trade(self.available_symbols[market][currency]['symbol'], 10, cb_wrapper)
            

        
    def get_max_leverage(self, currency : str, market_type : MARKET_TYPE, initial_funds : float) -> int:
        if market_type == MARKET_TYPE.FUTURES:
            brackets = self.futures_leverage_brackets.get(currency, [])
            for bracket in brackets:
                leverage = bracket['initialLeverage']
                cap = initial_funds * leverage
                if cap <= bracket['notionalCap']:
                    return leverage
            return 1
        
    def new_buy_order(self, currency : str, market_type : MARKET_TYPE, 
                      leverage : int, volume : float, limit_price : float, stop_price : float) -> List[str]:
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][currency]
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
        
        
    def new_sell_order(self, currency : str, market_type : MARKET_TYPE, volume : float, limit_price : float) -> str:
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][currency]
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
        
    def cancel_order(self, currency : str, market_type : MARKET_TYPE, order_id : str):
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][currency]
            symbol = item['symbol']
            try:
                resp = self.futures_api.cancel_order(symbol=symbol, origClientOrderId=order_id)
            except binance.error.ClientError as e:
                if e.error_code != -2011 and e.error_message != "'Unknown order sent.'":
                    raise(e)
                else:
                    return None
            return resp
            
        
        
    def get_position(self, currency : str, market_type : MARKET_TYPE) -> PositionItem:
        if market_type == MARKET_TYPE.FUTURES:
            item = self.available_symbols[market_type][currency]
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
        



            
            
            
            
        
        
        

