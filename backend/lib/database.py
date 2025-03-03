import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv
import logging

load_dotenv()


class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            self.conn.autocommit = True
        except Exception as e:
            raise

    def query(self, sql: str, params: tuple = None) -> list:
        """Execute a query and return all results"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                try:
                    return cur.fetchall()
                except psycopg2.ProgrammingError:
                    return []
        except Exception as e:
            raise

    def query_one(self, sql: str, params: tuple = None) -> dict:
        """Execute a query and return one result"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                try:
                    return cur.fetchone()
                except psycopg2.ProgrammingError:
                    return None
        except Exception as e:
            raise

    def execute(self, sql: str, params: tuple | list = None, many: bool = False) -> list:
        """Execute a query and optionally return results (for INSERT ... RETURNING)"""
        try:
            with self.conn.cursor() as cur:
                if many:
                    cur.executemany(sql, params)
                else:
                    cur.execute(sql, params)
                try:
                    if many:
                        return cur.fetchall()
                    else:
                        return cur.fetchone()
                except psycopg2.ProgrammingError:
                    # Return None for queries that don't return results
                    return None
        except Exception as e:
            raise

    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()


def db_execute(sql: str, params: tuple = None, many: bool = False) -> list:
    """Execute a query and return results if any (for INSERT ... RETURNING)"""
    db = Database()
    try:
        res = db.execute(sql, params, many)
        return res
    finally:
        db.close()

def db_query(sql: str, params: tuple = None) -> list:
    db = Database()
    res = db.query(sql, params)
    db.close()
    return res

def db_query_one(sql: str, params: tuple = None) -> dict:
    db = Database()
    res = db.query_one(sql, params)
    db.close()
    return res

def db_insert_many(sql: str, params_list: list) -> list:
    """Insert multiple records in a single database call
    
    Args:
        sql: SQL query with placeholders for parameters
        params_list: List of tuples, each containing parameters for one record
        
    Returns:
        Results if the query returns data (like with RETURNING clause)
    """
    db = Database()
    try:
        res = db.execute(sql, params_list, many=True)
        return res
    finally:
        db.close()


def db_bulk_insert(sql: str, records: list, page_size: int = 1000) -> None:
    """Execute a bulk insert using execute_values for much better performance
    
    Args:
        sql: SQL query with %s placeholder for the VALUES clause
        records: List of tuples, each containing parameters for one record
        page_size: Number of records to insert in each batch
    """
    db = Database()
    try:
        with db.conn.cursor() as cur:
            execute_values(cur, sql, records, page_size=page_size)
    finally:
        db.close()