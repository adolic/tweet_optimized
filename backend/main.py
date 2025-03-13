import os
import sys

from backend.constants import FREE_QUOTA
from backend.generator import TweetGenerator
from backend.lib.stripe_service import StripeService
from backend.utils import track_event

# Add the parent directory to sys.path to make 'backend' importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.lib.database import db_query, db_execute, db_query_one
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
import json
from datetime import datetime, timedelta


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()
# MODEL = Model.load(DATA_DIR / "model.pkl")
MODEL = Models.load(["views", "likes", "retweets", "comments"])
GENERATOR = TweetGenerator()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tweet-optimize.com", "http://localhost:3001", "http://localhost:8080", "http://localhost:5173"],  # Added frontend dev server origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Configure Resend API
resend.api_key = os.getenv('RESEND_API_KEY')

# Initialize auth and include its router
auth = Auth()
app.include_router(auth.router)

# Authentication dependency
get_current_user = auth.get_current_user
get_optional_user = auth.get_optional_user

class TweetPredictionRequest(BaseModel):
    text: str
    author_followers_count: int
    is_blue_verified: bool

class TweetVariationRequest(BaseModel):
    tweets: list[TweetPredictionRequest]
    custom_instructions: str | None = None

class CustomInstructionsUpdate(BaseModel):
    custom_instructions: str | None = None

@app.get("/user/custom-instructions")
async def get_custom_instructions(current_user: dict = Depends(get_current_user)):
    """Get the user's custom instructions for tweet generation"""
    try:
        result = db_query_one(
            "SELECT custom_instructions FROM users WHERE id = %s",
            (current_user['id'],)
        )
        return {"custom_instructions": result.get('custom_instructions')}
    except Exception as e:
        logger.error(f"Error getting custom instructions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/user/custom-instructions")
