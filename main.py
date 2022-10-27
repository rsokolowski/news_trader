import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


import binance_news_fetcher
import kucoin_client
import news
import telegram_bot
import time
import clock
from prometheus_client import start_http_server
import binance_client
from threading import Thread
from exchange_client import MARKET_TYPE
from automatic_trader import AutomaticTrader
from telegram_client import TelegramListener
import coin_info
import dynamic_config
import random

PROMETHEUS_SERVER_PORT = 11447


bot = telegram_bot.Bot()

clients = [binance_client.BinanceClient()]


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
    for rank in sorted(coins.keys(), reverse=True):
        if rank >= dynamic_config.top_marketcaps_to_skip() and coins[rank] not in dynamic_config.token_blacklist():
            res.append(coins[rank])
    random.shuffle(res)
    return res
    

def news_handler(n : news.News):
    logging.info(f"Processing news: {n}")
    bot.send_news(n)
    currencies = get_currencies(n.title) 
    if len(currencies) > 0:
        bot.send_message(f"Wykryto tokeny: {currencies}")
        for client in clients:
            for currency in currencies:
                if client.has_currency(currency):
                    trader = AutomaticTrader(clock=clock.Clock(), exchange=client, currency=currency)
                    trader.notifier = bot.send_message
                    Thread(target=trader.up_and_to_the_right).start()
                    break
                

    
start_http_server(PROMETHEUS_SERVER_PORT)
binance_news_fetcher.fetch_in_background(news_handler, clock.Clock())
logging.info("STARTING MAIN LOOP")

while True:
    time.sleep(1)

