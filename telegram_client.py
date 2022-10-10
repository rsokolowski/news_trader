from keys import keys
from telethon import TelegramClient, events
import logging
import news
from clock import Clock
import threading

class TelegramListener(object):
    
    def __init__(self, clock : Clock) -> None:
        self.clock = clock
        self.client = TelegramClient("news_trading", keys.get('telegram_client_api_id'), keys.get('telegram_client_api_hash'))
        
    def loop(self):
        with self.client:
            self.client.run_until_disconnected()
    
    def listen_binance_news(self, news_cb):
        @self.client.on(events.NewMessage(chats='https://t.me/binance_announcements')) 
        async def newMessageListener(event):
            # Get message text 
            text : str = event.message.message 
            logging.info(f"Processing telegram message {text}")
            tokens = text.split()
            if len(tokens) > 0 and tokens[-1].startswith('https://www.binance.com/en/support/'):
                title = ' '.join(tokens[0:-1])
                n = news.News(news.Source.BINANCE, self.clock.now(), title, "", tokens[-1], [])
                news_cb(n)
                

        
        
        