async def update_custom_instructions(
    data: CustomInstructionsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update the user's custom instructions for tweet generation"""
    try:
        db_execute(
            "UPDATE users SET custom_instructions = %s WHERE id = %s",
            (data.custom_instructions, current_user['id'])
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating custom instructions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tweet-variation")
async def get_tweet_variation(request: Request, data: TweetVariationRequest, current_user: dict = Depends(get_current_user)):
    try:
        COST_PER_VARIATION = 10
        # Check user quota
        quota_check = QuotaService.can_make_prediction(current_user['id'], cost=COST_PER_VARIATION)
        if quota_check["remaining"] < COST_PER_VARIATION:
            print(quota_check)
            raise HTTPException(status_code=403, detail=quota_check['reason'])
        
        author_followers_count = data.tweets[0].author_followers_count
        is_blue_verified = data.tweets[0].is_blue_verified
        tweets = [tweet.text for tweet in data.tweets]

        custom_instructions = db_query_one("SELECT custom_instructions FROM users WHERE id = %s", (current_user['id'],))
        custom_instructions = custom_instructions.get('custom_instructions')
        variations = GENERATOR.generate_tweets(tweets, custom_instructions)

        variations = [
            {
                "text": tweet,
                "author_followers_count": author_followers_count,
                "is_blue_verified": 1 if is_blue_verified else 0  # Convert to int for the ML model
            }
            for tweet in variations
        ]

        predictions = MODEL.predict_bulk(variations, [0.1] + list(range(1, 25)))
        QuotaService.record_prediction(current_user['id'], cost=COST_PER_VARIATION)

        # Track the variation generation
        await track_event(request, "Tweet Variation Generated", {
            "input_tweet_count": len(tweets),
            "variations_count": len(variations),
            "has_custom_instructions": custom_instructions is not None,
            "author_followers_count": author_followers_count,
            "is_blue_verified": is_blue_verified,
            "user_id": current_user['id'],
            "quota_remaining": quota_check['remaining'] - COST_PER_VARIATION
        })

        return {
            "variations": predictions,
            "quota_remaining": quota_check['remaining'] - 10  # Subtract 10 predictions
        }
    except HTTPException:
        raise
        


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
        
        # Make the prediction first
        prediction = MODEL.predict({
            "text": text, 
            "author_followers_count": author_followers_count,
            "is_blue_verified": 1 if is_blue_verified else 0  # Convert to int for the ML model
        }, [0.1] + list(range(1, 25)))
        
        # Only update quota after successful prediction
        QuotaService.record_prediction(
            user_id=current_user['id'],
        )

        # Track the forecast
        await track_event(request, "Tweet Forecast Generated", {
            "tweet_length": len(text),
            "author_followers_count": author_followers_count,
            "is_blue_verified": is_blue_verified,
            "user_id": current_user['id'],
            "predicted_views_24h": prediction["views"][23],  # 24-hour prediction
            "predicted_likes_24h": prediction["likes"][23],
            "predicted_retweets_24h": prediction["retweets"][23],
            "predicted_comments_24h": prediction["comments"][23],
            "quota_remaining": quota_check['remaining'] - 1
        })
        
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
async def get_user_quota(
    current_user: dict = Depends(get_current_user),
    response: Response = None,
    force_refresh: bool = False
):
    """Get the current user's quota information with caching"""
    try:
        # Set cache headers if not forcing a refresh
        if not force_refresh and response:
            response.headers["Cache-Control"] = "max-age=60"  # Cache for 60 seconds
        
        # Get user_id from the current user
        user_id = current_user['id']
        
        # Get all user stats in a single query instead of multiple queries
        # This replaces both QuotaService.can_make_prediction and QuotaService.get_user_stats
        stats = db_query_one("""
            WITH 
            -- Get current active subscription
            current_sub AS (
                SELECT 
                    us.id as subscription_id, 
                    us.status as subscription_status,
                    us.current_period_start,
                    us.current_period_end,
                    us.cancellation_date,
                    sp.id as plan_id,
                    sp.name as plan_name, 
                    sp.description as plan_description, 
                    sp.monthly_quota
                FROM user_subscriptions us
                JOIN subscription_plans sp ON us.plan_id = sp.id
                WHERE us.user_id = %s AND us.status = 'active'
                ORDER BY us.created_at DESC
                LIMIT 1
            ),
            -- Get current quota period
            current_quota AS (
                SELECT 
                    id as quota_id,
                    predictions_used,
                    predictions_limit,
                    period_start,
                    period_end
                FROM quota_usage
                WHERE user_id = %s
                ORDER BY period_start DESC
                LIMIT 1
            )
            -- Combine all data
            SELECT 
                -- Subscription data
                cs.subscription_id,
                cs.subscription_status,
                cs.current_period_start,
                cs.current_period_end,
                cs.cancellation_date,
                cs.plan_id,
                cs.plan_name,
                cs.plan_description,
                cs.monthly_quota,
                -- Quota data
                cq.quota_id,
                cq.predictions_used,
                cq.predictions_limit,
                cq.period_start,
                cq.period_end
            FROM current_sub cs
            FULL OUTER JOIN current_quota cq ON TRUE
        """, (user_id, user_id))
        
        # If no stats found, create a default quota period
        if not stats or not stats.get('quota_id'):
            # This can happen if user has no quota yet
            # Create a default quota period
            now = datetime.now()
            
            # Determine monthly quota (free plan if no subscription)
            monthly_quota = stats.get('monthly_quota') if stats else FREE_QUOTA  # Default to 5 for free plan
            
            # Create the quota period
            period_start = now
            period_end = now + timedelta(days=30)
            
            quota_id = db_query_one("""
                INSERT INTO quota_usage 
                (user_id, period_start, period_end, predictions_used, predictions_limit)
                VALUES (%s, %s, %s, 0, %s)
                RETURNING id
            """, (user_id, period_start, period_end, monthly_quota))['id']
            
            # Get the complete stats again with the new quota
            return await get_user_quota(current_user, response, True)
        
        # Format the quota info
        quota_info = {
            'allowed': stats.get('predictions_used', 0) < stats.get('predictions_limit', 0),
            'remaining': stats.get('predictions_limit', 0) - stats.get('predictions_used', 0),
            'reason': None if stats.get('predictions_used', 0) < stats.get('predictions_limit', 0) else "Monthly prediction quota exceeded"
        }
        
        # Format the user stats
        user_stats = {
            'current_quota': {
                'id': stats.get('quota_id'),
                'predictions_used': stats.get('predictions_used', 0),
                'predictions_limit': stats.get('predictions_limit', 0),
                'period_start': stats.get('period_start'),
                'period_end': stats.get('period_end')
            },
            'total_predictions': stats.get('predictions_used', 0),
            'recent_predictions': [],
            'subscription': {
                'id': stats.get('subscription_id'),
                'status': stats.get('subscription_status'),
                'plan_id': stats.get('plan_id'),
                'plan_name': 'Free' if not stats.get('subscription_id') else stats.get('plan_name'),
                'description': stats.get('plan_description'),
                'monthly_quota': stats.get('monthly_quota', FREE_QUOTA),  # Default to 5 for free plan
                'current_period_start': stats.get('current_period_start'),
                'current_period_end': stats.get('current_period_end'),
                'cancellation_date': stats.get('cancellation_date')
            }
        }
        
        # Format subscription info for the frontend
        subscription_info = None
        if stats.get('subscription_id'):
            is_cancelled = stats.get('cancellation_date') is not None
            period_end = stats.get('current_period_end')
            
            subscription_info = {
                "plan_name": stats.get('plan_name'),
                "is_cancelled": is_cancelled,
                "current_period_end": period_end.isoformat() if period_end else None,
                "monthly_quota": stats.get('monthly_quota'),
                # If cancelled, it expires at period_end, if active it renews at period_end
                "status_message": f"{'Expires' if is_cancelled else 'Renews'} on {period_end.strftime('%B %d, %Y')}" if period_end else None
            }
        
        return {
            "quota": quota_info,
            "stats": user_stats,
            "subscription": subscription_info
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

# Stripe-related routes
@app.post("/subscription/create-checkout")
async def create_checkout_session(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for the premium subscription"""
    # Track upgrade click
    await track_event(request, "Upgrade Clicked", {
        "user_id": current_user['id'],
        "email": current_user['email']
    })
    
    return await StripeService.create_checkout_session(
        user_id=current_user['id'],
        email=current_user['email']
    )

@app.get("/subscription/session/{session_id}")
async def get_session_status(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Get the status of a checkout session and update the user's subscription if needed"""
    result = await StripeService.get_session_status(session_id, current_user['id'])
    
    # Track subscription enabled if the session was successful
    if result.get('session', {}).get('payment_status') == 'paid':
        subscription_data = db_query_one("""
            SELECT sp.name as plan_name, sp.monthly_quota, us.current_period_end
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id = %s AND us.status = 'active'
            ORDER BY us.created_at DESC
            LIMIT 1
        """, (current_user['id'],))
        
        if subscription_data:
            await track_event(request, "Subscription Enabled", {
                "user_id": current_user['id'],
                "email": current_user['email'],
                "plan_name": subscription_data['plan_name'],
                "monthly_quota": subscription_data['monthly_quota'],
                "current_period_end": subscription_data['current_period_end'].isoformat() if subscription_data['current_period_end'] else None
            })
    
    return result

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    return await StripeService.handle_webhook_event(payload, sig_header)

@app.post("/subscription/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel the user's active subscription"""
    return await StripeService.cancel_subscription(current_user['id'])

@app.post("/subscription/reactivate")
async def reactivate_subscription(current_user: dict = Depends(get_current_user)):
    """Reactivate a cancelled subscription"""
    return await StripeService.reactivate_subscription(current_user['id'])

@app.post("/track/homepage-view")
async def track_homepage_view(request: Request):
    await track_event(request, "Homepage View")
    return {"status": "success"}

@app.post("/track/login-modal-opened")
async def track_login_modal_opened(request: Request):
    await track_event(request, "Login Modal Opened")
    return {"status": "success"}

@app.post("/track/email-login-sent")
async def track_email_login_sent(request: Request):
    await track_event(request, "Email Login Sent")
    return {"status": "success"}

@app.post("/track/oauth-google-clicked")
async def track_oauth_google_clicked(request: Request):
    await track_event(request, "OAuth Google Clicked")
    return {"status": "success"}

@app.post("/track/login-success")
async def track_login_success(request: Request):
    await track_event(request, "Login Success")
    return {"status": "success"}

@app.post("/track/tweet-variation-generated")
async def track_tweet_variation_generated(request: Request):
    await track_event(request, "Tweet Variation Generated")
    return {"status": "success"}

@app.post("/track/tweet-forecast-generated")
async def track_tweet_forecast_generated(request: Request):
    await track_event(request, "Tweet Forecast Generated")
    return {"status": "success"}

@app.post("/track/upgrade-clicked")
async def track_upgrade_clicked(request: Request):
    await track_event(request, "Upgrade Clicked")
    return {"status": "success"}

@app.post("/track/subscription-enabled")
async def track_subscription_enabled(request: Request):
    await track_event(request, "Subscription Enabled")
    return {"status": "success"}