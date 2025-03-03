def up():
    return """
    -- Add cancellation_date column to user_subscriptions
    ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS cancellation_date TIMESTAMP;
    
    -- Add index for faster lookups
    CREATE INDEX IF NOT EXISTS idx_user_subscriptions_cancellation_date ON user_subscriptions(cancellation_date);
    """

def down():
    return """
    -- Remove the index
    DROP INDEX IF EXISTS idx_user_subscriptions_cancellation_date;
    
    -- Remove the cancellation_date column
    ALTER TABLE user_subscriptions DROP COLUMN IF EXISTS cancellation_date;
    """
