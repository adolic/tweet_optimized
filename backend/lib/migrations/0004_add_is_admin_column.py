def up():
    return """
    ALTER TABLE users
    ADD COLUMN is_admin BOOLEAN DEFAULT false;
    """

def down():
    return """
    ALTER TABLE users
    DROP COLUMN is_admin;
    """
