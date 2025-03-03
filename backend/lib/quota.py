from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
from .database import db_query, db_execute, db_query_one

logger = logging.getLogger(__name__)

class QuotaService:
    """Service to manage user quotas and track usage for tweet predictions"""
    
    @staticmethod
    def get_user_current_quota(user_id: int) -> Dict[str, Any]:
        """
        Get the current quota period data for a user.
        If no quota period exists for the current period, create one.
        """
        # Check if a quota period already exists that covers today
        now = datetime.now()
        
        # First, check for an active period that includes today
        quota = db_query("""
            SELECT * FROM quota_usage 
            WHERE user_id = %s AND period_start <= %s AND period_end >= %s
            ORDER BY period_start DESC LIMIT 1
        """, (user_id, now, now))
        
        if quota:
            return quota[0]
        
        # No active quota period exists, need to create one
        # First, determine the user's subscription plan
        subscription = db_query("""
            SELECT us.*, sp.monthly_quota
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id = %s AND us.status = 'active'
            ORDER BY us.created_at DESC
            LIMIT 1
        """, (user_id,))
        
        # If no subscription, assign to free plan
        if not subscription:
            free_plan = db_query("SELECT id, monthly_quota FROM subscription_plans WHERE name = 'Free'")
            if not free_plan:
                # This shouldn't happen if the migration ran correctly
                logger.error(f"No free plan found in the database. User ID: {user_id}")
                raise Exception("No free plan found in the database")
            
            # Create a subscription for the user
            db_execute("""
                INSERT INTO user_subscriptions (user_id, plan_id, status)
                VALUES (%s, %s, 'active')
            """, (user_id, free_plan[0]['id']))
            
            monthly_quota = free_plan[0]['monthly_quota']
        else:
            monthly_quota = subscription[0]['monthly_quota']
        
        # Create the quota period - start from today, end in 1 month
        period_start = now
        period_end = now + timedelta(days=30)  # Approximately 1 month
        
        db_execute("""
            INSERT INTO quota_usage 
            (user_id, period_start, period_end, predictions_used, predictions_limit)
            VALUES (%s, %s, %s, 0, %s)
        """, (user_id, period_start, period_end, monthly_quota))
        
        # Get the created quota
        quota = db_query("""
            SELECT * FROM quota_usage 
            WHERE user_id = %s
            ORDER BY period_start DESC
            LIMIT 1
        """, (user_id,))
        
        return quota[0]
    
    @staticmethod
    def can_make_prediction(user_id: int) -> Dict[str, Any]:
        """
        Check if a user can make a prediction based on their quota.
        Returns a dict with keys:
        - allowed: bool - whether the prediction is allowed
        - quota: Dict - the current quota data
        - reason: str - the reason if not allowed
        """
        quota = QuotaService.get_user_current_quota(user_id)
        
        can_predict = quota['predictions_used'] < quota['predictions_limit']
        
        return {
            'allowed': can_predict,
            'quota': quota,
            'remaining': quota['predictions_limit'] - quota['predictions_used'],
            'reason': None if can_predict else "Monthly prediction quota exceeded"
        }
    
    @staticmethod
    def record_prediction(user_id: int) -> None:
        """
        Update a user's quota usage without recording the prediction content.
        Raises an exception if the user exceeded their quota.
        """
        # Check if prediction is allowed
        quota_check = QuotaService.can_make_prediction(user_id)
        if not quota_check['allowed']:
            raise Exception(quota_check['reason'])
        
        # Update the quota usage (skip saving the prediction content)
        db_execute("""
            UPDATE quota_usage
            SET predictions_used = predictions_used + 1, updated_at = NOW()
            WHERE id = %s
        """, (quota_check['quota']['id'],))
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict[str, Any]:
        """Get usage statistics for a user using a single efficient query"""
        # Get current subscription, quota, and prediction counts in a single query
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
            CROSS JOIN current_quota cq
        """, (user_id, user_id))
        
        # If no stats found, create default structure
        if not stats:
            # This can happen if user has no subscription or quota yet
            # Get the current quota to ensure it exists (will create if needed)
            current_quota = QuotaService.get_user_current_quota(user_id)
            
            # Try again with the fresh quota
            return QuotaService.get_user_stats(user_id)
        
        # Format the result
        return {
            'current_quota': {
                'id': stats.get('quota_id'),
                'predictions_used': stats.get('predictions_used', 0),
                'predictions_limit': stats.get('predictions_limit', 0),
                'period_start': stats.get('period_start'),
                'period_end': stats.get('period_end')
            },
            'total_predictions': stats.get('predictions_used', 0),  # Use current quota predictions instead of total historical
            'recent_predictions': [],  # Empty array as we no longer store predictions
            'subscription': {
                'id': stats.get('subscription_id'),
                'status': stats.get('subscription_status'),
                'plan_id': stats.get('plan_id'),
                'plan_name': stats.get('plan_name', 'Free'),
                'description': stats.get('plan_description'),
                'monthly_quota': stats.get('monthly_quota', 0),
                'current_period_start': stats.get('current_period_start'),
                'current_period_end': stats.get('current_period_end'),
                'cancellation_date': stats.get('cancellation_date')
            }
        } 