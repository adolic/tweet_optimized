from google.oauth2 import id_token
from google.auth.transport import requests
import os
from typing import Optional
from .database import db_query_one, db_execute
from fastapi import HTTPException
from secrets import token_urlsafe

class GoogleOAuth:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")

    async def verify_google_token(self, token: str) -> dict:
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.client_id
            )

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            return {
                'email': idinfo['email'],
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'oauth_id': idinfo['sub'],
                'oauth_provider': 'google'
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def get_or_create_user(self, user_info: dict) -> tuple[int, str]:
        """Get existing user or create a new one and return (user_id, session_token)"""
        # Check if user exists by OAuth ID
        user = db_query_one("""
            SELECT id 
            FROM users 
            WHERE oauth_provider = %s AND oauth_id = %s
        """, (user_info['oauth_provider'], user_info['oauth_id']))

        if not user:
            # Check if user exists by email
            user = db_query_one("SELECT id FROM users WHERE email = %s", (user_info['email'],))
            
            if user:
                # Update existing user with OAuth info
                db_execute("""
                    UPDATE users 
                    SET oauth_provider = %s,
                        oauth_id = %s,
                        name = %s,
                        picture_url = %s
                    WHERE id = %s
                """, (
                    user_info['oauth_provider'],
                    user_info['oauth_id'],
                    user_info.get('name'),
                    user_info.get('picture'),
                    user['id']
                ))
            else:
                # Create new user
                user = db_query_one("""
                    INSERT INTO users (
                        email, 
                        oauth_provider, 
                        oauth_id, 
                        name, 
                        picture_url
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_info['email'],
                    user_info['oauth_provider'],
                    user_info['oauth_id'],
                    user_info.get('name'),
                    user_info.get('picture')
                ))

        # Create session
        session_token = token_urlsafe(32)
        db_execute("""
            INSERT INTO sessions (user_id, token)
            VALUES (%s, %s)
        """, (user['id'], session_token))

        return user['id'], session_token 