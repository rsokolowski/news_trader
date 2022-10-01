from enum import Enum
from typing import List, Dict
import datetime

class Source(Enum):
    BINANCE_NEWS = 1
    BINANCE_LISTING = 2

class News(object):
    
    def __init__(self, source : Source, timestamp : int, title : str, full_text : str, href : str, tokens : List[str]):
        self.source = source
        self.title = title
        self.full_text = full_text
        self.timestamp = timestamp
        self.href = href
        self.tokens = tokens
    
    def __repr__(self) -> str:
        return f"{self.source.name}({datetime.datetime.fromtimestamp(self.timestamp)})={self.title}"
    
def discover_tokens(text, tokens_maps) -> List[str]:
    tokens : List[str] = []
    for word in text.split():
        if word.upper() in tokens_maps.keys() and word not in tokens:
            tokens.append(word)
    return tokens
    

cache : Dict[Source, Dict[str, News]] = { 
    Source.BINANCE_NEWS: {},
    Source.BINANCE_LISTING: {}
}