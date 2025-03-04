def up():
    return """
    ALTER TABLE user_subscriptions ADD COLUMN start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    """

def down():
    return """
    ALTER TABLE user_subscriptions DROP COLUMN start_date;
    """
