import os
import sys

from backend.generator import TweetGenerator

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
import stripe
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

# Configure Stripe API
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

PREMIUM_PLAN_NAME = os.getenv('PREMIUM_PLAN_NAME', 'Premium')
STRIPE_ENV = os.getenv('STRIPE_ENV')

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
            monthly_quota = stats.get('monthly_quota') if stats else 5  # Default to 5 for free plan
            
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
                'monthly_quota': stats.get('monthly_quota', 5),  # Default to 5 for free plan
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

# Stripe webhook endpoint
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        # Get the webhook payload
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # Verify webhook signature using the webhook signing secret
        # This helps ensure the webhook came from Stripe
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            logger.error("Stripe webhook secret not configured")
            return {"status": "error", "message": "Webhook secret not configured"}
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid webhook payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Invalid webhook signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle specific webhook events
        event_type = event['type']
        logger.info(f"Received Stripe webhook: {event_type}")
        
        # Handle checkout.session.completed event
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            
            # Extract user ID from metadata
            user_id = session.get('metadata', {}).get('user_id')
            if not user_id:
                logger.error("No user ID in session metadata")
                return {"status": "error", "message": "No user ID in session metadata"}
            
            # Make sure the user exists
            user = db_query_one("SELECT * FROM users WHERE id = %s", (user_id,))
            if not user:
                logger.error(f"User not found: {user_id}")
                return {"status": "error", "message": "User not found"}
            
            # Get customer ID and subscription ID
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            
            # Update user's customer ID if needed
            if customer_id and not user.get('stripe_customer_id'):
                db_execute(
                    "UPDATE users SET stripe_customer_id = %s WHERE id = %s", 
                    (customer_id, user_id)
                )
            
            # Handle subscription
            if subscription_id:
                # Get premium plan ID
                premium_plan = db_query_one(f"SELECT id, monthly_quota FROM subscription_plans WHERE name = '{PREMIUM_PLAN_NAME}'")
                
                if not premium_plan:
                    logger.error("Premium plan not found in database")
                    return {"status": "error", "message": "Premium plan not found"}
                
                # Current date for subscription period
                now = datetime.now()
                period_end = now + timedelta(days=30)  # Approximately 1 month
                
                # Update or create user subscription
                existing_sub = db_query_one(
                    "SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active'", 
                    (user_id,)
                )
                
                if existing_sub:
                    # Update existing subscription
                    db_execute(
                        """
                        UPDATE user_subscriptions 
                        SET plan_id = %s, stripe_subscription_id = %s, status = 'active',
                            current_period_start = %s, current_period_end = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (premium_plan['id'], subscription_id, now, period_end, existing_sub['id'])
                    )
                else:
                    # Create new subscription
                    db_execute(
                        """
                        INSERT INTO user_subscriptions 
                        (user_id, plan_id, stripe_subscription_id, status, current_period_start, current_period_end)
                        VALUES (%s, %s, %s, 'active', %s, %s)
                        """,
                        (user_id, premium_plan['id'], subscription_id, now, now, period_end)
                    )
                
                # Update is_premium flag
                db_execute("UPDATE users SET is_premium = TRUE WHERE id = %s", (user_id,))
                
                # Create a new quota period for the subscription
                current_quota = db_query_one("""
                    SELECT * FROM quota_usage
                    WHERE user_id = %s AND period_start <= %s AND period_end >= %s
                    ORDER BY period_start DESC LIMIT 1
                """, (user_id, now, now))
                
                if current_quota:
                    # Update existing quota
                    db_execute("""
                        UPDATE quota_usage
                        SET predictions_limit = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (premium_plan['monthly_quota'], current_quota['id']))
                else:
                    # Create new quota period
                    db_execute("""
                        INSERT INTO quota_usage
                        (user_id, period_start, period_end, predictions_used, predictions_limit)
                        VALUES (%s, %s, %s, 0, %s)
                    """, (user_id, now, period_end, premium_plan['monthly_quota']))
                
                logger.info(f"Successfully updated subscription for user {user_id}")
        
        # Handle customer.subscription.updated event
        elif event_type == 'customer.subscription.updated':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            
            # Find user by customer ID
            user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
            if not user:
                logger.error(f"User not found for customer: {customer_id}")
                return {"status": "error", "message": "User not found"}
            
            # Get the subscription details
            subscription_id = subscription.get('id')
            current_period_start = datetime.fromtimestamp(subscription.get('current_period_start', 0))
            current_period_end = datetime.fromtimestamp(subscription.get('current_period_end', 0))
            status = subscription.get('status')
            cancel_at_period_end = subscription.get('cancel_at_period_end', False)

            # Get the user's current subscription record
            user_subscription = db_query_one("""
                SELECT us.*, sp.monthly_quota
                FROM user_subscriptions us
                JOIN subscription_plans sp ON us.plan_id = sp.id
                WHERE us.user_id = %s AND us.stripe_subscription_id = %s
            """, (user['id'], subscription_id))

            if not user_subscription:
                logger.error(f"No subscription found for user {user['id']} with Stripe ID {subscription_id}")
                return {"status": "error", "message": "Subscription not found"}

            # Update the subscription periods and status
            db_execute("""
                UPDATE user_subscriptions 
                SET current_period_start = %s,
                    current_period_end = %s,
                    status = %s,
                    cancellation_date = CASE WHEN %s THEN NOW() ELSE NULL END,
                    updated_at = NOW()
                WHERE id = %s
            """, (current_period_start, current_period_end, status, cancel_at_period_end, user_subscription['id']))

            # Create or update quota for the new period
            current_quota = db_query_one("""
                SELECT * FROM quota_usage
                WHERE user_id = %s AND period_start <= %s AND period_end >= %s
                ORDER BY period_start DESC LIMIT 1
            """, (user['id'], current_period_start, current_period_start))

            if current_quota:
                # Update existing quota period
                db_execute("""
                    UPDATE quota_usage
                    SET predictions_limit = %s,
                        period_start = %s,
                        period_end = %s,
                        predictions_used = 0,
                        updated_at = NOW()
                    WHERE id = %s
                """, (user_subscription['monthly_quota'], current_period_start, current_period_end, current_quota['id']))
            else:
                # Create new quota period
                db_execute("""
                    INSERT INTO quota_usage
                    (user_id, period_start, period_end, predictions_used, predictions_limit)
                    VALUES (%s, %s, %s, 0, %s)
                """, (user['id'], current_period_start, current_period_end, user_subscription['monthly_quota']))

            logger.info(f"Successfully updated subscription and quota for user {user['id']}")

            return {"status": "success"}
        
        # Handle customer.subscription.deleted event
        elif event_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            
            # Find user by customer ID
            user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
            if not user:
                logger.error(f"User not found for customer: {customer_id}")
                return {"status": "error", "message": "User not found"}

            # Get the subscription details
            subscription_id = subscription.get('id')
            
            # Update the subscription in our database
            db_execute("""
                UPDATE user_subscriptions 
                SET status = 'cancelled',
                    updated_at = NOW()
                WHERE user_id = %s AND stripe_subscription_id = %s
            """, (user['id'], subscription_id))
            
            logger.info(f"Marked subscription as cancelled for user {user['id']}")
            return {"status": "success"}
        
        # Handle invoice.payment_failed event
        elif event_type == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            subscription_id = invoice.get('subscription')
            
            if not subscription_id:
                return {"status": "success"}  # Not a subscription invoice
            
            # Find user by customer ID
            user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
            if not user:
                logger.error(f"User not found for customer: {customer_id}")
                return {"status": "error", "message": "User not found"}
            
            # Update subscription status to reflect payment failure
            db_execute("""
                UPDATE user_subscriptions 
                SET status = 'past_due',
                    updated_at = NOW()
                WHERE user_id = %s AND stripe_subscription_id = %s
            """, (user['id'], subscription_id))
            
            logger.info(f"Marked subscription as past_due for user {user['id']} due to payment failure")
            return {"status": "success"}
        
        # Handle customer.subscription.trial_will_end event (if you implement trials in the future)
        elif event_type == 'customer.subscription.trial_will_end':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            
            # Find user by customer ID
            user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
            if not user:
                logger.error(f"User not found for customer: {customer_id}")
                return {"status": "error", "message": "User not found"}
            
            # You could implement trial end notification logic here
            logger.info(f"Trial ending soon for user {user['id']}")
            return {"status": "success"}
        
        # Return success for other events
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing webhook")

