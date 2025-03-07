def up():
    return """
    -- Add is_premium column if it doesn't exist
    DO $$ 
    BEGIN 
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'is_premium'
        ) THEN
            ALTER TABLE users
            ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;
        END IF;
    END $$;
    """

def down():
    return """
    -- Remove is_premium column if it exists
    DO $$ 
    BEGIN 
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'is_premium'
        ) THEN
            ALTER TABLE users
            DROP COLUMN is_premium;
        END IF;
    END $$;
    """
