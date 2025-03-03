from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.lib.database import db_query, db_execute
import logging
import httpx
from backend.lib.events import EventCreate, create_event
from backend.lib.auth import Auth
from pydantic import BaseModel
from backend.model.models import Models
from backend.config import DATA_DIR
import pandas as pd


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI()
# MODEL = Model.load(DATA_DIR / "model.pkl")
MODEL = Models.load(["views", "likes", "retweets", "comments"])

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class LoginRequest(BaseModel):
    email: str

class VerifyRequest(BaseModel):
    email: str
    code: str | None = None
    magic_link_token: str | None = None

class ToggleVisibilityRequest(BaseModel):
    document_id: int
    show_live: bool

@app.post("/auth/login")
async def login(request: LoginRequest):
    """Handle login request by sending magic link and code."""
    try:
        auth = Auth()
        result = auth.create_login_attempt(request.email)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error in login: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/verify")
async def verify(request: VerifyRequest):
    """Verify a login attempt using either code or magic link."""
    try:
        auth = Auth()
        result = auth.verify_attempt(
            email=request.email,
            code=request.code,
            magic_link_token=request.magic_link_token
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        logger.error(f"Error in verify: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/me")
async def get_user_data(request: Request):
    """Get user data from session token."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(' ')[1]
        auth = Auth()
        user = auth.get_user_by_session(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session token")
            
        return {"user": user}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_user_data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/proxy")
async def proxy_request(url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch document")
            return response.text
    except Exception as e:
        logger.error(f"Error in proxy_request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/tweet-forecast")
async def get_tweet_forecast(request: Request):
    try:
        data = await request.json()
        print(data)
        # must be present, text, author_followers_count, is_blue_verified
        if not isinstance(data, dict) or 'text' not in data or not isinstance(data['text'], str) \
            or 'author_followers_count' not in data or not isinstance(data['author_followers_count'], (int, float)) \
            or 'is_blue_verified' not in data or not isinstance(data['is_blue_verified'], (int, float)):
            raise HTTPException(status_code=400, detail="Invalid request format")
        
        text = data['text']
        author_followers_count = int(data['author_followers_count'])
        is_blue_verified = int(data['is_blue_verified'])
        if not text or author_followers_count <= 0:
            return {"prediction": 0, "error": "Invalid input data"}
        
        prediction = MODEL.predict( {
            "text": text, 
            "author_followers_count": author_followers_count,
            "is_blue_verified": is_blue_verified
        }, age_hours=[0.1] + list(range(1, 24)))
        
        return {
            "prediction": prediction,
        }
    except Exception as e:
        logger.error(f"Error in get_tweet_forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    


class Ref:
    pass