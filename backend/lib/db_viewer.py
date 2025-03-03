#!/usr/bin/env python3

from backend.lib.database import db_query
from tabulate import tabulate
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def format_table(rows, title):
    """Format a table with tabulate for better readability"""
    if not rows:
        return f"\n=== {title} (0 rows) ===\nNo data found.\n"
    
    headers = rows[0].keys()
    data = [[row[col] for col in headers] for row in rows]
    
    table = tabulate(data, headers=headers, tablefmt="grid")
    return f"\n=== {title} ({len(rows)} rows) ===\n{table}\n"

def preview_database():
    """Fetch and display sample data from key tables"""
    # Get table structure for user_subscriptions to check for column existence
    user_sub_columns = db_query("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'user_subscriptions'
        ORDER BY ordinal_position
    """)
    
    print("\n=== Table Structure: user_subscriptions ===")
    columns = [col['column_name'] for col in user_sub_columns]
    print(", ".join(columns))
    
    # Users table
    users = db_query("SELECT * FROM users ORDER BY id LIMIT 5")
    print(format_table(users, "Users"))
    
    # User subscriptions
    user_subscriptions = db_query("SELECT * FROM user_subscriptions ORDER BY id LIMIT 5")
    print(format_table(user_subscriptions, "User Subscriptions"))
    
    # Quota usage
    quota_usage = db_query("SELECT * FROM quota_usage ORDER BY id LIMIT 5")
    print(format_table(quota_usage, "Quota Usage"))
    
    # Subscription plans
    subscription_plans = db_query("SELECT * FROM subscription_plans ORDER BY id LIMIT 5")
    print(format_table(subscription_plans, "Subscription Plans"))
    
    # Predictions
    predictions = db_query("SELECT * FROM predictions ORDER BY id LIMIT 5")
    print(format_table(predictions, "Recent Predictions"))

if __name__ == "__main__":
    preview_database() 