def up():
    return """
    -- Add OAuth-related columns to users table
    ALTER TABLE users
    ADD COLUMN oauth_provider VARCHAR(20),
    ADD COLUMN oauth_id VARCHAR(255),
    ADD COLUMN picture_url TEXT,
    ADD COLUMN name VARCHAR(255);

    -- Add unique constraint for OAuth provider and ID combination
    CREATE UNIQUE INDEX idx_users_oauth 
    ON users(oauth_provider, oauth_id) 
    WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL;
    """

def down():
    return """
    -- Remove OAuth-related columns from users table
    ALTER TABLE users
    DROP COLUMN oauth_provider,
    DROP COLUMN oauth_id,
    DROP COLUMN picture_url,
    DROP COLUMN name;

    -- Drop the OAuth unique index
    DROP INDEX IF EXISTS idx_users_oauth;
    """
