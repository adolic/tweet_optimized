from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any
from .database import db_query, db_execute

logger = logging.getLogger(__name__)

class QuotaService:
    """Service to manage user quotas and track usage for tweet predictions"""
    
    @staticmethod
    def get_user_current_quota(user_id: int) -> Dict[str, Any]:
        """
        Get the current quota period data for a user.
        If no quota period exists for the current month, create one.
        """
        # Calculate the current period (month)
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_of_month = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        
        # Check if a quota period already exists for this month
        quota = db_query("""
            SELECT * FROM quota_usage 
            WHERE user_id = %s AND period_start = %s AND period_end = %s
        """, (user_id, start_of_month, end_of_month))
        
        if quota:
            return quota[0]
        
        # No quota period exists, need to create one
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
        
        # Create the quota period
        db_execute("""
            INSERT INTO quota_usage 
            (user_id, period_start, period_end, predictions_used, predictions_limit)
            VALUES (%s, %s, %s, 0, %s)
            RETURNING *
        """, (user_id, start_of_month, end_of_month, monthly_quota))
        
        # Get the created quota
        quota = db_query("""
            SELECT * FROM quota_usage 
            WHERE user_id = %s AND period_start = %s AND period_end = %s
        """, (user_id, start_of_month, end_of_month))
        
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
    def record_prediction(user_id: int, text: str, followers_count: int, is_verified: bool) -> None:
        """
        Record a prediction and update the user's quota usage.
        Raises an exception if the user exceeded their quota.
        """
        # Check if prediction is allowed
        quota_check = QuotaService.can_make_prediction(user_id)
        if not quota_check['allowed']:
            raise Exception(quota_check['reason'])
        
        # Record the prediction
        db_execute("""
            INSERT INTO predictions (user_id, tweet_text, followers_count, is_verified)
            VALUES (%s, %s, %s, %s)
        """, (user_id, text, followers_count, bool(is_verified)))
        
        # Update the quota usage
        db_execute("""
            UPDATE quota_usage
            SET predictions_used = predictions_used + 1, updated_at = NOW()
            WHERE id = %s
        """, (quota_check['quota']['id'],))
    
    @staticmethod
    def get_user_stats(user_id: int) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        # Current quota
        current_quota = QuotaService.get_user_current_quota(user_id)
        
        # Get total predictions made
        total_predictions = db_query("""
            SELECT COUNT(*) as count FROM predictions WHERE user_id = %s
        """, (user_id,))
        
        # Get recent predictions
        recent_predictions = db_query("""
            SELECT * FROM predictions 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        
        # Get the subscription plan
        subscription = db_query("""
            SELECT us.*, sp.name as plan_name, sp.description, sp.monthly_quota
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id = %s AND us.status = 'active'
            ORDER BY us.created_at DESC
            LIMIT 1
        """, (user_id,))
        
        return {
            'current_quota': current_quota,
            'total_predictions': total_predictions[0]['count'] if total_predictions else 0,
            'recent_predictions': recent_predictions,
            'subscription': subscription[0] if subscription else None
        } 