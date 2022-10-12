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

PROMETHEUS_SERVER_PORT = 11447


bot = telegram_bot.Bot()

clients = [binance_client.BinanceClient()]


def get_currencies(title : str):
    words = [word.strip(',.') for word in title.split()]
    coins = {}
    for word in words:
        stats = coin_info.info.coins.get(word, None)
        if stats != None:
            coins[stats['rank']] = word
    res = []
    for rank in sorted(coins.keys()):
        if rank >= dynamic_config.top_marketcaps_to_skip():
            res.append(coins[rank])
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
                

    
def get_token_checker_fn(client : binance_client.BinanceClient):
    return lambda x: client.has_currency(x) and x not in ["ETH", "BTC"]
    
    
start_http_server(PROMETHEUS_SERVER_PORT)
binance_news_fetcher.fetch_in_background(news_handler, clock.Clock())


while True:
    time.sleep(1)

