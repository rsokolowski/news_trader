import telegram
import logging
import news
import queue
import threading
import datetime
from keys import keys

BOT_TOKEN = keys.get('BOT_TOKEN') 
CHATS = keys.get('CHATS')


class Bot(object):
    
    def __init__(self):
        self.bot = telegram.Bot(BOT_TOKEN)
        self.q = queue.Queue()
        threading.Thread(target=self.__run_in_background, daemon=True).start()
    
    def __run_in_background(self):
        while True:
            item = self.q.get()
            self.__send_message(item)
            
    def __send_message(self, text: str):
        for chat in CHATS:
            self.bot.send_message(text=text, parse_mode=telegram.ParseMode.HTML, chat_id=chat)
        
    def send_message(self, text: str):
        self.q.put(f"{datetime.datetime.now()}: {text}")
            
    def send_news(self, n : news.News):
        msg = f"<strong>{n.source.name}</strong>: <a href='{n.href}'>{n.title}</a>. Time: {datetime.datetime.fromtimestamp(n.timestamp / 1000.)}"
        self.send_message(msg)