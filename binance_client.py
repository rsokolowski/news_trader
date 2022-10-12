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
from binance.websocket.websocket_client import BinanceWebsocketClient
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
    
def round_volume(volume : float, filters) -> str:
    volume_step = None
    for filter in filters:
        if filter['filterType'] == 'LOT_SIZE':
            volume_step = filter['stepSize']
            break
    return round_to_precision(volume, volume_step)

def round_price(price : float, filters) -> str:
    tick_size = None
    for filter in filters:
        if filter['filterType'] == 'PRICE_FILTER':
            tick_size = filter['tickSize']
            break
    return round_to_precision(price, tick_size)



class BinanceClient(Exchange):
    
    def __init__(self) -> None:
        self.futures_api = UMFutures(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        self.spot_api = Spot(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        self.futures_ws_client : UMFuturesWebsocketClient = None
        self.spot_ws_client : BinanceWebsocketClient = None
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
    
    def __repay_margin_loan(self):
        to_repay = 0
        assets = self.spot_api.margin_account()
        for asset in assets['userAssets']:
            if asset['asset'] == 'USDT':
                to_repay = float(asset['borrowed']) + float(asset['interest'])

        if to_repay > 0:
            logging.info(f"Repaying margin: {to_repay} USDT")
            self.spot_api.margin_repay("USDT", round_to_precision(to_repay, "0.00000001"))
            
    def __get_margin_loan(self):
        max_borrowable = float(self.spot_api.margin_max_borrowable("USDT")['amount'])
        if max_borrowable > 0:
            logging.info(f"Taking marging loan: {max_borrowable} USDT")
            self.spot_api.margin_borrow("USDT", round_to_precision(max_borrowable, "0.00000001"))

    def transfer_funds(self, from_market : MARKET_TYPE, to_market : MARKET_TYPE):
        if from_market == MARKET_TYPE.SPOT and to_market == MARKET_TYPE.FUTURES:
            self.spot_api.futures_transfer('USDT', int(self.get_balance(from_market)), 1)
        elif from_market == MARKET_TYPE.SPOT and to_market == MARKET_TYPE.MARGIN:
            self.spot_api.margin_transfer('USDT', int(self.get_balance(from_market)), 1)
            self.__get_margin_loan()
        if from_market == MARKET_TYPE.FUTURES and to_market == MARKET_TYPE.SPOT:
            self.spot_api.futures_transfer('USDT', int(self.get_balance(from_market)), 2)
        elif from_market == MARKET_TYPE.MARGIN and to_market == MARKET_TYPE.SPOT:
            self.__repay_margin_loan()
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
        elif market in [MARKET_TYPE.SPOT, MARKET_TYPE.MARGIN]:
            price_item = self.spot_api.ticker_price(symbol=f"{currency}USDT")
            return float(price_item['price'])
        
    
    def register_market_watcher(self, currency : str, market : MARKET_TYPE, cb):
        def cb_wrapper(item):
            if item.get('e', "") == 'aggTrade':
                cb(convert_binance_trade_stream_item_to_trade_stream_item(item))
            
        if market == MARKET_TYPE.FUTURES:
            if self.futures_ws_client == None:
                self.futures_ws_client = UMFuturesWebsocketClient()
                self.futures_ws_client.start()
            self.futures_ws_client.agg_trade(self.available_symbols[market][currency]['symbol'], 10, cb_wrapper)
        elif market in [MARKET_TYPE.SPOT, MARKET_TYPE.MARGIN]:
            if self.spot_ws_client == None:
                self.spot_ws_client = BinanceWebsocketClient("wss://stream.binance.com:9443")
                self.spot_ws_client.start()
            self.spot_ws_client.instant_subscribe(f"{currency.lower()}usdt@aggTrade", cb_wrapper)
            
    def stop_market_watcher(self):
        if self.futures_ws_client != None:
            self.futures_ws_client.close()
            self.futures_ws_client = None
        if self.spot_ws_client != None:
            self.spot_ws_client.close()
            self.spot_ws_client = None
        
    def get_max_leverage(self, currency : str, market_type : MARKET_TYPE, initial_funds : float) -> int:
        
        if market_type == MARKET_TYPE.FUTURES:
            brackets = self.futures_leverage_brackets.get(currency, [])
            for bracket in brackets:
                leverage = bracket['initialLeverage']
                cap = initial_funds * leverage
                if cap <= bracket['notionalCap']:
                    return leverage
            return 1
        if market_type in [MARKET_TYPE.SPOT, MARKET_TYPE.MARGIN]:
            return 1
        
    def new_buy_order(self, currency : str, market_type : MARKET_TYPE, 
                      leverage : int, volume : float, limit_price : float) -> List[str]:
        item = self.available_symbols[market_type][currency]
        symbol = item['symbol']
        volume = round_volume(volume, item['filters'])
        limit_price = round_price(limit_price, item['filters'])
        limit_order = None
        
        if market_type == MARKET_TYPE.FUTURES:
            resp = self.futures_api.change_leverage(symbol, leverage)
            limit_order = self.futures_api.new_order(symbol, "BUY", "LIMIT", timeInForce="GTC", 
                 quantity=volume, price=limit_price)
        elif market_type == MARKET_TYPE.MARGIN:
            limit_order = self.spot_api.new_margin_order(
                symbol, side="BUY", type="LIMIT", timeInForce="GTC", 
                quantity=volume, price=limit_price)
        elif market_type == MARKET_TYPE.SPOT:
            limit_order = self.spot_api.new_order(
                symbol, side="BUY", type="LIMIT", timeInForce="GTC", 
                quantity=volume, price=limit_price)
                
        return limit_order['orderId']

        
        
    def new_sell_order(self, currency : str, market_type : MARKET_TYPE, volume : float, limit_price : float) -> str:
        item = self.available_symbols[market_type][currency]
        symbol = item['symbol']
        volume = round_volume(volume, item['filters'])
        limit_price = round_price(limit_price, item['filters'])
        limit_order = None
        if market_type == MARKET_TYPE.FUTURES:
            limit_order = self.futures_api.new_order(symbol, "SELL", "LIMIT", timeInForce="GTC", 
                 quantity=volume, price=limit_price, reduceOnly=True)
        elif market_type == MARKET_TYPE.MARGIN:
            limit_order = self.spot_api.new_margin_order(
                symbol, side="SELL", type="LIMIT", timeInForce="GTC", 
                quantity=volume, price=limit_price)
        elif market_type == MARKET_TYPE.SPOT:
            limit_order = self.spot_api.new_order(
                symbol, side="SELL", type="LIMIT", timeInForce="GTC", 
                quantity=volume, price=limit_price)
            
        return limit_order['orderId']
        
    def cancel_order(self, currency : str, market_type : MARKET_TYPE, order_id : str):
        try:
            item = self.available_symbols[market_type][currency]
            symbol = item['symbol']
        
            if market_type == MARKET_TYPE.FUTURES:
                resp = self.futures_api.cancel_order(symbol=symbol, orderId=order_id)
                return resp
            if market_type == MARKET_TYPE.MARGIN:
                resp = self.spot_api.cancel_margin_order(symbol=symbol, orderId=order_id)
            if market_type == MARKET_TYPE.SPOT:
                resp = self.spot_api.cancel_order(symbol=symbol, orderId=order_id)
            
        except binance.error.ClientError as e:
            if e.error_code != -2011 and e.error_message != "'Unknown order sent.'":
                raise(e)
            else:
                return None
            
        
        
    def get_position(self, currency : str, market_type : MARKET_TYPE, open_order_id : str) -> PositionItem:
        item = self.available_symbols[market_type][currency]
        symbol = item['symbol']
        if market_type == MARKET_TYPE.FUTURES:
            resp = self.futures_api.get_position_risk(symbol=symbol)
            return convert_binance_position_item_to_position_item(resp[0])
        elif market_type == MARKET_TYPE.MARGIN:
            volume = None
            account = self.spot_api.margin_account()
            for asset in account['userAssets']:
                if asset['asset'] == currency:
                    volume = float(asset['free'])
            trades = self.spot_api.margin_my_trades(f"{currency}USDT", orderId=open_order_id)
            qty = 0
            cost = 0
            for trade in trades:
                qty += float(trade['qty'])
                cost += float(trade['qty']) * float(trade['price'])
            avg_price = 1
            if qty > 0:
                avg_price = cost / qty
            return PositionItem(avg_price, volume)
        elif market_type == MARKET_TYPE.SPOT:
            account = self.spot_api.account()
            for balance in account['balances']:
                if balance['asset'] == currency:
                    volume = float(balance['free'])
            trades = self.spot_api.my_trades(f"{currency}USDT", orderId=open_order_id)
            qty = 0
            cost = 0
            for trade in trades:
                qty += float(trade['qty'])
                cost += float(trade['qty']) * float(trade['price'])
            avg_price = 1
            if qty > 0:
                avg_price = cost / qty
            return PositionItem(avg_price, volume)

            

        
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
        
        exchange_info = self.spot_api.exchange_info()
        spot_symbols = {}
        margin_symbols = {}
        for symbol in exchange_info.get('symbols', []):
            if symbol['status'] == 'TRADING' and symbol['symbol'].endswith('USDT'):
                s = symbol['symbol'][0:-4]
                if symbol['isSpotTradingAllowed']:
                    spot_symbols[s] = symbol
                if symbol['isMarginTradingAllowed']:
                    margin_symbols[s] = symbol
        self.available_symbols[MARKET_TYPE.SPOT] = spot_symbols
        self.available_symbols[MARKET_TYPE.MARGIN] = margin_symbols
        logging.info(f"Available symbols in Binance have been refreshed")
        
        threading.Timer(interval=10 * 60, function=self.__refresh_available_symbols).start()
        


            
            
            
            
        
        
        

