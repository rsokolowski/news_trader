import logging

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
from cmath import log
import decimal
from re import L
from turtle import pos, position
from keys import keys
from exchange_client import MARKET_TYPE, TradeStreamItem, PositionItem, Exchange
import os, certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

import binance.error
from binance.spot import Spot
import threading
from typing import List
from queue import Queue
import random
import time
import datetime
import clock
import coin_info
import requests
import news
from pathlib import Path


RESULT_FILE = Path(os.path.dirname(os.path.abspath(__file__))).joinpath('history_analysis.txt')


source_to_category = {
    news.Source.BINANCE_LISTING: 48,
    news.Source.BINANCE_NEWS: 49
}

def get_currencies(title : str):
    words = [word.strip(',.()') for word in title.split()]
    items = []
    for token in words:
        for i in token.split('/'):
            items.append(i)
    coins = {}
    res = []
    for word in items:
        stats = coin_info.info.coins.get(word, None)
        if stats != None:
            coins[stats['rank']] = word
    for rank in sorted(coins.keys()):
        if rank >= 8 and coins[rank] not in ['USDT', 'USDC', 'BUSD', 'DAI']:
            res.append(coins[rank])
    random.shuffle(res)
    return res

def fetch_binance_announcements(source, num_news):
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 1)

    random_number = random.randint(1, 99999999999999999999)
    queries = [
        "type=1",
        f"catalogId={source_to_category[source]}",
        "pageNo=1",
        f"pageSize={num_news}",
    ]
    request_url = (
        f"https://www.binance.com/gateway-api/v1/public/cms/article/list/query"
        f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}"
    )

    latest_announcement = requests.get(request_url, timeout=1)
    if latest_announcement.status_code == 200:
        try:
            cache_hit = True
        except KeyError:
            # No X-Cache header was found - great news, we're hitting the source.
            pass

        latest_announcement = latest_announcement.json()
        res = []
        for item in latest_announcement["data"]["catalogs"][0]["articles"]:
            res.append(news.News(source, item['releaseDate'], item['title'], "", "", get_currencies(item['title'])))
        return res
    else:
        return None
    


def convert_date_to_ts(d : str) -> int:
    return int(time.mktime(datetime.datetime.strptime(d, "%Y-%m-%d %H:%M:%S").timetuple()) * 1000)

def format_time_delta(ms) -> str:
    s = ms / 1000.
    if s < 60:
        return f"{s:.2f}s"
    else:
        m = int(s / 60)
        s = int(s - m * 60)
        return f"{m}m {s}s"

class PriceAnalysis(object):
    
    def __init__(self, start_time, start_price) -> None:
        self.start_time = start_time
        self.max_time = start_time
        self.start_price = start_price
        self.max_price = start_price
        self.cummulative_volume = 0
        self.max_price_breakout_pc = 0
        self.price_breakout_after = {}
        self.max_retractment_pct = 0
        self.increase_per_retractment = {}
        
    def analyze(self, items):
        for item in items:
            ts = item['T']
            self.max_time = ts
            time_delta = ts - self.start_time
            price = float(item['p'])
            volume = float(item['q'])
            self.cummulative_volume += price * volume
            if price < self.start_price:
                price = self.start_price
            
            if price > self.max_price:
                price_delta_pct = int((price / self.start_price - 1.) * 100)
                if self.max_price_breakout_pc < price_delta_pct:
                    self.max_price_breakout_pc = price_delta_pct
                    self.price_breakout_after[self.max_price_breakout_pc] = [time_delta, self.cummulative_volume]
                self.max_price = price
            elif 1 in self.price_breakout_after and time_delta > 30 * 1000:
                max_increase = self.max_price - self.start_price
                current_increase = price - self.start_price
                retracement_pct = int((max_increase - current_increase) / max_increase * 100)
                while self.max_retractment_pct < retracement_pct:
                    self.max_retractment_pct += 1
                    increase_pct = (price / self.start_price - 1)  * 100.
                    self.increase_per_retractment[self.max_retractment_pct] = [time_delta, self.cummulative_volume, increase_pct]
                    
    
                    
                
            
            
        #     price = elem['p']
        #     price_delta_pct =(float(price) / start_price - 1.) * 100
        #     total_volume += float(price) * float(elem['q'])
        #     logging.info(f"{t}: {price}; cumm vol={total_volume:.0f} price delta = {price_delta_pct:.1f}%")
        #     time.sleep(1)


