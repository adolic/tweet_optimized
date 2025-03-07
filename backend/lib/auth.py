from datetime import datetime, timedelta
import random
import string
from secrets import token_urlsafe
import resend
import os
from dotenv import load_dotenv
from .database import db_query, db_query_one, db_execute
import logging
from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from pydantic import BaseModel

load_dotenv()
resend.api_key = os.getenv('RESEND_API_KEY')

class LoginRequest(BaseModel):
    email: str

class VerifyRequest(BaseModel):
    email: str
    code: str | None = None
    magic_link_token: str | None = None

class Auth:
    def __init__(self):
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost')
        self.max_attempts_per_hour = 5
        self.router = APIRouter()
        self.setup_routes()

    def setup_routes(self):
        """Set up the FastAPI routes for authentication."""
        self.router.post("/auth/login")(self.login_endpoint)
        self.router.post("/auth/verify")(self.verify_endpoint)
        self.router.get("/auth/me")(self.get_user_data_endpoint)

    def get_or_create_user(self, email: str) -> int:
        """Get user ID or create if doesn't exist."""
        user = db_query_one("SELECT id FROM users WHERE email = %s", (email,))
        if user:
            return user['id']
        
        return db_query_one(
            "INSERT INTO users (email) VALUES (%s) RETURNING id",
            (email,)
        )['id']

    def check_email_rate_limit(self, email: str) -> tuple[bool, str | None]:
        """Check if user has exceeded email rate limit.
        Returns (is_limited, error_message)"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        count = db_query_one("""
            SELECT COUNT(*) as count
            FROM login_attempts 
            WHERE email = %s 
            AND created_at > %s
        """, (email, one_hour_ago))['count']

        if count >= self.max_attempts_per_hour:
            return True, f"Too many login attempts. Please wait and try again in a few minutes. Maximum {self.max_attempts_per_hour} emails per hour."
        return False, None

    def create_login_attempt(self, email: str) -> dict:
        """Create a new login attempt with magic link."""
        logger = logging.getLogger(__name__)
        
        # Check rate limit for emails
        is_limited, error_msg = self.check_email_rate_limit(email)
        if is_limited:
            return {"error": error_msg}

        magic_link_token = token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)

        db_execute("""
            INSERT INTO login_attempts 
            (email, magic_link_token, expires_at)
            VALUES (%s, %s, %s)
        """, (email, magic_link_token, expires_at))

        # Send email
        try:
            magic_link = f"{self.frontend_url}/auth/verify/{magic_link_token}?email={email}"
            logger.info(f"Sending login email to {email} with magic link: {magic_link}")
            
            # Log Resend API key status (masked for security)
            api_key = resend.api_key
            if api_key:
                masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "***"
                logger.info(f"Resend API key is set: {masked_key}")
            else:
                logger.error("Resend API key is not set")
            
            response = resend.Emails.send({
                "from": "Tweet-Optimize Auth <auth@tweet-optimize.com>",
                "to": [email],
                "subject": "Log in to Tweet-Optimize",
                "html": f"""
                    <h2>Login to Tweet-Optimize</h2>
                    <p>Click the button below to log in to your account. This link will expire in 1 hour.</p>
                    <p style="margin: 2em 0;">
                        <a href="{magic_link}" 
                           style="background-color: #5db1ef; color: white; padding: 12px 24px; 
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Log in to Tweet-Optimize
                        </a>
                    </p>
                    <p style="color: #666; font-size: 0.9em;">
                        If the button doesn't work, you can copy and paste this link into your browser:<br>
                        {magic_link}
                    </p>
                """
            })
            logger.info(f"Email sent successfully: {response}")
            return {"success": True, "message": "Login email sent"}
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Failed to send email: {str(e)}\n{error_traceback}")
            return {"error": f"Failed to send email: {str(e)}"}

    def verify_attempt(self, email: str, code: str = None, magic_link_token: str = None) -> dict:
        """Verify a login attempt using magic link."""
        if not magic_link_token:
            return {"error": "No magic link token provided"}

        # Use a transaction to ensure atomicity
        db = db_query_one("""
            BEGIN;
            
            -- Check if this is a valid and unused attempt
            SELECT id
            FROM login_attempts
            WHERE email = %s
            AND magic_link_token = %s
            AND NOT used
            AND expires_at > NOW()
            FOR UPDATE;  -- Lock the row
        """, (email, magic_link_token))

        if not db:
            db_execute("ROLLBACK;")
            return {"error": "Invalid or expired login link"}

        try:
            # Mark as used
            db_execute("""
                UPDATE login_attempts
                SET used = TRUE
                WHERE email = %s
                AND magic_link_token = %s;
            """, (email, magic_link_token))

            # Create session
            user_id = self.get_or_create_user(email)
            session_token = token_urlsafe(32)
            
            db_execute("""
                INSERT INTO sessions (user_id, token)
                VALUES (%s, %s);
                
                COMMIT;
            """, (user_id, session_token))

            # Get user data
            user_data = db_query_one("""
                SELECT email, is_admin
                FROM users
                WHERE id = %s
            """, (user_id,))

            return {
                "success": True,
                "session_token": session_token,
                "user": user_data
            }
        except Exception as e:
            db_execute("ROLLBACK;")
            return {"error": f"Verification failed: {str(e)}"}

    def get_user_by_session(self, token: str) -> dict:
        """Get user info from session token."""
        return db_query_one("""
            SELECT u.* FROM users u
            INNER JOIN sessions s ON s.user_id = u.id
            WHERE s.token = %s
        """, (token,))

    def is_valid_session(self, token: str) -> bool:
        """Check if a session token is valid."""
        if not token:
            return False
        
        user = self.get_user_by_session(token)
        return user is not None

    def logout(self, token: str) -> bool:
        """Remove a session."""
        db_execute("DELETE FROM sessions WHERE token = %s", (token,))
        return True

    async def get_current_user(self, request: Request):
        """Get the current authenticated user or raise 401 error."""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=401, 
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = auth_header.split(' ')[1]
        user = self.get_user_by_session(token)
        
        if not user:
            raise HTTPException(
                status_code=401, 
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user

    async def get_optional_user(self, request: Request):
        """Get the current user or return None if not authenticated."""
        try:
            return await self.get_current_user(request)
        except HTTPException:
            return None

    async def login_endpoint(self, request: LoginRequest):
        """Handle login request by sending magic link and code."""
        try:
            result = self.create_login_attempt(request.email)
            
            # Check if result is a dictionary and contains an "error" key
            if isinstance(result, dict) and "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            # If result is not a dictionary or doesn't have expected format
            if not isinstance(result, dict) or "success" not in result:
                raise HTTPException(status_code=500, detail="Invalid response format from authentication service")
                
            return result
        except HTTPException:
            # Re-raise HTTP exceptions as they are already formatted properly
            raise
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logging.error(f"Error in login: {str(e)}\n{error_traceback}")
            raise HTTPException(status_code=500, detail=str(e) or "An unknown error occurred")

    async def verify_endpoint(self, request: VerifyRequest):
        """Verify a login attempt using either code or magic link."""
        try:
            result = self.verify_attempt(
                email=request.email,
                code=request.code,
                magic_link_token=request.magic_link_token
            )
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            return result
        except Exception as e:
            logging.error(f"Error in verify: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_user_data_endpoint(self, request: Request):
        """Get user data from session token."""
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = auth_header.split(' ')[1]
            user = self.get_user_by_session(token)
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid session token")
                
            return {"user": user}
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error in get_user_data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) 