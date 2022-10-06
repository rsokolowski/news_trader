import web_scraper
import kucoin_client
import news
import logging
import telegram_bot
import time
import clock
from prometheus_client import start_http_server
import binance_client
from threading import Thread
from exchange_client import MARKET_TYPE

PROMETHEUS_SERVER_PORT = 11447

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

bot = telegram_bot.Bot()
client = binance_client.BinanceClient()


def news_handler(n : news.News):
    logging.info(f"Processing news: {n}")
    bot.send_news(n)
    bot.send_message(f"Wykroto tokeny: {','.join(n.tokens)}")
    if len(n.tokens) > 0:
        token = n.tokens[0]
        position_manager = binance_client.PositionManager(clock.Clock(), token, MARKET_TYPE.FUTURES, client)
        position_manager.notifier = bot.send_message
        Thread(target=position_manager.up_and_to_the_right).start()

    
def get_token_checker_fn(client : binance_client.BinanceClient):
    return lambda x: client.has_symbol(x) and x not in ["ETH", "BTC"]
    
    
start_http_server(PROMETHEUS_SERVER_PORT)


web_scraper.scrape_in_background(get_token_checker_fn(client), news_handler, clock.Clock())

while True:
    time.sleep(1)

