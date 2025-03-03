def up():
    return """
    ALTER TABLE login_attempts
    DROP COLUMN code,
    DROP COLUMN attempt_type,
    DROP COLUMN attempts,
    DROP COLUMN max_attempts,
    DROP COLUMN invalidated,
    DROP COLUMN invalidated_reason;
    """

def down():
    return """
    ALTER TABLE login_attempts
    ADD COLUMN code VARCHAR(6),
    ADD COLUMN attempt_type VARCHAR(10) NOT NULL DEFAULT 'magic_link',
    ADD COLUMN attempts INTEGER DEFAULT 0,
    ADD COLUMN max_attempts INTEGER DEFAULT 3,
    ADD COLUMN invalidated BOOLEAN DEFAULT FALSE,
    ADD COLUMN invalidated_reason VARCHAR(50);
    """ 