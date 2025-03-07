def up():
    return """
    -- Add stripe_price_id_test column
    ALTER TABLE subscription_plans 
    ADD COLUMN stripe_price_id_test VARCHAR(255);

    -- Update the Premium test plan
    UPDATE subscription_plans 
    SET stripe_price_id_test = 'price_1QyaElAcJbcSLyjgqaXE1XsH'
    WHERE name = 'Premium test';

    -- Update the Premium plan
    UPDATE subscription_plans 
    SET stripe_price_id_test = 'price_1QyaElAcJbcSLyjgqaXE1XsH'
    WHERE name = 'Premium';
    """

def down():
    return """
    -- Remove the test price ID column
    ALTER TABLE subscription_plans 
    DROP COLUMN IF EXISTS stripe_price_id_test;
    """
