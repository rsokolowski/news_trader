import yaml
import os

class Keys(object):
    
    def __init__(self):
        with open(os.path.dirname(os.path.abspath(__file__)) + '/secrets.yaml', 'r') as f:
            self.__secrets = yaml.load(f, Loader=yaml.Loader)
    
    def get(self, key : str) -> str:
        return self.__secrets.get(key, None)
    

keys = Keys()