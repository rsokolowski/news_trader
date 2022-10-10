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

PROMETHEUS_SERVER_PORT = 11447


bot = telegram_bot.Bot()
client = binance_client.BinanceClient()


def news_handler(n : news.News):
    logging.info(f"Processing news: {n}")
    bot.send_news(n)
    words = [word.strip(',.') for word in n.title.split()]
    currencies = [word.upper() for word in words if client.has_currency(word.upper()) and word.upper() not in ["ETH", "BTC"]]
        
    if len(currencies) > 0:
        bot.send_message(f"Wykryto tokeny: {currencies}")
        # token = currencies[0]
        # trader = AutomaticTrader(clock=clock.Clock(), client=client, currency=token)
        # trader.notifier = bot.send_message
        # Thread(target=trader.up_and_to_the_right).start()

    
def get_token_checker_fn(client : binance_client.BinanceClient):
    return lambda x: client.has_currency(x) and x not in ["ETH", "BTC"]
    
    
start_http_server(PROMETHEUS_SERVER_PORT)
# telegram_listener = TelegramListener(clock.Clock())
# telegram_listener.listen_binance_news(news_handler)


binance_news_fetcher.fetch_in_background(news_handler, clock.Clock())

# telegram_listener.loop()

while True:
    time.sleep(1)

