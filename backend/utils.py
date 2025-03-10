import datetime
import dotenv
dotenv.load_dotenv()
import mixpanel
import os
from mixpanel import Mixpanel
from fastapi import Request
from backend.config import ENV
import json

MIXPANEL = Mixpanel(os.getenv("MIXPANEL_TOKEN"))

async def track_event(request: Request, event_name: str, properties: dict = None):
    if properties is None:
        properties = {}
    
    # Get properties from request body if any
    try:
        body = await request.body()
        if body:
            body_properties = json.loads(body)
            properties.update(body_properties)
    except:
        pass
    
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    environment = request.headers.get("x-environment") or ENV or 'development'
    
    base_properties = {
        "ip": client_host,
        "browser": user_agent,
        "referrer": referer,
        "$ip": client_host,
        "$user_agent": user_agent,
        "$referrer": referer,
        "environment": environment
    }
    
    properties.update(base_properties)
    MIXPANEL.track(client_host, event_name, properties)

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
