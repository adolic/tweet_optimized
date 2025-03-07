import datetime


class SimpleCache:
    def __init__(self):
        self._cache = {}

    def set(self, key: str, data: any, expiry_seconds: int = 60):
        self._cache[key] = {
            'data': data,
            'expiry': datetime.datetime.now() + datetime.timedelta(seconds=expiry_seconds)
        }

    def get(self, key: str) -> any:
        if key not in self._cache:
            return None
        
        cache_item = self._cache[key]
        if datetime.datetime.now() > cache_item['expiry']:
            del self._cache[key]
            return None
            
        return cache_item['data']
