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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

from enum import Enum
import datetime
from typing import List, Dict
import news
import clock
import sys
import prometheus_client

CHROME_DRIVER = 'D:\programming\git\chromedriver.exe'

SCRAPE_TIME = prometheus_client.Summary('scrape_duration', 'Time spent scraping a website', ['website'])
SCRAPE_ERROR_CNT = prometheus_client.Counter('scrape_errors', 'Number of errors while scraping', ['website'])

class WebScraper(object):
    
    def __init__(self, clk : clock.Clock) -> None:
        
        self.__chrome_options = webdriver.ChromeOptions()
        self.__chrome_options.add_argument('--headless')
        self.__chrome_options.add_argument('--no-sandbox')
        self.__chrome_options.add_argument("--log-level=3")
        self.__chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(CHROME_DRIVER, options=self.__chrome_options)
        self.driver.set_page_load_timeout(10)
        atexit.register(self.driver.quit)
        self.__token_checker_fn = lambda x: False 
        self.__clock = clk
        logging.info("Web Client initialized.")
        
    def set_token_checker_fn(self, token_checker_fn):
        self.__token_checker_fn = token_checker_fn
        
        
    def fetch_binance_announcement(self, n : news.News) -> news.News:
        self.driver.get(n.href)
        title_text = ""
        for c in n.title:
            if ord(c) < 128:
                title_text += c
            else:
                break
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//h1[text()[contains(.,\"' + title_text + '\")]]')))
        elem = self.driver.find_element(By.XPATH, '//h1[text()[contains(.,\"' + title_text + '\")]]/following-sibling::div')
        timestamp = time.mktime(datetime.datetime.strptime(elem.text, "%Y-%m-%d %H:%M").timetuple())
        elem = elem.find_element(By.XPATH, './following-sibling::div')
        full_text = elem.text
        return news.News(n.source, timestamp, n.title, full_text, n.href, news.discover_tokens(n.title, self.__token_checker_fn))
    
    def fetch_binance_announcements(self, source: news.Source, href: str, title : str):
        result : List[news.News] =  []
        self.driver.get(href)
        selector = '[text()="' + title + '"]'
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, f"//*{selector}")))
        elem = self.driver.find_element(By.XPATH, f"//div{selector}/following-sibling::div")
        if elem:
            elems = [e for e in elem.find_elements(By.XPATH, ".//a") if e.get_attribute('href').startswith('https://www.binance.com/en/support/announcement')]
            candidates : List[news.News] = [news.News(source, self.__clock.now(), e.text[0:-10], "", e.get_attribute('href'), []) for e in elems]
            for c in candidates[0:2]:
                if c.title not in news.cache[source]:
                    r = c # self.fetch_binance_announcement(c)
                    news.cache[source][r.title] = r
                    result.append(r)
        return result
        
    def fetch_latest_binance_news(self) -> List[news.News]:
        return self.fetch_binance_announcements(news.Source.BINANCE_NEWS, 'https://www.binance.com/en/support/announcement/c-49', 'Latest Binance News')
    
    def fetch_new_binance_listings(self) -> List[news.News]:
        return self.fetch_binance_announcements(news.Source.BINANCE_LISTING, 'https://www.binance.com/en/support/announcement/c-48', 'New Cryptocurrency Listing')
    
    
        
        
def scrape_in_background(token_checker_fn, news_cb, clk):
    scrape_fns = {
        news.Source.BINANCE_NEWS.name: WebScraper.fetch_latest_binance_news, 
        news.Source.BINANCE_LISTING.name: WebScraper.fetch_new_binance_listings
    }
    
    for (website_name, scrape_fn) in scrape_fns.items():
        def loop(website_name, scrape_fn):
            logging.info(f"Fetching initial news for {website_name}")
            web_scraper = WebScraper(clk)
            web_scraper.set_token_checker_fn(token_checker_fn)
            initial_news = scrape_fn(web_scraper)
            for n in initial_news:
                logging.info(f"Initial news: {n}")
            logging.info(f"Initial news fetched for {website_name}")
            while True:
                try:
                    start = clk.now()
                    news = scrape_fn(web_scraper)
                    SCRAPE_TIME.labels(website_name).observe(clk.now() - start)
                    #logging.info(f"News fetching loop finished in {clk.now() - start}ms")
                    for n in news:
                        news_cb(n)
                except KeyboardInterrupt:
                    logging.warning("Interupted by user")
                    break
                except Exception as e:
                    SCRAPE_ERROR_CNT.labels(website_name).inc()
                    logging.warning(f"Exception in scraping loop: {e}")
                    time.sleep(10)
        background_thread = threading.Thread(target=loop, args=(website_name, scrape_fn, ))
        background_thread.start()



            
            
        
    
