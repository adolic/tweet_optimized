def up():
    return """
    -- Add indexes to improve quota query performance
    CREATE INDEX IF NOT EXISTS idx_quota_usage_user_period ON quota_usage(user_id, period_start DESC, period_end DESC);
    CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_status ON user_subscriptions(user_id, status);
    CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_id ON user_subscriptions(plan_id);
    CREATE INDEX IF NOT EXISTS idx_predictions_user_created ON predictions(user_id, created_at DESC);
    """

def down():
    return """
    -- Remove indexes
    DROP INDEX IF EXISTS idx_quota_usage_user_period;
    DROP INDEX IF EXISTS idx_user_subscriptions_user_status;
    DROP INDEX IF EXISTS idx_user_subscriptions_plan_id;
    DROP INDEX IF EXISTS idx_predictions_user_created;
    """
