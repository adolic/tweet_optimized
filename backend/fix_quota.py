#!/usr/bin/env python
"""
Script to fix quota inconsistencies between subscription plans and quota usage
"""
from backend.lib.database import db_query, db_execute, db_query_one
import logging
from backend.lib.quota import QuotaService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Get all active premium subscriptions
    premium_subs = db_query("""
        SELECT us.user_id, us.id as subscription_id, sp.monthly_quota 
        FROM user_subscriptions us
        JOIN subscription_plans sp ON us.plan_id = sp.id
        WHERE us.status = 'active' AND sp.name = 'Premium'
    """)
    
    logger.info(f"Found {len(premium_subs)} active premium subscriptions")
    
    for sub in premium_subs:
        user_id = sub['user_id']
        
        # Get current quota
        quota = db_query_one("""
            SELECT * FROM quota_usage 
            WHERE user_id = %s
            ORDER BY period_start DESC
            LIMIT 1
        """, (user_id,))
        
        if not quota:
            logger.info(f"No quota found for user {user_id}, creating new quota")
            # Force create new quota via QuotaService
            QuotaService.get_user_current_quota(user_id)
            continue
        
        # Update the quota if not already at premium level
        if quota['predictions_limit'] != sub['monthly_quota']:
            logger.info(f"Updating quota for user {user_id} from {quota['predictions_limit']} to {sub['monthly_quota']}")
            
            db_execute("""
                UPDATE quota_usage
                SET predictions_limit = %s, updated_at = NOW()
                WHERE id = %s
            """, (sub['monthly_quota'], quota['id']))
        else:
            logger.info(f"User {user_id} already has correct quota limit of {quota['predictions_limit']}")
        
        # Also ensure user.is_premium is set correctly
        db_execute("""
            UPDATE users
            SET is_premium = TRUE
            WHERE id = %s
        """, (user_id,))
        
    logger.info("Quota fix completed")

if __name__ == "__main__":
    main() 