# Manual subscription upgrade endpoint
@app.post("/subscription/manual-upgrade")
async def manual_subscription_upgrade(current_user: dict = Depends(get_current_user)):
    """Manually upgrade a user's subscription when webhook doesn't trigger"""
    try:
        # Get premium plan ID
        premium_plan = db_query_one(f"SELECT id FROM subscription_plans WHERE name = '{PREMIUM_PLAN_NAME}'")
        
        if not premium_plan:
            logger.error("Premium plan not found in database")
            raise HTTPException(status_code=404, detail="Premium plan not found")
        
        # Update or create user subscription
        existing_sub = db_query_one(
            "SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active'", 
            (current_user['id'],)
        )
        
        if existing_sub:
            # Update existing subscription
            db_execute(
                """
                UPDATE user_subscriptions 
                SET plan_id = %s, status = 'active',
                    current_period_start = NOW(), current_period_end = NOW() + INTERVAL '1 month',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (premium_plan['id'], existing_sub['id'])
            )
        else:
            # Create new subscription
            db_execute(
                """
                INSERT INTO user_subscriptions 
                (user_id, plan_id, status, current_period_start, current_period_end)
                VALUES (%s, %s, 'active', NOW(), NOW() + INTERVAL '1 month')
                """,
                (current_user['id'], premium_plan['id'])
            )
        
        logger.info(f"Manually updated subscription for user {current_user['id']}")
        
        # Update user quota for the current period
        current_quota = QuotaService.get_user_current_quota(current_user['id'])
        if current_quota:
            # Get the premium plan quota
            premium_quota = db_query_one(
                f"SELECT monthly_quota FROM subscription_plans WHERE name = '{PREMIUM_PLAN_NAME}'"
            )
            
            if premium_quota:
                # Update quota limit
                db_execute(
                    """
                    UPDATE quota_usage
                    SET predictions_limit = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (premium_quota['monthly_quota'], current_quota['id'])
                )
        
        return {"status": "success", "message": "Subscription manually updated"}
    except Exception as e:
        logger.error(f"Error manually updating subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Create a Stripe Checkout Session
@app.post("/subscription/create-checkout")
async def create_checkout_session(current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for the premium subscription"""
    try:
        # Get premium plan ID
        premium_plan = db_query_one(f"SELECT id, stripe_price_id, monthly_quota FROM subscription_plans WHERE name = '{PREMIUM_PLAN_NAME}'")
        if not premium_plan:
            raise HTTPException(status_code=404, detail="Premium plan not found")
        
        if STRIPE_ENV == 'test':
            # this will force using test mode
            customer_id = None
        else:
            # Check if the user already has a Stripe customer ID
            user_data = db_query_one("SELECT stripe_customer_id FROM users WHERE id = %s", (current_user['id'],))
            customer_id = user_data.get('stripe_customer_id')
        
        # If no customer ID, create a new Stripe customer
        if not customer_id:
            customer = stripe.Customer.create(
                email=current_user['email'],
                metadata={
                    "user_id": current_user['id']
                }
            )
            customer_id = customer.id
            
            # Save the customer ID to the user record
            db_execute(
                "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
                (customer_id, current_user['id'])
            )
        
        # Build success and cancel URLs
        success_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5174')}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5174')}/subscription/cancel"
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': premium_plan['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": current_user['id'],
                "plan_id": premium_plan['id']
            }
        )
        
        return {"checkout_url": session.url}
    
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

# Fetch session endpoint to check subscription status
@app.get("/subscription/session/{session_id}")
async def get_session_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get the status of a checkout session and update the user's subscription if needed"""
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify that this session belongs to the current user
        if session.metadata.get('user_id') != str(current_user['id']):
            raise HTTPException(status_code=403, detail="Unauthorized access to this session")
        
        # If payment is successful and not already processed, update the subscription
        if session.payment_status == 'paid':
            # Get the subscription plan from session metadata
            plan_id = session.metadata.get('plan_id')
            if not plan_id:
                # Fallback to looking up the premium plan
                premium_plan = db_query_one(f"SELECT id, monthly_quota FROM subscription_plans WHERE name = '{PREMIUM_PLAN_NAME}'")
                plan_id = premium_plan['id']
                monthly_quota = premium_plan['monthly_quota']
            else:
                # Get the plan details
                plan_data = db_query_one("SELECT id, monthly_quota FROM subscription_plans WHERE id = %s", (plan_id,))
                if not plan_data:
                    raise HTTPException(status_code=404, detail="Subscription plan not found")
                
                monthly_quota = plan_data['monthly_quota']
            
            # Current date for subscription period
            now = datetime.now()
            period_end = now + timedelta(days=30)  # Approximately 1 month
            
            # Check if the user already has an active subscription
            existing_sub = db_query_one("""
                SELECT id FROM user_subscriptions 
                WHERE user_id = %s AND status = 'active'
            """, (current_user['id'],))
            
            if existing_sub:
                # Update the existing subscription
                db_execute("""
                    UPDATE user_subscriptions 
                    SET plan_id = %s, 
                        current_period_start = %s,
                        current_period_end = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (plan_id, now, period_end, existing_sub['id']))
            else:
                # Create a new subscription
                db_execute("""
                    INSERT INTO user_subscriptions 
                    (user_id, plan_id, stripe_subscription_id, status, current_period_start, current_period_end)
                    VALUES (%s, %s, %s, 'active', %s, %s)
                """,
                (current_user['id'], plan_id, session.subscription, now, period_end))
            
            # Update the is_premium flag in the users table
            db_execute("""
                UPDATE users 
                SET is_premium = TRUE
                WHERE id = %s
            """, (current_user['id'],))
            
            # Create a new quota period for the subscription
            current_quota = db_query_one("""
                SELECT * FROM quota_usage
                WHERE user_id = %s AND period_start <= %s AND period_end >= %s
                ORDER BY period_start DESC LIMIT 1
            """, (current_user['id'], now, now))
            
            if current_quota:
                # Update existing quota period
                db_execute("""
                    UPDATE quota_usage
                    SET predictions_limit = %s, updated_at = NOW()
                    WHERE id = %s
                """, (monthly_quota, current_quota['id'])
            )
            else:
                # Create new quota period
                db_execute("""
                    INSERT INTO quota_usage
                    (user_id, period_start, period_end, predictions_used, predictions_limit)
                    VALUES (%s, %s, %s, 0, %s)
                """, (current_user['id'], now, period_end, monthly_quota))
        
        # Return the session to the client
        return {"session": {
            "id": session.id,
            "payment_status": session.payment_status,
            "customer": session.customer,
        }}
    
    except Exception as e:
        logger.error(f"Error processing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process session")

# Endpoint to cancel a subscription
@app.post("/subscription/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel the user's active subscription"""
    try:
        # Get the user's active subscription
        subscription = db_query_one("""
            SELECT us.id, us.stripe_subscription_id, us.current_period_end
            FROM user_subscriptions us
            WHERE us.user_id = %s AND us.status = 'active'
        """, (current_user['id'],))
        
        if not subscription:
            logger.error(f"No active subscription found for user {current_user['id']}")
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Handle case where we have a subscription record but no Stripe subscription ID
        if not subscription.get('stripe_subscription_id'):
            logger.warning(f"User {current_user['id']} has an active subscription without Stripe ID")
            
            # Update subscription in our database - use the trigger to update user.is_premium
            # Just mark it as cancelled but still active until period end
            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NOW()
                WHERE id = %s
            """, (subscription['id'],))
            
            # Use the current_period_end from our database if available
            formatted_date = "the end of your current billing period"
            if subscription.get('current_period_end'):
                formatted_date = subscription['current_period_end'].strftime("%Y-%m-%d")
            
            return {
                "status": "success", 
                "message": f"Subscription will be cancelled at {formatted_date}",
                "expiration_date": formatted_date
            }
        
        # Otherwise, cancel the subscription in Stripe
        stripe_subscription_id = subscription['stripe_subscription_id']
        try:
            # Use at_period_end=True to allow the user to use the subscription until the end of the current period
            stripe_response = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update subscription in our database
            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NOW()
                WHERE id = %s
            """, (subscription['id'],))
            
            # Return success with cancellation details
            current_period_end = datetime.fromtimestamp(stripe_response.current_period_end)
            formatted_date = current_period_end.strftime("%Y-%m-%d")
            
            return {
                "status": "success", 
                "message": f"Subscription will be cancelled at the end of the current billing period ({formatted_date})",
                "expiration_date": formatted_date
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error while cancelling subscription: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to cancel subscription with Stripe")
            
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")

@app.post("/subscription/reactivate")
async def reactivate_subscription(current_user: dict = Depends(get_current_user)):
    """Reactivate a cancelled subscription"""
    try:
        # Get the user's subscription that was cancelled but still active
        subscription = db_query_one("""
            SELECT us.id, us.stripe_subscription_id, us.current_period_end
            FROM user_subscriptions us
            WHERE us.user_id = %s 
            AND us.status = 'active'
            AND us.cancellation_date IS NOT NULL
        """, (current_user['id'],))
        
        if not subscription:
            logger.error(f"No cancelled subscription found for user {current_user['id']}")
            raise HTTPException(status_code=404, detail="No cancelled subscription found")
        
        # Handle case where we have a subscription record but no Stripe subscription ID
        if not subscription.get('stripe_subscription_id'):
            logger.warning(f"User {current_user['id']} has a subscription without Stripe ID")
            
            # Simply remove the cancellation date
            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NULL
                WHERE id = %s
            """, (subscription['id'],))
            
            return {
                "status": "success",
                "message": "Subscription reactivated successfully"
            }
        
        # Otherwise, reactivate the subscription in Stripe
        stripe_subscription_id = subscription['stripe_subscription_id']
        try:
            # Remove the cancel_at_period_end flag
            stripe_response = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=False
            )
            
            # Update subscription in our database
            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NULL
                WHERE id = %s
            """, (subscription['id'],))
            
            return {
                "status": "success",
                "message": "Subscription reactivated successfully"
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error while reactivating subscription: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to reactivate subscription with Stripe")
            
    except Exception as e:
        logger.error(f"Error reactivating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reactivate subscription")