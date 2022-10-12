import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


import binance_client
import exchange_client
import automatic_trader
import telegram_bot
import time
from clock import Clock
import coin_info

bot = telegram_bot.Bot()


def price_handler_futures(price):
    logging.info(f"FUTURES Handling price: {price}")
    
def price_handler_spot(price):
    logging.info(f"SPOT Handling price: {price}")



coin_info = coin_info.CoinInfo()




while True:
    time.sleep(1)
