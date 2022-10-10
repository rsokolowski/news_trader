import time

class Clock(object):
    
    def __init__(self):
        pass
    
    def now(self) -> int:
        return int(time.time() * 1000)
    
    def now_s(self) -> float:
        return time.time()
    
clock = Clock()
    
    
    