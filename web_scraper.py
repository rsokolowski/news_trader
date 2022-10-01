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

CHROME_DRIVER = 'D:\programming\git\chromedriver.exe'

class WebScraper(object):
    
    def __init__(self, clk : clock.Clock) -> None:
        
        self.__chrome_options = webdriver.ChromeOptions()
        self.__chrome_options.add_argument('--headless')
        self.__chrome_options.add_argument('--no-sandbox')
        self.__chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(CHROME_DRIVER, options=self.__chrome_options)
        self.driver.set_page_load_timeout(10)
        atexit.register(self.driver.quit)
        self.__currencies_fetcher = lambda: {}
        self.__news_callback = None
        self.__loop_init = False
        self.__clock = clk
        logging.info("Web Client initialized.")
        
    def set_currencies_fetcher(self, currencies_fetcher):
        self.__currencies_fetcher = currencies_fetcher
        
    def set_news_callback(self, news_callback):
        self.__news_callback = news_callback
        
    def fetch_binance_announcement(self, n : news.News) -> news.News:
        self.driver.get(n.href)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[text()=\"' + n.title + '\"]')))
        elem = self.driver.find_element(By.XPATH, '//*[text()=\"' + n.title + '\"]/following-sibling::div')
        timestamp = time.mktime(datetime.datetime.strptime(elem.text, "%Y-%m-%d %H:%M").timetuple())
        elem = elem.find_element(By.XPATH, './following-sibling::div')
        full_text = elem.text
        return news.News(n.source, timestamp, n.title, full_text, n.href, news.discover_tokens(n.title, self.__currencies_fetcher()))
    
    def fetch_binance_announcements(self, source: news.Source, href: str, title : str):
        result : List[news.News] =  []
        self.driver.get(href)
        selector = '[text()="' + title + '"]'
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, f"//*{selector}")))
        elem = self.driver.find_element(By.XPATH, f"//div{selector}/following-sibling::div")
        if elem:
            elems = [e for e in elem.find_elements(By.XPATH, ".//a") if e.get_attribute('href').startswith('https://www.binance.com/en/support/announcement')]
            candidates : List[news.News] = [news.News(source, 0, e.text[0:-10], "", e.get_attribute('href'), []) for e in elems]
            for c in candidates[0:2]:
                if c.title not in news.cache[source]:
                    r = self.fetch_binance_announcement(c)
                    news.cache[source][r.title] = r
                    result.append(r)
                    if self.__loop_init == False and self.__news_callback != None:
                        self.__news_callback(r)
        return result
        
    def fetch_latest_binance_news(self) -> List[news.News]:
        return self.fetch_binance_announcements(news.Source.BINANCE_NEWS, 'https://www.binance.com/en/support/announcement/c-49', 'Latest Binance News')
    
    def fetch_new_binance_listings(self) -> List[news.News]:
        return self.fetch_binance_announcements(news.Source.BINANCE_LISTING, 'https://www.binance.com/en/support/announcement/c-48', 'New Cryptocurrency Listing')
    
    def run_in_background(self):
        def loop():
            self.__loop_init = True
            logging.info("Fetching initial news")
            self.fetch_latest_binance_news()
            self.fetch_new_binance_listings()
            logging.info("Initial news fetched")
            while True:
                start = self.__clock.now()
                news = self.fetch_latest_binance_news() + self.fetch_new_binance_listings()
                logging.info(f"News fetching loop finished in {self.__clock.now() - start}ms")
                for n in news:
                    if self.__news_callback != None:
                        self.__news_callback(n)
                time.sleep(1)
        background_thread = threading.Thread(target=loop, name="WebScraperLoop", daemon=True)
        background_thread.start()


            
            
        
    
