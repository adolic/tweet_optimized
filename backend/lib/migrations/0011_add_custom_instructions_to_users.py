def up():
    return """
    ALTER TABLE users ADD COLUMN custom_instructions TEXT;
    """

def down():
    return """
    ALTER TABLE users DROP COLUMN custom_instructions;
    """
