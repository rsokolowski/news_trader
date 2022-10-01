import web_scraper
import kucoin_client
import news
import logging
import telegram_bot
import time
import clock

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

bot = telegram_bot.Bot()

def news_handler(n : news.News):
    logging.info(f"Processing news: {n}")
    bot.send_news(n)
    
    

market_client = kucoin_client.KuCoinClient()
web_scraper = web_scraper.WebScraper(clock.clock)
web_scraper.set_currencies_fetcher(market_client.get_spot_currencies)
web_scraper.set_news_callback(news_handler)
web_scraper.run_in_background()

time.sleep(10000)

