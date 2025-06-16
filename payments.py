import os
import stripe
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PaymentManager:
    def __init__(self, database):
        self.db = database
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "your-stripe-secret-key")
        
        if not stripe.api_key or stripe.api_key == "your-stripe-secret-key":
            logger.warning("Stripe secret key not configured. Payment functionality will not work.")
    
    async def create_payment_intent(self, user_id: str, agent_id: str) -> stripe.PaymentIntent:
        """Create a Stripe payment intent for agent access"""
        try:
            from agents import AgentManager
            agent_manager = AgentManager()
            
            agent = agent_manager.get_agent(agent_id)
            if not agent or agent["type"] != "paid":
                raise ValueError("Invalid paid agent")
            
            amount = agent.get("price", 0)
            if amount <= 0:
                raise ValueError("Invalid agent price")
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="usd",
                metadata={
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "agent_name": agent["name"]
                },
                description=f"Access to {agent['name']} AI Agent"
            )
            
            return intent
            
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    async def verify_payment(self, user_id: str, agent_id: str, payment_intent_id: str) -> bool:
        """Verify payment and grant agent access"""
        try:
            # Retrieve payment intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Check if payment was successful
            if intent.status == "succeeded":
                # Verify the metadata matches
                metadata = intent.metadata
                if (metadata.get("user_id") == user_id and 
                    metadata.get("agent_id") == agent_id):
                    
                    # Grant agent access
                    await self.db.grant_agent_access(user_id, agent_id, payment_intent_id)
                    
                    logger.info(f"Payment verified and access granted: user={user_id}, agent={agent_id}")
                    return True
                else:
                    logger.warning(f"Payment metadata mismatch: {metadata}")
                    return False
            else:
                logger.warning(f"Payment not successful: status={intent.status}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return False
    
    async def get_user_payments(self, user_id: str) -> List[Dict]:
        """Get user's payment history"""
        try:
            # This would typically query Stripe for payment history
            # For now, we'll get it from our database
            conn = await self.db.get_connection()
            try:
                payments = await conn.fetch("""
                    SELECT agent_id, payment_intent_id, granted_at
                    FROM user_agent_access
                    WHERE user_id = $1 AND payment_intent_id IS NOT NULL
                    ORDER BY granted_at DESC
                """, user_id)
                
                return [dict(payment) for payment in payments]
            finally:
                await self.db.release_connection(conn)
                
        except Exception as e:
            logger.error(f"Error fetching user payments: {str(e)}")
            return []
