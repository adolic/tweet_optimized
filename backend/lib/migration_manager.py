import os
import importlib.util
from typing import List
from .database import Database

class MigrationManager:
    def __init__(self):
        self.db = Database()
        self.migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Ensure the migrations table exists"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                migration_file VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def _get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        result = self.db.query("SELECT migration_file FROM migrations ORDER BY id")
        return [row['migration_file'] for row in result] if result else []

    def _get_migration_files(self) -> List[str]:
        """Get sorted list of migration files"""
        files = [f for f in os.listdir(self.migrations_dir) 
                if f.endswith('.py') and f != '__init__.py']
        return sorted(files)

    def _load_migration_module(self, filename: str):
        """Load a migration module dynamically"""
        filepath = os.path.join(self.migrations_dir, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def migrate(self, direction: str = 'up'):
        """Run all pending migrations"""
        applied = self._get_applied_migrations()
        files = self._get_migration_files()
        
        if direction == 'up':
            to_apply = [f for f in files if f not in applied]
            for file in to_apply:
                print(f"Applying migration: {file}")
                module = self._load_migration_module(file)
                self.db.execute(module.up())
                self.db.execute(
                    "INSERT INTO migrations (migration_file) VALUES (%s)",
                    (file,)
                )
                print(f"Applied migration: {file}")
        
        elif direction == 'down':
            to_rollback = [f for f in reversed(files) if f in applied]
            if to_rollback:
                latest = to_rollback[0]
                print(f"Rolling back migration: {latest}")
                module = self._load_migration_module(latest)
                self.db.execute(module.down())
                self.db.execute(
                    "DELETE FROM migrations WHERE migration_file = %s",
                    (latest,)
                )
                print(f"Rolled back migration: {latest}")

    def create_migration(self, name: str):
        """Create a new migration file"""
        files = self._get_migration_files()
        next_num = '0001' if not files else str(int(files[-1][:4]) + 1).zfill(4)
        filename = f"{next_num}_{name}.py"
        filepath = os.path.join(self.migrations_dir, filename)
        
        template = '''def up():
    return """
    -- Add your UP migration SQL here
    """

def down():
    return """
    -- Add your DOWN migration SQL here
    """
'''
        with open(filepath, 'w') as f:
            f.write(template)
        print(f"Created migration file: {filename}") 