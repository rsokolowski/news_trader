from enum import Enum
from typing import List, Dict
import datetime

class Source(Enum):
    BINANCE_NEWS = 1
    BINANCE_LISTING = 2
    BINANCE = 3

class News(object):
    
    def __init__(self, source : Source, timestamp : int, title : str, full_text : str, href : str, tokens : List[str]):
        self.source = source
        self.title = title
        self.full_text = full_text
        self.timestamp = timestamp
        self.href = href
        self.tokens = tokens
    
    def __repr__(self) -> str:
        return f"{self.source.name}({datetime.datetime.fromtimestamp(self.timestamp / 1000.)})={self.title} tokens=[{self.tokens}]"
    
def discover_tokens(text, token_checker_fn) -> List[str]:
    tokens : List[str] = []
    for word in text.split():
        word_upper = word.upper()
        if token_checker_fn(word_upper) and word_upper not in tokens:
            tokens.append(word)
    return tokens
    

cache : Dict[Source, Dict[str, News]] = { 
    Source.BINANCE: {},
    Source.BINANCE_NEWS: {},
    Source.BINANCE_LISTING: {}
}