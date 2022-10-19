import random
import string
import time
import logging
from tkinter import E

import requests

import logging
import yaml
import atexit
from logging import Logger
from datetime import datetime
import threading

import selenium
from selenium import webdriver

import traceback
import time
import random

from enum import Enum
import datetime
from typing import List, Dict
import news
import clock
import sys
import prometheus_client
from keys import keys
import dynamic_config
import requests
import json
import os
from pathlib import Path

BINANCE_SCRAPER_LAMBDA_FILE = Path(os.path.dirname(os.path.abspath(__file__))).joinpath('binance_scraper_lambda.py')


FETCH_TIME = prometheus_client.Summary('fetch_duration', 'Time spent scraping a website', ['website', 'cache_hit'])
FETCH_ERROR_CNT = prometheus_client.Counter('fetch_errors', 'Number of errors while scraping', ['website'])

LAMBDA_FETCHERS = keys.get('lambda_binance_fetchers')

class BinanceNewsFetcher(object):
    
    def __init__(self, clk : clock.Clock) -> None:
        self.__clock = clk
        logging.info("Web Client initialized.")
        
    
    def fetch_binance_announcement_from_lambda(self, source : news.Source, categoryId : int):        
        url = f"{random.choice(LAMBDA_FETCHERS)}"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        start_time = self.__clock.now()
        cache_hit = False
        try:
            with open(BINANCE_SCRAPER_LAMBDA_FILE, 'r') as file:
                code = file.read()
                data = {
                    'code': code,
                    'key': keys.get('lambda_executor_key'),
                    'category_id': categoryId
                }
                n = requests.post(url, data=json.dumps(data), headers=headers).json()
                if n == None:
                    logging.error(f"Error pulling binance announcement page {url}: no news returned")
                    FETCH_ERROR_CNT.labels(source.name).inc()
                    return []
                cache_hit = n['cache_hit']
                FETCH_TIME.labels(source.name, cache_hit).observe(self.__clock.now() - start_time)
                candidate = news.News(source, n['releaseDate'], n['title'], "", "", [])
                #logging.info(f"News: {candidate}")
                if candidate.title not in news.cache[source]:
                    news.cache[source][candidate.title] = candidate
                    return [candidate]
                else:
                    return []
        except Exception as e:
            FETCH_ERROR_CNT.labels(source.name).inc()
            logging.error(f"Error pulling binance announcement page from {url}: {e}")
            return []
        
        
        
    def fetch_latest_binance_news(self) -> List[news.News]:
        return self.fetch_binance_announcement_from_lambda(news.Source.BINANCE_NEWS, 49)
    
    def fetch_new_binance_listings(self) -> List[news.News]:
        return self.fetch_binance_announcement_from_lambda(news.Source.BINANCE_LISTING, 48)
    
    
        
        
def fetch_in_background(news_cb, clk):
    scrape_fns = {
        news.Source.BINANCE_NEWS.name: BinanceNewsFetcher.fetch_latest_binance_news, 
        news.Source.BINANCE_LISTING.name: BinanceNewsFetcher.fetch_new_binance_listings
    }
    
    for (website_name, scrape_fn) in scrape_fns.items():
        def loop(website_name, scrape_fn):
            logging.info(f"Fetching initial news for {website_name}")
            web_scraper = BinanceNewsFetcher(clk)
            while True:
                initial_news = scrape_fn(web_scraper)
                for n in initial_news:
                    logging.info(f"Initial news: {n}")
                if len(initial_news) > 0:
                    break
            logging.info(f"Initial news fetched for {website_name}")
            while True:
                try:
                    news = scrape_fn(web_scraper)
                    for n in news:
                        logging.info(f"Handling news: {news}")
                        news_cb(n)
                except KeyboardInterrupt:
                    logging.warning("Interupted by user")
                    break
                except Exception as e:
                    logging.warning(f"Exception in scraping loop: {e}")
                    time.sleep(10)
                time.sleep(dynamic_config.binance_fetcher_refresh_interval_s())
        background_thread = threading.Thread(target=loop, args=(website_name, scrape_fn, ))
        background_thread.start()



            
            
        
    