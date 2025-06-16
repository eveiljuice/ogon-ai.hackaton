import os
import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            logger.warning("DATABASE_URL environment variable not set. Database functionality will not work.")
        self.pool = None
    
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.database_url:
            raise ValueError("Database not configured")
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)
        return await self.pool.acquire()
    
    async def release_connection(self, conn):
        """Release connection back to pool"""
        await self.pool.release(conn)
    
    async def init_database(self):
        """Initialize database tables"""
        conn = await self.get_connection()
        try:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR UNIQUE NOT NULL,
                    username VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    stripe_customer_id VARCHAR,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # User agent access table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_agent_access (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    agent_id VARCHAR NOT NULL,
                    payment_intent_id VARCHAR,
                    granted_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, agent_id)
                )
            """)
            
            # Conversations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    agent_id VARCHAR NOT NULL,
                    title VARCHAR DEFAULT 'New Conversation',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Messages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES conversations(id),
                    role VARCHAR NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Activity log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    action VARCHAR NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Agent access table (alternative name for admin compatibility)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_access (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    agent_id VARCHAR NOT NULL,
                    payment_intent_id VARCHAR,
                    granted_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, agent_id)
                )
            """)
            
            # Agent ratings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_ratings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agent_id VARCHAR NOT NULL,
                    user_id UUID REFERENCES users(id),
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    review TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(agent_id, user_id)
                )
            """)
            
            # Activity logs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    action VARCHAR NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            logger.info("Database tables initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise
        finally:
            await self.release_connection(conn)
    
    async def create_user(self, email: str, username: str, password_hash: str) -> Dict:
        """Create a new user"""
        conn = await self.get_connection()
        try:
            user = await conn.fetchrow("""
                INSERT INTO users (email, username, password_hash)
                VALUES ($1, $2, $3)
                RETURNING id, email, username, created_at
            """, email, username, password_hash)
            
            return dict(user)
        finally:
            await self.release_connection(conn)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = await self.get_connection()
        try:
            user = await conn.fetchrow("""
                SELECT id, email, username, password_hash, stripe_customer_id, created_at
                FROM users WHERE email = $1
            """, email)
            
            return dict(user) if user else None
        finally:
            await self.release_connection(conn)
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        conn = await self.get_connection()
        try:
            user = await conn.fetchrow("""
                SELECT id, email, username, stripe_customer_id, created_at
                FROM users WHERE id = $1
            """, user_id)
            
            return dict(user) if user else None
        finally:
            await self.release_connection(conn)
    
    async def grant_agent_access(self, user_id: str, agent_id: str, payment_intent_id: str = None):
        """Grant user access to an agent"""
        conn = await self.get_connection()
        try:
            await conn.execute("""
                INSERT INTO user_agent_access (user_id, agent_id, payment_intent_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, agent_id) DO UPDATE SET
                payment_intent_id = $3,
                granted_at = NOW()
            """, user_id, agent_id, payment_intent_id)
        finally:
            await self.release_connection(conn)
    
    async def check_agent_access(self, user_id: str, agent_id: str) -> bool:
        """Check if user has access to an agent"""
        conn = await self.get_connection()
        try:
            # Free agents are always accessible
            free_agents = ["creative-writer", "code-helper", "research-assistant"]
            if agent_id in free_agents:
                return True
            
            # Check paid agent access
            access = await conn.fetchrow("""
                SELECT id FROM user_agent_access
                WHERE user_id = $1 AND agent_id = $2
            """, user_id, agent_id)
            
            return access is not None
        finally:
            await self.release_connection(conn)
    
    async def create_conversation(self, user_id: str, agent_id: str, title: str = "New Conversation") -> str:
        """Create a new conversation"""
        conn = await self.get_connection()
        try:
            conversation = await conn.fetchrow("""
                INSERT INTO conversations (user_id, agent_id, title)
                VALUES ($1, $2, $3)
                RETURNING id
            """, user_id, agent_id, title)
            
            return str(conversation['id'])
        finally:
            await self.release_connection(conn)
    
    async def save_message(self, conversation_id: str, role: str, content: str):
        """Save a message to a conversation"""
        conn = await self.get_connection()
        try:
            await conn.execute("""
                INSERT INTO messages (conversation_id, role, content)
                VALUES ($1, $2, $3)
            """, conversation_id, role, content)
            
            # Update conversation timestamp
            await conn.execute("""
                UPDATE conversations SET updated_at = NOW()
                WHERE id = $1
            """, conversation_id)
        finally:
            await self.release_connection(conn)
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages in a conversation"""
        conn = await self.get_connection()
        try:
            messages = await conn.fetch("""
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
            """, conversation_id)
            
            return [dict(msg) for msg in messages]
        finally:
            await self.release_connection(conn)
    
    async def get_user_chat_history(self, user_id: str) -> List[Dict]:
        """Get user's chat history grouped by agent"""
        conn = await self.get_connection()
        try:
            conversations = await conn.fetch("""
                SELECT 
                    c.id,
                    c.agent_id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = $1
                GROUP BY c.id, c.agent_id, c.title, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC
            """, user_id)
            
            return [dict(conv) for conv in conversations]
        finally:
            await self.release_connection(conn)
    
    async def log_activity(self, user_id: str, action: str, metadata: Dict = None):
        """Log user activity"""
        conn = await self.get_connection()
        try:
            await conn.execute("""
                INSERT INTO activity_logs (user_id, action, metadata)
                VALUES ($1, $2, $3)
            """, user_id, action, json.dumps(metadata) if metadata else None)
        finally:
            await self.release_connection(conn)
    
    async def get_user_dashboard_data(self, user_id: str) -> Dict:
        """Get user dashboard statistics"""
        conn = await self.get_connection()
        try:
            # Total messages sent
            total_messages = await conn.fetchval("""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = $1 AND m.role = 'user'
            """, user_id)
            
            # Messages per agent
            agent_stats = await conn.fetch("""
                SELECT 
                    c.agent_id,
                    COUNT(m.id) as message_count
                FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = $1 AND m.role = 'user'
                GROUP BY c.agent_id
            """, user_id)
            
            # Last activity
            last_activity = await conn.fetchrow("""
                SELECT created_at FROM activity_logs
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, user_id)
            
            # Accessible paid agents
            paid_agents = await conn.fetch("""
                SELECT agent_id, granted_at FROM user_agent_access
                WHERE user_id = $1
            """, user_id)
            
            return {
                "total_messages": total_messages or 0,
                "agent_interactions": {dict(stat)['agent_id']: dict(stat)['message_count'] for stat in agent_stats},
                "last_activity": last_activity['created_at'] if last_activity else None,
                "accessible_paid_agents": [dict(agent) for agent in paid_agents]
            }
        finally:
            await self.release_connection(conn)
    
    async def get_user_accessible_agents(self, user_id: str) -> List[str]:
        """Get list of agents user has access to"""
        conn = await self.get_connection()
        try:
            # Free agents
            free_agents = ["creative-writer", "code-helper", "research-assistant"]
            
            # Paid agents user has access to
            paid_agents = await conn.fetch("""
                SELECT agent_id FROM user_agent_access
                WHERE user_id = $1
            """, user_id)
            
            accessible_agents = free_agents + [dict(agent)['agent_id'] for agent in paid_agents]
            return accessible_agents
        finally:
            await self.release_connection(conn)
