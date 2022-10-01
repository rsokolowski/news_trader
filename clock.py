import time

class Clock(object):
    
    def __init__(self):
        pass
    
    def now(self) -> int:
        return int(time.time() * 1000)
    
clock = Clock()
    
    
    