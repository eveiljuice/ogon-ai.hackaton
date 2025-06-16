from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta

class AdminManager:
    def __init__(self, database):
        self.database = database
    
    async def get_all_users(self) -> List[Dict]:
        """Get all users with their statistics"""
        conn = await self.database.get_connection()
        try:
            # Get users with basic info
            users_query = """
                SELECT u.id, u.email, u.username, u.created_at,
                       COUNT(DISTINCT c.id) as conversation_count,
                       COUNT(DISTINCT m.id) as message_count,
                       COUNT(DISTINCT aa.agent_id) as accessible_agents_count
                FROM users u
                LEFT JOIN conversations c ON u.id = c.user_id
                LEFT JOIN messages m ON c.id = m.conversation_id
                LEFT JOIN user_agent_access aa ON u.id = aa.user_id
                GROUP BY u.id, u.email, u.username, u.created_at
                ORDER BY u.created_at DESC
            """
            users = await conn.fetch(users_query)
            
            # Get last activity for each user
            for user in users:
                activity_query = """
                    SELECT MAX(created_at) as last_activity
                    FROM activity_log
                    WHERE user_id = $1
                """
                activity = await conn.fetchrow(activity_query, user['id'])
                user_dict = dict(user)
                user_dict['last_activity'] = activity['last_activity'] if activity else None
            
            return [dict(user) for user in users]
        finally:
            await self.database.release_connection(conn)
    
    async def get_user_details(self, user_id: str) -> Optional[Dict]:
        """Get detailed information about a specific user"""
        conn = await self.database.get_connection()
        try:
            # Get user basic info
            user_query = """
                SELECT id, email, username, created_at
                FROM users
                WHERE id = $1
            """
            user = await conn.fetchrow(user_query, user_id)
            if not user:
                return None
            
            user_dict = dict(user)
            
            # Get user's agent access
            access_query = """
                SELECT agent_id, granted_at, payment_intent_id
                FROM user_agent_access
                WHERE user_id = $1
                ORDER BY granted_at DESC
            """
            access = await conn.fetch(access_query, user_id)
            user_dict['agent_access'] = [dict(a) for a in access]
            
            # Get user's conversations
            conv_query = """
                SELECT c.id, c.agent_id, c.title, c.created_at,
                       COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = $1
                GROUP BY c.id, c.agent_id, c.title, c.created_at
                ORDER BY c.created_at DESC
                LIMIT 10
            """
            conversations = await conn.fetch(conv_query, user_id)
            user_dict['recent_conversations'] = [dict(c) for c in conversations]
            
            # Get activity log
            activity_query = """
                SELECT action, metadata, created_at
                FROM activity_log
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 20
            """
            activities = await conn.fetch(activity_query, user_id)
            user_dict['recent_activities'] = [dict(a) for a in activities]
            
            return user_dict
        finally:
            await self.database.release_connection(conn)
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and all associated data"""
        conn = await self.database.get_connection()
        try:
            # Delete in correct order due to foreign key constraints
            await conn.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = $1)", user_id)
            await conn.execute("DELETE FROM conversations WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM user_agent_access WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM activity_log WHERE user_id = $1", user_id)
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            
            return result == "DELETE 1"
        finally:
            await self.database.release_connection(conn)
    
    async def toggle_user_agent_access(self, user_id: str, agent_id: str) -> bool:
        """Grant or revoke access to an agent for a user"""
        conn = await self.database.get_connection()
        try:
            # Check if user already has access
            check_query = """
                SELECT id FROM user_agent_access
                WHERE user_id = $1 AND agent_id = $2
            """
            existing = await conn.fetchrow(check_query, user_id, agent_id)
            
            if existing:
                # Revoke access
                await conn.execute("DELETE FROM user_agent_access WHERE user_id = $1 AND agent_id = $2", user_id, agent_id)
                return False
            else:
                # Grant access
                await conn.execute("""
                    INSERT INTO user_agent_access (user_id, agent_id, granted_at)
                    VALUES ($1, $2, $3)
                """, user_id, agent_id, datetime.utcnow())
                return True
        finally:
            await self.database.release_connection(conn)
    
    async def get_system_stats(self) -> Dict:
        """Get overall system statistics"""
        conn = await self.database.get_connection()
        try:
            stats = {}
            
            # Total users
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            stats['total_users'] = total_users
            
            # Total conversations
            total_conversations = await conn.fetchval("SELECT COUNT(*) FROM conversations")
            stats['total_conversations'] = total_conversations
            
            # Total messages
            total_messages = await conn.fetchval("SELECT COUNT(*) FROM messages")
            stats['total_messages'] = total_messages
            
            # Active users (last 7 days)
            active_users = await conn.fetchval("""
                SELECT COUNT(DISTINCT user_id) 
                FROM activity_log 
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            stats['active_users_7d'] = active_users
            
            # Most popular agents
            popular_agents = await conn.fetch("""
                SELECT agent_id, COUNT(*) as usage_count
                FROM conversations
                GROUP BY agent_id
                ORDER BY usage_count DESC
                LIMIT 5
            """)
            stats['popular_agents'] = [dict(a) for a in popular_agents]
            
            # Daily message counts (last 7 days)
            daily_messages = await conn.fetch("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM messages
                WHERE created_at > NOW() - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            stats['daily_messages'] = [dict(d) for d in daily_messages]
            
            # Paid agent access statistics
            paid_access = await conn.fetch("""
                SELECT agent_id, COUNT(*) as access_count
                FROM user_agent_access
                WHERE payment_intent_id IS NOT NULL
                GROUP BY agent_id
                ORDER BY access_count DESC
            """)
            stats['paid_agent_access'] = [dict(p) for p in paid_access]
            
            return stats
        finally:
            await self.database.release_connection(conn)
    
    async def get_agent_usage_stats(self) -> List[Dict]:
        """Get detailed usage statistics for each agent"""
        conn = await self.database.get_connection()
        try:
            agent_stats = await conn.fetch("""
                SELECT 
                    c.agent_id,
                    COUNT(DISTINCT c.id) as conversation_count,
                    COUNT(DISTINCT c.user_id) as unique_users,
                    COUNT(m.id) as total_messages,
                    AVG(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) as avg_response_rate,
                    MAX(c.created_at) as last_used
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.agent_id
                ORDER BY conversation_count DESC
            """)
            
            return [dict(stat) for stat in agent_stats]
        finally:
            await self.database.release_connection(conn)
    
    async def cleanup_old_data(self, days_old: int = 90) -> Dict:
        """Clean up old conversations and messages"""
        conn = await self.database.get_connection()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Get old conversation IDs
            old_conversations = await conn.fetch("""
                SELECT id FROM conversations 
                WHERE created_at < $1
            """, cutoff_date)
            
            old_conv_ids = [conv['id'] for conv in old_conversations]
            
            if old_conv_ids:
                # Delete old messages
                deleted_messages = await conn.execute("""
                    DELETE FROM messages 
                    WHERE conversation_id = ANY($1)
                """, old_conv_ids)
                
                # Delete old conversations
                deleted_conversations = await conn.execute("""
                    DELETE FROM conversations 
                    WHERE created_at < $1
                """, cutoff_date)
                
                # Clean up old activity logs
                deleted_activities = await conn.execute("""
                    DELETE FROM activity_log 
                    WHERE created_at < $1
                """, cutoff_date)
                
                return {
                    'deleted_conversations': len(old_conv_ids),
                    'deleted_messages': int(deleted_messages.split()[-1]),
                    'deleted_activities': int(deleted_activities.split()[-1])
                }
            
            return {'deleted_conversations': 0, 'deleted_messages': 0, 'deleted_activities': 0}
        finally:
            await self.database.release_connection(conn)