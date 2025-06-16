import os
import openai
import asyncio
import logging

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, database):
        self.db = database
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OpenAI API key not configured. Chat functionality will not work.")
            self.openai_client = None
        else:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.model = "gpt-4o"
    
    async def create_conversation(self, user_id, agent_id):
        """Create a new conversation"""
        return await self.db.create_conversation(user_id, agent_id)
    
    async def save_message(self, conversation_id, role, content):
        """Save a message to the conversation"""
        await self.db.save_message(conversation_id, role, content)
    
    async def get_conversation_messages(self, conversation_id):
        """Get all messages in a conversation"""
        return await self.db.get_conversation_messages(conversation_id)
    
    async def get_user_chat_history(self, user_id):
        """Get user's chat history"""
        return await self.db.get_user_chat_history(user_id)
    
    async def get_agent_response_stream(self, agent, user_message):
        """Get streaming response from AI agent"""
        try:
            if not self.openai_client:
                yield "AI chat is not available. Please configure OpenAI API key."
                return
                
            system_prompt = agent.get("system_prompt", "You are a helpful AI assistant.")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Create streaming chat completion
            stream = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                max_tokens=1000,
                temperature=0.7
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield content
                    # Add small delay to simulate realistic streaming
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Error generating agent response: {str(e)}")
            yield f"Sorry, I encountered an error: {str(e)}"
    
    async def get_agent_response(self, agent, user_message, conversation_history=None):
        """Get complete response from AI agent"""
        try:
            if not self.openai_client:
                return "AI chat is not available. Please configure OpenAI API key."
                
            system_prompt = agent.get("system_prompt", "You are a helpful AI assistant.")
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages for context
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content or "No response generated"
            
        except Exception as e:
            logger.error(f"Error generating agent response: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"