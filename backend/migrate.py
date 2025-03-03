import sys
from lib.migration_manager import MigrationManager

def print_usage():
    print("""
Usage: python migrate.py <command> [args]

Commands:
    up              - Run all pending migrations
    down            - Rollback the latest migration
    create <name>   - Create a new migration file
    """)

def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    manager = MigrationManager()
    command = sys.argv[1]

    if command == 'up':
        manager.migrate('up')
    elif command == 'down':
        manager.migrate('down')
    elif command == 'create' and len(sys.argv) == 3:
        manager.create_migration(sys.argv[2])
    else:
        print_usage()

if __name__ == '__main__':
    main() 