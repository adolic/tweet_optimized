def up():
    return """
    -- First apply the still-pending migration for cancellation_date
    ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS cancellation_date TIMESTAMP;
    CREATE INDEX IF NOT EXISTS idx_user_subscriptions_cancellation_date ON user_subscriptions(cancellation_date);
    
    -- 1. Remove unused subscription_id from users table
    ALTER TABLE users DROP COLUMN IF EXISTS subscription_id;
    
    -- 2. Make sure quota_usage properly references user_subscriptions
    -- First, add the subscription_id to quota_usage table
    ALTER TABLE quota_usage ADD COLUMN subscription_id INTEGER;
    
    -- 3. Create foreign key constraints
    -- First create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_id ON user_subscriptions(plan_id);
    CREATE INDEX IF NOT EXISTS idx_quota_usage_subscription_id ON quota_usage(subscription_id);
    
    -- Add foreign key constraints
    ALTER TABLE user_subscriptions 
        ADD CONSTRAINT fk_user_subscriptions_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    
    ALTER TABLE user_subscriptions 
        ADD CONSTRAINT fk_user_subscriptions_plan_id 
        FOREIGN KEY (plan_id) REFERENCES subscription_plans(id) ON DELETE RESTRICT;
    
    -- 4. Update quota_usage to reference user_subscriptions
    -- Match quota periods to subscription periods
    UPDATE quota_usage q
    SET subscription_id = s.id
    FROM user_subscriptions s
    WHERE q.user_id = s.user_id
    AND q.period_start = s.current_period_start
    AND q.period_end = s.current_period_end;
    
    -- For any orphaned quota records, try to find by user_id and overlap
    UPDATE quota_usage q
    SET subscription_id = s.id
    FROM user_subscriptions s
    WHERE q.subscription_id IS NULL
    AND q.user_id = s.user_id
    AND s.status = 'active';
    
    -- Add the foreign key constraint after data migration
    ALTER TABLE quota_usage 
        ADD CONSTRAINT fk_quota_usage_subscription_id 
        FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id) ON DELETE CASCADE;
    
    -- 5. Add function to update user premium status automatically
    CREATE OR REPLACE FUNCTION update_user_premium_status()
    RETURNS TRIGGER AS $$
    BEGIN
        -- When subscription status changes, update user's premium status
        IF (TG_OP = 'UPDATE' AND OLD.status != NEW.status) OR TG_OP = 'INSERT' THEN
            UPDATE users
            SET is_premium = (NEW.status = 'active')
            WHERE id = NEW.user_id;
        -- When subscription is deleted and user has no other active subscriptions
        ELSIF TG_OP = 'DELETE' THEN
            UPDATE users u
            SET is_premium = EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = OLD.user_id AND us.status = 'active'
            )
            WHERE u.id = OLD.user_id;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Create trigger for automatic user premium status update
    DROP TRIGGER IF EXISTS trigger_update_user_premium_status ON user_subscriptions;
    CREATE TRIGGER trigger_update_user_premium_status
    AFTER INSERT OR UPDATE OR DELETE ON user_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_user_premium_status();
    """

def down():
    return """
    -- Remove triggers first
    DROP TRIGGER IF EXISTS trigger_update_user_premium_status ON user_subscriptions;
    DROP FUNCTION IF EXISTS update_user_premium_status();
    
    -- Remove foreign key constraints and indexes
    ALTER TABLE quota_usage DROP CONSTRAINT IF EXISTS fk_quota_usage_subscription_id;
    ALTER TABLE user_subscriptions DROP CONSTRAINT IF EXISTS fk_user_subscriptions_plan_id;
    ALTER TABLE user_subscriptions DROP CONSTRAINT IF EXISTS fk_user_subscriptions_user_id;
    
    DROP INDEX IF EXISTS idx_quota_usage_subscription_id;
    DROP INDEX IF EXISTS idx_user_subscriptions_plan_id;
    DROP INDEX IF EXISTS idx_user_subscriptions_user_id;
    
    -- Remove subscription_id from quota_usage
    ALTER TABLE quota_usage DROP COLUMN IF EXISTS subscription_id;
    
    -- Add back subscription_id to users (though we'll leave it NULL)
    ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_id INTEGER;
    
    -- Remove cancellation_date
    DROP INDEX IF EXISTS idx_user_subscriptions_cancellation_date;
    ALTER TABLE user_subscriptions DROP COLUMN IF EXISTS cancellation_date;
    """
