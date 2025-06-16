import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, database):
        self.db = database
        self.jwt_secret = os.getenv("JWT_SECRET", "agencore-secret-key-change-in-production")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_access_token(self, user_id: str, email: str) -> str:
        """Create a JWT access token"""
        expire = datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    async def register(self, email: str, password: str, username: str) -> Dict:
        """Register a new user"""
        if not email or not password or not username:
            raise ValueError("Email, password, and username are required")
        
        try:
            # Check if user already exists
            existing_user = await self.db.get_user_by_email(email)
            if existing_user:
                raise ValueError("User with this email already exists")
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user
            user = await self.db.create_user(email, username, password_hash)
            
            # Grant access to free agents
            free_agents = ["creative-writer", "code-helper", "research-assistant"]
            for agent_id in free_agents:
                await self.db.grant_agent_access(str(user['id']), agent_id)
            
            # Create access token
            access_token = self.create_access_token(str(user['id']), email)
            
            return {
                "id": str(user['id']),
                "email": user['email'],
                "username": user['username'],
                "created_at": user['created_at'],
                "access_token": access_token
            }
        except ValueError as e:
            if "Database not configured" in str(e):
                # Create temporary user for demo purposes
                import uuid
                from datetime import datetime
                
                user_id = str(uuid.uuid4())
                access_token = self.create_access_token(user_id, email)
                
                return {
                    "id": user_id,
                    "email": email,
                    "username": username,
                    "created_at": datetime.now().isoformat(),
                    "access_token": access_token
                }
            raise
    
    async def login(self, email: str, password: str) -> Dict:
        """Login a user"""
        if not email or not password:
            raise ValueError("Email and password are required")
        
        # Get user by email
        user = await self.db.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not self.verify_password(password, user['password_hash']):
            raise ValueError("Invalid email or password")
        
        # Create access token
        access_token = self.create_access_token(str(user['id']), email)
        
        return {
            "id": str(user['id']),
            "email": user['email'],
            "username": user['username'],
            "created_at": user['created_at'],
            "access_token": access_token
        }
    
    async def get_current_user(self, token: str) -> Optional[Dict]:
        """Get current user from token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user = await self.db.get_user_by_id(payload['user_id'])
        return user
