import telegram
import logging
import news
from keys import keys

BOT_TOKEN = keys.get('BOT_TOKEN') 
CHATS = keys.get('CHATS')

class Bot(object):
    
    def __init__(self):
        self.bot = telegram.Bot(BOT_TOKEN)
        
    def send_message(self, text: str):
        for chat in CHATS:
            self.bot.send_message(text=text, parse_mode=telegram.ParseMode.HTML, chat_id=chat)
            
    def send_news(self, n : news.News):
        msg = f"<strong>{n.source.name}</strong>: <a href='{n.href}'>{n.title}</a>"
        self.send_message(msg)