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

FETCH_TIME = prometheus_client.Summary('fetch_duration', 'Time spent scraping a website', ['website', 'cache_hit'])
FETCH_ERROR_CNT = prometheus_client.Counter('fetch_errors', 'Number of errors while scraping', ['website'])

LAMBDA_FETCHERS = keys.get('lambda_binance_fetchers')

class BinanceNewsFetcher(object):
    
    def __init__(self, clk : clock.Clock) -> None:
        self.__clock = clk
        logging.info("Web Client initialized.")
        
    
    def fetch_binance_announcement_from_lambda(self, source : news.Source, categoryId : int):
        url = f"{random.choice(LAMBDA_FETCHERS)}/?category_id={categoryId}"
        start_time = self.__clock.now()
        cache_hit = False
        try:
            result = requests.get(url).json()
            n = result['news']
            if n == None:
                logging.error(f"Error pulling binance announcement page: no news returned")
                FETCH_ERROR_CNT.labels(source.name).inc()
                return []
            cache_hit = n['cache_hit']
            FETCH_TIME.labels(source.name, cache_hit).observe(self.__clock.now() - start_time)
            candidate = news.News(source, n['releaseDate'], n['title'], "", "", [])
            logging.info(f"News: {news}")
            if candidate.title not in news.cache[source]:
                news.cache[source][candidate.title] = candidate
                return [candidate]
            else:
                return []
        except Exception as e:
            FETCH_ERROR_CNT.labels(source.name).inc()
            logging.error(f"Error pulling binance announcement page: {e}")
            return []
        
    
    def fetch_binance_announcements(self, source : news.Source, categoryId : int):
        # Generate random query/params to help prevent caching
        rand_page_size = random.randint(1, 200)
        letters = string.ascii_letters
        random_string = "".join(random.choice(letters) for i in range(random.randint(10, 20)))
        random_number = random.randint(1, 99999999999999999999)
        queries = [
            "type=1",
            f"catalogId={categoryId}",
            "pageNo=1",
            f"pageSize={str(rand_page_size)}",
            f"rnd={str(time.time())}",
            f"{random_string}={str(random_number)}",
        ]
        random.shuffle(queries)
        request_url = (
            f"https://www.binance.com/gateway-api/v1/public/cms/article/list/query"
            f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
        )

        start_time = self.__clock.now()
        cache_hit = False
        result = []
        latest_announcement = requests.get(request_url)
        if latest_announcement.status_code == 200:
            try:
                logging.info(f'X-Cache: {latest_announcement.headers["X-Cache"]}')
                cache_hit = True
            except KeyError:
                # No X-Cache header was found - great news, we're hitting the source.
                pass

            latest_announcement = latest_announcement.json()
            for n in latest_announcement["data"]["catalogs"][0]["articles"][0:2]:
                candidate = news.News(source, n['releaseDate'], n['title'], "", "", [])
                if candidate.title not in news.cache[source]:
                    news.cache[source][candidate.title] = candidate
                    result.append(candidate)
        else:
            FETCH_ERROR_CNT.labels(source.name).inc()
            logging.error(f"Error pulling binance announcement page: {latest_announcement.status_code}")
        FETCH_TIME.labels(source.name, cache_hit).observe(self.__clock.now() - start_time)
        return result
        
        
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
            initial_news = scrape_fn(web_scraper)
            for n in initial_news:
                logging.info(f"Initial news: {n}")
            logging.info(f"Initial news fetched for {website_name}")
            while True:
                try:
                    news = scrape_fn(web_scraper)
                    for n in news:
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



            
            
        
    