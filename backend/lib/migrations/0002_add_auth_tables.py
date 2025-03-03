def up():
    return """
    -- Users table
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Login attempts tracking
    CREATE TABLE login_attempts (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        code VARCHAR(8),
        magic_link_token VARCHAR(64),
        attempt_type VARCHAR(10) NOT NULL,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 5,
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP NOT NULL,
        used BOOLEAN DEFAULT FALSE,
        invalidated BOOLEAN DEFAULT FALSE,
        invalidated_reason VARCHAR(50),

        CONSTRAINT valid_attempt CHECK (
            (NOT invalidated AND attempts < max_attempts AND expires_at > NOW())
            OR used 
            OR invalidated
        )
    );

    -- Sessions
    CREATE TABLE sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        token VARCHAR(64) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        last_used TIMESTAMP DEFAULT NOW(),
        user_agent TEXT,
        ip_address INET
    );

    -- Indexes (without using NOW() in predicates)
    CREATE INDEX idx_login_attempts_email ON login_attempts(email);
    CREATE INDEX idx_login_attempts_active ON login_attempts(email, expires_at) 
    WHERE NOT used AND NOT invalidated;
    
    CREATE INDEX idx_sessions_token ON sessions(token);
    CREATE INDEX idx_sessions_user ON sessions(user_id);
    """

def down():
    return """
    DROP TABLE IF EXISTS sessions;
    DROP TABLE IF EXISTS login_attempts;
    DROP TABLE IF EXISTS users;
    """
