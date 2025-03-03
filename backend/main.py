from fastapi import FastAPI, HTTPException, Request, Depends
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

# Configure Stripe API
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

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

# Stripe webhook endpoint
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    # Get the webhook secret from environment variables
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        # Verify the event came from Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid payload in Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid signature in Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle specific event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Get the client reference ID which should contain the user's session token
        client_reference_id = session.get('client_reference_id')
        if not client_reference_id:
            logger.error("No client_reference_id in Stripe session")
            return {"status": "error", "message": "No client reference ID"}
        
        # Get customer email
        customer_email = session.get('customer_details', {}).get('email')
        if not customer_email:
            logger.error("No customer email in Stripe session")
            return {"status": "error", "message": "No customer email"}
        
        # Find user by session token or email
        auth = Auth()
        user = auth.get_user_by_session(client_reference_id)
        
        # If no user found by session token, try to find by email
        if not user and customer_email:
            user_record = db_query_one("SELECT * FROM users WHERE email = %s", (customer_email,))
            if user_record:
                user = user_record
        
        if not user:
            logger.error(f"No user found for Stripe webhook. Email: {customer_email}")
            return {"status": "error", "message": "User not found"}
        
        # Get subscription ID
        subscription_id = session.get('subscription')
        
        if subscription_id:
            # Get premium plan ID
            premium_plan = db_query_one("SELECT id FROM subscription_plans WHERE name = 'Premium'")
            
            if not premium_plan:
                logger.error("Premium plan not found in database")
                return {"status": "error", "message": "Premium plan not found"}
            
            # Update or create user subscription
            existing_sub = db_query_one(
                "SELECT id FROM user_subscriptions WHERE user_id = %s AND status = 'active'", 
                (user['id'],)
            )
            
            if existing_sub:
                # Update existing subscription
                db_execute(
                    """
                    UPDATE user_subscriptions 
                    SET plan_id = %s, stripe_subscription_id = %s, status = 'active',
                        current_period_start = NOW(), current_period_end = NOW() + INTERVAL '1 month',
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (premium_plan['id'], subscription_id, existing_sub['id'])
                )
            else:
                # Create new subscription
                db_execute(
                    """
                    INSERT INTO user_subscriptions 
                    (user_id, plan_id, stripe_subscription_id, status, 
                     current_period_start, current_period_end)
                    VALUES (%s, %s, %s, 'active', NOW(), NOW() + INTERVAL '1 month')
                    """,
                    (user['id'], premium_plan['id'], subscription_id)
                )
            
            logger.info(f"Successfully updated subscription for user {user['id']}")
            
            # Update user quota for the current period
            current_quota = QuotaService.get_user_current_quota(user['id'])
            if current_quota:
                # Get the premium plan quota
                premium_quota = db_query_one(
                    "SELECT monthly_quota FROM subscription_plans WHERE name = 'Premium'"
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
            
            return {"status": "success", "message": "Subscription updated"}
    
    return {"status": "success"}

# Manual subscription upgrade endpoint
@app.post("/subscription/manual-upgrade")
async def manual_subscription_upgrade(current_user: dict = Depends(get_current_user)):
    """Manually upgrade a user's subscription when webhook doesn't trigger"""
    try:
        # Get premium plan ID
        premium_plan = db_query_one("SELECT id FROM subscription_plans WHERE name = 'Premium'")
        
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
                "SELECT monthly_quota FROM subscription_plans WHERE name = 'Premium'"
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
        premium_plan = db_query_one("SELECT id, stripe_price_id, monthly_quota FROM subscription_plans WHERE name = 'Premium'")
        if not premium_plan:
            raise HTTPException(status_code=404, detail="Premium plan not found")
        
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
        success_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/subscription/cancel"
        
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
                premium_plan = db_query_one("SELECT id, monthly_quota FROM subscription_plans WHERE name = 'Premium'")
                plan_id = premium_plan['id']
                monthly_quota = premium_plan['monthly_quota']
            else:
                # Get the plan details
                plan_data = db_query_one("SELECT id, monthly_quota FROM subscription_plans WHERE id = %s", (plan_id,))
                if not plan_data:
                    raise HTTPException(status_code=404, detail="Subscription plan not found")
                
                monthly_quota = plan_data['monthly_quota']
            
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
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (plan_id, existing_sub['id']))
            else:
                # Create a new subscription
                db_execute("""
                    INSERT INTO user_subscriptions (user_id, plan_id, status, start_date)
                    VALUES (%s, %s, 'active', CURRENT_TIMESTAMP)
                """, (current_user['id'], plan_id))
            
            # Update the is_premium flag in the users table
            db_execute("""
                UPDATE users 
                SET is_premium = TRUE
                WHERE id = %s
            """, (current_user['id'],))
            
            # Update the current quota usage record to reflect the new plan
            current_quota = QuotaService.get_user_current_quota(current_user['id'])
            if current_quota:
                db_execute("""
                    UPDATE quota_usage
                    SET predictions_limit = %s, updated_at = NOW()
                    WHERE id = %s
                """, (monthly_quota, current_quota['id']))
        
        # Return the session to the client
        return {"session": {
            "id": session.id,
            "payment_status": session.payment_status,
            "customer": session.customer,
        }}
    
    except Exception as e:
        logger.error(f"Error processing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process session")