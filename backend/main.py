from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.lib.database import db_query, db_execute
import logging
import httpx
from backend.lib.events import EventCreate, create_event
from backend.lib.auth import Auth
from backend.lib.quota import QuotaService
from pydantic import BaseModel
from backend.model.models import Models
from backend.config import DATA_DIR
import pandas as pd
import os
from dotenv import load_dotenv
import resend


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

load_dotenv()
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

# Configure Resend API
resend.api_key = os.getenv('RESEND_API_KEY')

class LoginRequest(BaseModel):
    email: str

class VerifyRequest(BaseModel):
    email: str
    code: str | None = None
    magic_link_token: str | None = None

class ToggleVisibilityRequest(BaseModel):
    document_id: int
    show_live: bool

class TweetPredictionRequest(BaseModel):
    text: str
    author_followers_count: int
    is_blue_verified: bool

# Authentication dependency
async def get_current_user(request: Request):
    """Get the current authenticated user or raise 401 error."""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=401, 
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(' ')[1]
    auth = Auth()
    user = auth.get_user_by_session(token)
    
    if not user:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

# Optional authentication - doesn't raise error if not authenticated
async def get_optional_user(request: Request):
    """Get the current user or return None if not authenticated."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

@app.post("/auth/login")
async def login(request: LoginRequest):
    """Handle login request by sending magic link and code."""
    try:
        auth = Auth()
        result = auth.create_login_attempt(request.email)
        
        # Check if result is a dictionary and contains an "error" key
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # If result is not a dictionary or doesn't have expected format
        if not isinstance(result, dict) or "success" not in result:
            raise HTTPException(status_code=500, detail="Invalid response format from authentication service")
            
        return result
    except HTTPException:
        # Re-raise HTTP exceptions as they are already formatted properly
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error in login: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=str(e) or "An unknown error occurred")

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

@app.post("/tweet-forecast")
async def get_tweet_forecast(request: Request, data: TweetPredictionRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Check user quota
        quota_check = QuotaService.can_make_prediction(current_user['id'])
        if not quota_check['allowed']:
            raise HTTPException(status_code=403, detail=quota_check['reason'])
            
        text = data.text
        author_followers_count = data.author_followers_count
        is_blue_verified = data.is_blue_verified  # This is already a boolean from the Pydantic model
        
        if not text or author_followers_count <= 0:
            return {"prediction": 0, "error": "Invalid input data"}
        
        prediction = MODEL.predict({
            "text": text, 
            "author_followers_count": author_followers_count,
            "is_blue_verified": 1 if is_blue_verified else 0  # Convert to int for the ML model
        }, [0.1] + list(range(1, 25)))
        
        # Record the prediction
        QuotaService.record_prediction(
            user_id=current_user['id'], 
            text=text, 
            followers_count=author_followers_count, 
            is_verified=is_blue_verified  # Pass the boolean directly
        )
        
        return {
            "prediction": prediction,
            "quota_remaining": quota_check['remaining'] - 1  # Subtract this prediction
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_tweet_forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/quota")
async def get_user_quota(current_user: dict = Depends(get_current_user)):
    """Get the current user's quota information"""
    try:
        quota_info = QuotaService.can_make_prediction(current_user['id'])
        stats = QuotaService.get_user_stats(current_user['id'])
        
        return {
            "quota": quota_info,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error in get_user_quota: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subscription/plans")
async def get_subscription_plans(current_user: dict = Depends(get_optional_user)):
    """Get available subscription plans"""
    try:
        plans = db_query("SELECT * FROM subscription_plans ORDER BY monthly_quota")
        
        # If user is authenticated, include their current plan
        current_plan = None
        if current_user:
            user_sub = db_query("""
                SELECT us.*, sp.name as plan_name, sp.monthly_quota
                FROM user_subscriptions us
                JOIN subscription_plans sp ON us.plan_id = sp.id
                WHERE us.user_id = %s AND us.status = 'active'
                ORDER BY us.created_at DESC
                LIMIT 1
            """, (current_user['id'],))
            
            if user_sub:
                current_plan = user_sub[0]
        
        return {
            "plans": plans,
            "current_plan": current_plan
        }
    except Exception as e:
        logger.error(f"Error in get_subscription_plans: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class Ref:
    pass

@app.get("/test-email")
async def test_email(email: str):
    """Test endpoint to verify Resend email functionality."""
    try:
        logger.info(f"Testing email to: {email}")
        
        # Check if Resend API key is set
        api_key = resend.api_key
        if not api_key:
            logger.error("Resend API key is not set")
            return {"error": "Resend API key is not configured"}
            
        # Send a test email
        response = resend.Emails.send({
            "from": "Tweet-Optimize Test <test@tweet-optimize.com>",
            "to": [email],
            "subject": "Test Email from Tweet-Optimize",
            "html": "<h1>This is a test email</h1><p>If you receive this, the email service is working correctly.</p>"
        })
        
        logger.info(f"Test email response: {response}")
        return {"success": True, "message": "Test email sent", "response": response}
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error sending test email: {str(e)}\n{error_traceback}")
        return {"error": f"Failed to send test email: {str(e)}"}