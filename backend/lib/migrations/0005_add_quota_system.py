def up():
    return """
    -- Create subscription plans table
    CREATE TABLE subscription_plans (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        stripe_price_id VARCHAR(100),
        description TEXT,
        monthly_quota INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Create user subscriptions table
    CREATE TABLE user_subscriptions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        plan_id INTEGER REFERENCES subscription_plans(id),
        stripe_subscription_id VARCHAR(100),
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        current_period_start TIMESTAMP,
        current_period_end TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- Create predictions table to track user predictions
    CREATE TABLE predictions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        tweet_text TEXT NOT NULL,
        followers_count INTEGER NOT NULL,
        is_verified BOOLEAN NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Create quota usage table
    CREATE TABLE quota_usage (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        period_start TIMESTAMP NOT NULL,
        period_end TIMESTAMP NOT NULL,
        predictions_used INTEGER NOT NULL DEFAULT 0,
        predictions_limit INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(user_id, period_start, period_end)
    );

    -- Insert the default free plan
    INSERT INTO subscription_plans (name, description, monthly_quota, is_active)
    VALUES ('Free', 'Free tier with 5 predictions per month', 5, TRUE);

    -- Insert the paid plan
    INSERT INTO subscription_plans (name, description, monthly_quota, is_active)
    VALUES ('Premium', 'Premium tier with 1000 predictions per month', 1000, TRUE);

    -- Create indexes for performance
    CREATE INDEX idx_predictions_user_id ON predictions(user_id);
    CREATE INDEX idx_predictions_created_at ON predictions(created_at);
    CREATE INDEX idx_quota_usage_user_id ON quota_usage(user_id);
    CREATE INDEX idx_quota_usage_period ON quota_usage(user_id, period_start, period_end);
    CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
    """

def down():
    return """
    DROP TABLE IF EXISTS quota_usage;
    DROP TABLE IF EXISTS predictions;
    DROP TABLE IF EXISTS user_subscriptions;
    DROP TABLE IF EXISTS subscription_plans;
    """
