import os
import stripe
import logging
from datetime import datetime, timedelta
from fastapi import HTTPException

from backend.config import ENV
from .database import db_query, db_execute, db_query_one

logger = logging.getLogger(__name__)

# Configure Stripe API
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


class StripeService:
    @staticmethod
    async def create_checkout_session(user_id: int, email: str):
        """Create a Stripe checkout session for the premium subscription"""
        try:
            # Get premium plan ID
            field = 'stripe_price_id_test' if ENV == 'test' else 'stripe_price_id'
            premium_plan = db_query_one(f"SELECT id, {field}, monthly_quota FROM subscription_plans WHERE name = 'Premium'")
            if not premium_plan:
                raise HTTPException(status_code=404, detail="Premium plan not found")
            
            user_data = db_query_one("SELECT stripe_customer_id FROM users WHERE id = %s", (user_id,))
            customer_id = user_data.get('stripe_customer_id')
            
            # If no customer ID, create a new Stripe customer
            if not customer_id:
                customer = stripe.Customer.create(
                    email=email,
                    metadata={
                        "user_id": user_id
                    }
                )
                customer_id = customer.id
                
                # Save the customer ID to the user record
                db_execute(
                    "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
                    (customer_id, user_id)
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
                    "user_id": user_id,
                    "plan_id": premium_plan['id']
                }
            )
            
            return {"checkout_url": session.url}
        
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create checkout session")

    @staticmethod
    async def handle_webhook_event(payload: bytes, sig_header: str):
        """Handle Stripe webhook events"""
        try:
            # Verify webhook signature using the webhook signing secret
            webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
            if not webhook_secret:
                logger.error("Stripe webhook secret not configured")
                return {"status": "error", "message": "Webhook secret not configured"}
            
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError as e:
                logger.error(f"Invalid webhook payload: {e}")
                raise HTTPException(status_code=400, detail="Invalid payload")
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Invalid webhook signature: {e}")
                raise HTTPException(status_code=400, detail="Invalid signature")

            # Handle specific webhook events
            event_type = event['type']
            logger.info(f"Received Stripe webhook: {event_type}")

            handlers = {
                'checkout.session.completed': StripeService._handle_checkout_completed,
                'customer.subscription.updated': StripeService._handle_subscription_updated,
                'customer.subscription.deleted': StripeService._handle_subscription_deleted,
                'invoice.payment_failed': StripeService._handle_payment_failed,
                'customer.subscription.trial_will_end': StripeService._handle_trial_will_end
            }

            handler = handlers.get(event_type)
            if handler:
                return await handler(event['data']['object'])
            
            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error processing Stripe webhook: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing webhook")

    @staticmethod
    async def _handle_checkout_completed(session):
        """Handle checkout.session.completed webhook event"""
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

        if subscription_id:
            await StripeService._create_or_update_subscription(
                user_id=user_id,
                subscription_id=subscription_id
            )

        return {"status": "success"}

    @staticmethod
    async def _handle_subscription_updated(subscription):
        """Handle customer.subscription.updated webhook event"""
        customer_id = subscription.get('customer')
        user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return {"status": "error", "message": "User not found"}

        subscription_id = subscription.get('id')
        current_period_start = datetime.fromtimestamp(subscription.get('current_period_start', 0))
        current_period_end = datetime.fromtimestamp(subscription.get('current_period_end', 0))
        status = subscription.get('status')
        cancel_at_period_end = subscription.get('cancel_at_period_end', False)

        await StripeService._update_subscription_periods(
            user_id=user['id'],
            subscription_id=subscription_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            status=status,
            cancel_at_period_end=cancel_at_period_end
        )

        return {"status": "success"}

    @staticmethod
    async def _handle_subscription_deleted(subscription):
        """Handle customer.subscription.deleted webhook event"""
        customer_id = subscription.get('customer')
        user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return {"status": "error", "message": "User not found"}

        subscription_id = subscription.get('id')
        db_execute("""
            UPDATE user_subscriptions 
            SET status = 'cancelled',
                updated_at = NOW()
            WHERE user_id = %s AND stripe_subscription_id = %s
        """, (user['id'], subscription_id))

        logger.info(f"Marked subscription as cancelled for user {user['id']}")
        return {"status": "success"}

    @staticmethod
    async def _handle_payment_failed(invoice):
        """Handle invoice.payment_failed webhook event"""
        customer_id = invoice.get('customer')
        subscription_id = invoice.get('subscription')

        if not subscription_id:
            return {"status": "success"}  # Not a subscription invoice

        user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return {"status": "error", "message": "User not found"}

        db_execute("""
            UPDATE user_subscriptions 
            SET status = 'past_due',
                updated_at = NOW()
            WHERE user_id = %s AND stripe_subscription_id = %s
        """, (user['id'], subscription_id))

        logger.info(f"Marked subscription as past_due for user {user['id']} due to payment failure")
        return {"status": "success"}

    @staticmethod
    async def _handle_trial_will_end(subscription):
        """Handle customer.subscription.trial_will_end webhook event"""
        customer_id = subscription.get('customer')
        user = db_query_one("SELECT * FROM users WHERE stripe_customer_id = %s", (customer_id,))
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return {"status": "error", "message": "User not found"}

        # You could implement trial end notification logic here
        logger.info(f"Trial ending soon for user {user['id']}")
        return {"status": "success"}

    @staticmethod
    async def _create_or_update_subscription(user_id: int, subscription_id: str):
        """Create or update a user's subscription"""
        # Get premium plan ID
        premium_plan = db_query_one(f"SELECT id, monthly_quota FROM subscription_plans WHERE name = 'Premium'")
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
            db_execute(
                """
                INSERT INTO user_subscriptions 
                (user_id, plan_id, stripe_subscription_id, status, current_period_start, current_period_end)
                VALUES (%s, %s, %s, 'active', %s, %s)
                """,
                (user_id, premium_plan['id'], subscription_id, now, period_end)
            )

        # Update is_premium flag
        db_execute("UPDATE users SET is_premium = TRUE WHERE id = %s", (user_id,))

        # Create or update quota period
        await StripeService._update_quota_period(
            user_id=user_id,
            period_start=now,
            period_end=period_end,
            monthly_quota=premium_plan['monthly_quota']
        )

    @staticmethod
    async def _update_subscription_periods(
        user_id: int,
        subscription_id: str,
        current_period_start: datetime,
        current_period_end: datetime,
        status: str,
        cancel_at_period_end: bool
    ):
        """Update subscription periods and status"""
        user_subscription = db_query_one("""
            SELECT us.*, sp.monthly_quota
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id = %s AND us.stripe_subscription_id = %s
        """, (user_id, subscription_id))

        if not user_subscription:
            logger.error(f"No subscription found for user {user_id} with Stripe ID {subscription_id}")
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

        # Update quota period
        await StripeService._update_quota_period(
            user_id=user_id,
            period_start=current_period_start,
            period_end=current_period_end,
            monthly_quota=user_subscription['monthly_quota']
        )

    @staticmethod
    async def _update_quota_period(
        user_id: int,
        period_start: datetime,
        period_end: datetime,
        monthly_quota: int
    ):
        """Create or update a quota period"""
        current_quota = db_query_one("""
            SELECT * FROM quota_usage
            WHERE user_id = %s AND period_start <= %s AND period_end >= %s
            ORDER BY period_start DESC LIMIT 1
        """, (user_id, period_start, period_start))

        if current_quota:
            db_execute("""
                UPDATE quota_usage
                SET predictions_limit = %s,
                    period_start = %s,
                    period_end = %s,
                    predictions_used = 0,
                    updated_at = NOW()
                WHERE id = %s
            """, (monthly_quota, period_start, period_end, current_quota['id']))
        else:
            db_execute("""
                INSERT INTO quota_usage
                (user_id, period_start, period_end, predictions_used, predictions_limit)
                VALUES (%s, %s, %s, 0, %s)
            """, (user_id, period_start, period_end, monthly_quota))

    @staticmethod
    async def cancel_subscription(user_id: int):
        """Cancel a user's subscription"""
        subscription = db_query_one("""
            SELECT us.id, us.stripe_subscription_id, us.current_period_end
            FROM user_subscriptions us
            WHERE us.user_id = %s AND us.status = 'active'
        """, (user_id,))

        if not subscription:
            logger.error(f"No active subscription found for user {user_id}")
            raise HTTPException(status_code=404, detail="No active subscription found")

        # Handle case where we have a subscription record but no Stripe subscription ID
        if not subscription.get('stripe_subscription_id'):
            logger.warning(f"User {user_id} has an active subscription without Stripe ID")
            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NOW()
                WHERE id = %s
            """, (subscription['id'],))

            formatted_date = "the end of your current billing period"
            if subscription.get('current_period_end'):
                formatted_date = subscription['current_period_end'].strftime("%Y-%m-%d")

            return {
                "status": "success",
                "message": f"Subscription will be cancelled at {formatted_date}",
                "expiration_date": formatted_date
            }

        # Cancel the subscription in Stripe
        try:
            stripe_response = stripe.Subscription.modify(
                subscription['stripe_subscription_id'],
                cancel_at_period_end=True
            )

            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NOW()
                WHERE id = %s
            """, (subscription['id'],))

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

    @staticmethod
    async def reactivate_subscription(user_id: int):
        """Reactivate a cancelled subscription"""
        subscription = db_query_one("""
            SELECT us.id, us.stripe_subscription_id, us.current_period_end
            FROM user_subscriptions us
            WHERE us.user_id = %s 
            AND us.status = 'active'
            AND us.cancellation_date IS NOT NULL
        """, (user_id,))

        if not subscription:
            logger.error(f"No cancelled subscription found for user {user_id}")
            raise HTTPException(status_code=404, detail="No cancelled subscription found")

        # Handle case where we have a subscription record but no Stripe subscription ID
        if not subscription.get('stripe_subscription_id'):
            logger.warning(f"User {user_id} has a subscription without Stripe ID")
            db_execute("""
                UPDATE user_subscriptions 
                SET cancellation_date = NULL
                WHERE id = %s
            """, (subscription['id'],))

            return {
                "status": "success",
                "message": "Subscription reactivated successfully"
            }

        # Reactivate the subscription in Stripe
        try:
            stripe.Subscription.modify(
                subscription['stripe_subscription_id'],
                cancel_at_period_end=False
            )

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

    @staticmethod
    async def get_session_status(session_id: str, user_id: int):
        """Get the status of a checkout session and update the user's subscription if needed"""
        try:
            logger.info(f"Checking session status for session_id: {session_id}, user_id: {user_id}")
            
            # Retrieve the session from Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            logger.info(f"Session retrieved: payment_status={session.payment_status}, customer={session.customer}")
            
            # Verify that this session belongs to the current user
            if session.metadata.get('user_id') != str(user_id):
                raise HTTPException(status_code=403, detail="Unauthorized access to this session")
            
            # If payment is successful and not already processed, update the subscription
            if session.payment_status == 'paid':
                logger.info("Payment successful, updating subscription")
                
                # Get the subscription plan from session metadata
                plan_id = session.metadata.get('plan_id')
                if not plan_id:
                    # Fallback to looking up the premium plan
                    premium_plan = db_query_one(f"SELECT id, monthly_quota FROM subscription_plans WHERE name = 'Premium'")
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
                """, (user_id,))
                
                if existing_sub:
                    logger.info(f"Updating existing subscription for user {user_id}")
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
                    logger.info(f"Creating new subscription for user {user_id}")
                    # Create a new subscription
                    db_execute("""
                        INSERT INTO user_subscriptions 
                        (user_id, plan_id, stripe_subscription_id, status, current_period_start, current_period_end)
                        VALUES (%s, %s, %s, 'active', %s, %s)
                    """,
                    (user_id, plan_id, session.subscription, now, period_end))
                
                # Update the is_premium flag in the users table
                db_execute("""
                    UPDATE users 
                    SET is_premium = TRUE
                    WHERE id = %s
                """, (user_id,))
                
                # Create a new quota period for the subscription
                current_quota = db_query_one("""
                    SELECT * FROM quota_usage
                    WHERE user_id = %s AND period_start <= %s AND period_end >= %s
                    ORDER BY period_start DESC LIMIT 1
                """, (user_id, now, now))
                
                if current_quota:
                    logger.info(f"Updating existing quota period for user {user_id}")
                    # Update existing quota period
                    db_execute("""
                        UPDATE quota_usage
                        SET predictions_limit = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (monthly_quota, current_quota['id'])
                    )
                else:
                    logger.info(f"Creating new quota period for user {user_id}")
                    # Create new quota period
                    db_execute("""
                        INSERT INTO quota_usage
                        (user_id, period_start, period_end, predictions_used, predictions_limit)
                        VALUES (%s, %s, %s, 0, %s)
                    """, (user_id, now, period_end, monthly_quota))
            
            # Return the session to the client
            return {"session": {
                "id": session.id,
                "payment_status": session.payment_status,
                "customer": session.customer,
            }}
        
        except Exception as e:
            logger.error(f"Error processing session: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process session") 