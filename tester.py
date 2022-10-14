import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


import binance_client
import exchange_client
import automatic_trader
import telegram_bot
import time
from clock import Clock
import keys
import requests
import json
import os
import binance_news_fetcher
from pathlib import Path


def news_handler(aa):
    pass

binance_news_fetcher.fetch_in_background(news_handler, Clock())



while True:
    time.sleep(1)
