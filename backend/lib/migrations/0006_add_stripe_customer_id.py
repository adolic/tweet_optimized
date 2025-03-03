def up():
    return """
    -- Add stripe_customer_id column to users table
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);
    
    -- Create index for faster lookups
    CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);
    
    -- Update Stripe price ID for Premium plan
    UPDATE subscription_plans SET stripe_price_id = 'price_1QyaElAcJbcSLyjgqaXE1XsH' WHERE name = 'Premium';
    """

def down():
    return """
    -- Drop index first
    DROP INDEX IF EXISTS idx_users_stripe_customer_id;
    
    -- Remove the stripe_customer_id column
    ALTER TABLE users DROP COLUMN IF EXISTS stripe_customer_id;
    
    -- Clear stripe_price_id for Premium plan
    UPDATE subscription_plans SET stripe_price_id = NULL WHERE name = 'Premium';
    """