class PriceHistoryAnalyzer(object):
    
    def __init__(self) -> None:
        self.client = Spot(key=keys.get('BINANCE_API_KEY'), secret=keys.get('BINANCE_API_SECRET'), timeout=3)
        
    def get_price_history(self, from_ts, to_ts, currency):
        logging.info(f"Fetching price history for [{datetime.datetime.fromtimestamp(from_ts / 1000.)}, {datetime.datetime.fromtimestamp(to_ts / 1000.)}] for {currency}. ")
        symbol = None
        exchange_info = self.client.exchange_info()
        expected_symbols = [f"{currency}{stable}" for stable in ['USDT', 'BUSD']]
        for info in exchange_info.get('symbols', []):
            if info['symbol'] in expected_symbols:
                symbol = info['symbol']
                break
        if symbol == None:
            logging.info(f"Brak pary walutowej dla {currency}")
            return None
        
        logging.info(f"Uzywam pary walotowej {symbol}.")
        result = self.client.agg_trades(symbol=symbol, limit=1000, startTime=from_ts, endTime=to_ts)
        return result
    
    def analyze_news(self, n : news.News):
        logging.info(f"Analyzing news: {n}")
        start_time = n.timestamp
        end_time = start_time + 30 * 60 * 1000
        with open(RESULT_FILE, 'a', encoding='utf-8') as output:
            output.write(f"\n\n")
            output.write(f"Przetwarzam newsa \"{n.title}\" z datą {datetime.datetime.fromtimestamp(n.timestamp / 1000.)}.\n")
            output.write(f"Wykryte crypto: [{n.tokens}]\n")
            for token in n.tokens:
                history = self.get_price_history(start_time, end_time, token)
                if history == None or len(history) == 0:
                    output.write(f"\n  Crypto {token} nie jest dostępny na Binance.\n\n")
                    continue
                output.write(f"  Przetwarzam crypto {token}:\n")
                analysis = PriceAnalysis(start_time, float(history[0]['p']))
                analysis.analyze(history)
                while analysis.max_time + 5 < end_time:
                    history = self.get_price_history(analysis.max_time + 1, end_time, token)
                    if len(history) == 0:
                        break
                    analysis.analyze(history)
                    
                output.write(f"    Dane za okres [{datetime.datetime.fromtimestamp(analysis.start_time / 1000.)}, {datetime.datetime.fromtimestamp(analysis.max_time / 1000.)}]\n")
                output.write(f"    Cena startowa: {analysis.start_price}\n")
                pct_increase = (analysis.max_price / analysis.start_price - 1) * 100
                output.write(f"    Cena maksymalna: {analysis.max_price} (zmiana o {pct_increase:.1f}%)\n")
                if analysis.max_price_breakout_pc > 0:
                    output.write(f"    Analiza wzrostów:\n")
                    for inc in sorted(analysis.price_breakout_after.keys()):
                        time_delta = format_time_delta(analysis.price_breakout_after[inc][0])
                        vol = int(analysis.price_breakout_after[inc][1])
                        output.write(f"      Wzrost o {inc}% po {time_delta} i obrocie {vol} USD.\n")
                considered_retractments = [10, 20, 30, 50]
                if analysis.max_retractment_pct >= considered_retractments[0]:
                    output.write(f"    Analiza zysków przy cofce od maxa:\n")
                    for ret in considered_retractments:
                        if ret not in analysis.increase_per_retractment.keys():
                            break
                        time_delta = format_time_delta(analysis.increase_per_retractment[ret][0])
                        vol = int(analysis.increase_per_retractment[ret][1])
                        inc_pct = int(analysis.increase_per_retractment[ret][2])
                        output.write(f"      Cofka o {ret}% od maxa po {time_delta} i obrocie {vol} USD. Zysk {inc_pct:.2f}%.\n")
                else:
                    output.write(f"    Nie nastąpiła znacząca cofka od maxa:\n")
               
                
                
            
        
    

news = fetch_binance_announcements(news.Source.BINANCE_LISTING, 20) + fetch_binance_announcements(news.Source.BINANCE_NEWS, 20)
news = sorted(news, key=lambda x: x.timestamp, reverse=True)
analyzer = PriceHistoryAnalyzer()
for n in news:
    analyzer.analyze_news(n)
