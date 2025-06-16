from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import asyncio
from typing import Dict, List
from datetime import datetime
from io import BytesIO
import textwrap
import uvicorn
import logging

from database import Database
from auth import AuthManager
from agents import AgentManager
from chat import ChatManager
from payments import PaymentManager
from websocket_handler import WebSocketManager
from admin import AdminManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Agencore API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
db = Database()
auth_manager = AuthManager(db)
agent_manager = AgentManager()
chat_manager = ChatManager(db)
payment_manager = PaymentManager(db)
websocket_manager = WebSocketManager()
admin_manager = AdminManager(db)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    await db.init_database()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# Auth endpoints
@app.post("/api/auth/register")
async def register(request: Request):
    data = await request.json()
    try:
        user = await auth_manager.register(data.get("email"), data.get("password"), data.get("username"))
        await db.log_activity(user["id"], "user_registration", {"email": data.get("email")})
        return {"user": user, "success": True}
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def login(request: Request):
    data = await request.json()
    try:
        user = await auth_manager.login(data.get("email"), data.get("password"))
        await db.log_activity(user["id"], "user_login", {"email": data.get("email")})
        return {"user": user, "success": True}
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/auth/logout")
async def logout(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    if user_id:
        await db.log_activity(user_id, "user_logout", {})
    return {"success": True}

# Agent endpoints
@app.get("/api/agents")
async def get_agents():
    """Get all available agents"""
    agents = agent_manager.get_all_agents()
    return {"agents": agents}

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get specific agent details"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent": agent}

# Chat endpoints
@app.get("/api/chat/history/{user_id}")
async def get_chat_history(user_id: str):
    """Get user's chat history"""
    try:
        history = await chat_manager.get_user_chat_history(user_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get specific conversation messages"""
    try:
        messages = await chat_manager.get_conversation_messages(conversation_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error fetching conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Payment endpoints
@app.post("/api/payments/create-intent")
async def create_payment_intent(request: Request):
    """Create Stripe payment intent for agent access"""
    data = await request.json()
    try:
        user_id = data.get("user_id")
        agent_id = data.get("agent_id")
        
        if not user_id or not agent_id:
            raise HTTPException(status_code=400, detail="user_id and agent_id required")
        
        # Log payment attempt
        await db.log_activity(user_id, "payment_attempt", {"agent_id": agent_id})
        
        intent = await payment_manager.create_payment_intent(user_id, agent_id)
        return {"client_secret": intent.client_secret}
    except Exception as e:
        logger.error(f"Payment intent error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/verify")
async def verify_payment(request: Request):
    """Verify payment and grant agent access"""
    data = await request.json()
    try:
        user_id = data.get("user_id")
        agent_id = data.get("agent_id")
        payment_intent_id = data.get("payment_intent_id")
        
        success = await payment_manager.verify_payment(user_id, agent_id, payment_intent_id)
        
        if success:
            await db.log_activity(user_id, "payment_success", {
                "agent_id": agent_id, 
                "payment_intent_id": payment_intent_id
            })
            return {"success": True, "message": "Payment verified and access granted"}
        else:
            await db.log_activity(user_id, "payment_failed", {
                "agent_id": agent_id, 
                "payment_intent_id": payment_intent_id
            })
            raise HTTPException(status_code=400, detail="Payment verification failed")
            
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/enhance-prompt")
async def enhance_prompt(request: Request):
    """Enhance user prompt using AI"""
    try:
        data = await request.json()
        prompt = data.get("prompt", "")
        agent_type = data.get("agent_type", "general")
        
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Use OpenAI to enhance the prompt
        import openai
        
        system_prompts = {
            "creative": "You are a creative writing expert. Enhance the user's prompt to be more creative, detailed, and inspiring for creative writing tasks.",
            "code": "You are a programming expert. Enhance the user's prompt to be more specific, technical, and clear for coding tasks.",
            "research": "You are a research expert. Enhance the user's prompt to be more comprehensive, structured, and academic for research tasks.",
            "business": "You are a business consultant. Enhance the user's prompt to be more strategic, actionable, and professional for business analysis.",
            "data": "You are a data science expert. Enhance the user's prompt to be more analytical, precise, and data-focused for data science tasks.",
            "general": "You are an AI assistant expert. Enhance the user's prompt to be clearer, more specific, and more effective for getting better AI responses."
        }
        
        system_prompt = system_prompts.get(agent_type, system_prompts["general"])
        
        try:
            openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": f"{system_prompt} Keep the enhanced prompt concise but more effective. Return only the enhanced prompt without explanations."},
                    {"role": "user", "content": f"Enhance this prompt: {prompt}"}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            enhanced_prompt = response.choices[0].message.content.strip()
            
            return {"enhanced_prompt": enhanced_prompt}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to enhance prompt: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User dashboard endpoints
@app.get("/api/user/{user_id}/dashboard")
async def get_user_dashboard(user_id: str):
    """Get user dashboard data"""
    try:
        dashboard_data = await db.get_user_dashboard_data(user_id)
        return dashboard_data
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{user_id}/accessible-agents")
async def get_accessible_agents(user_id: str):
    """Get agents the user has access to"""
    try:
        accessible_agents = await db.get_user_accessible_agents(user_id)
        return {"agents": accessible_agents}
    except Exception as e:
        logger.error(f"Error fetching accessible agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin endpoints
@app.get("/api/admin/users")
async def get_all_users():
    """Get all users with statistics (Admin only)"""
    try:
        users = await admin_manager.get_all_users()
        return {"users": users}
    except Exception as e:
        logger.error(f"Admin users error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/users/{user_id}")
async def get_user_details(user_id: str):
    """Get detailed user information (Admin only)"""
    try:
        user_details = await admin_manager.get_user_details(user_id)
        if not user_details:
            raise HTTPException(status_code=404, detail="User not found")
        return user_details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user details error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user and all associated data (Admin only)"""
    try:
        success = await admin_manager.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin delete user error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/users/{user_id}/agent-access/{agent_id}")
async def toggle_user_agent_access(user_id: str, agent_id: str):
    """Grant or revoke agent access for a user (Admin only)"""
    try:
        granted = await admin_manager.toggle_user_agent_access(user_id, agent_id)
        action = "granted" if granted else "revoked"
        return {"message": f"Agent access {action}", "granted": granted}
    except Exception as e:
        logger.error(f"Admin toggle access error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_system_stats():
    """Get system statistics (Admin only)"""
    try:
        stats = await admin_manager.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Admin stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/agent-stats")
async def get_agent_usage_stats():
    """Get agent usage statistics (Admin only)"""
    try:
        agent_stats = await admin_manager.get_agent_usage_stats()
        return {"agent_stats": agent_stats}
    except Exception as e:
        logger.error(f"Admin agent stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/cleanup")
async def cleanup_old_data(request: Request):
    """Clean up old data (Admin only)"""
    try:
        data = await request.json()
        days_old = data.get("days_old", 90)
        result = await admin_manager.cleanup_old_data(days_old)
        return {"message": "Cleanup completed", "result": result}
    except Exception as e:
        logger.error(f"Admin cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced agent management endpoints
@app.put("/api/admin/agents/{agent_id}")
async def update_agent(agent_id: str, request: Request):
    """Update an existing agent (Admin only)"""
    try:
        data = await request.json()
        
        # Find and update agent in the agents manager
        for i, agent in enumerate(agent_manager.agents):
            if agent["id"] == agent_id:
                agent_manager.agents[i].update({
                    "name": data.get("name", agent["name"]),
                    "description": data.get("description", agent["description"]),
                    "avatar": data.get("avatar", agent["avatar"]),
                    "category": data.get("category", agent["category"]),
                    "type": data.get("type", agent["type"]),
                    "price": data.get("price", agent["price"]),
                    "prompt": data.get("prompt", agent.get("prompt", "You are a helpful AI assistant.")),
                    "capabilities": data.get("capabilities", agent.get("capabilities", ["AI Assistant"]))
                })
                return {"success": True, "agent": agent_manager.agents[i]}
        
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        logger.error(f"Agent update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/agents/{agent_id}/toggle-status")
async def toggle_agent_status(agent_id: str):
    """Toggle agent active status (Admin only)"""
    try:
        if agent_id in agent_manager.agents:
            agent = agent_manager.agents[agent_id]
            agent["active"] = not agent.get("active", True)
            return {"success": True, "active": agent["active"]}
        
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        logger.error(f"Toggle agent status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent (Admin only)"""
    try:
        if agent_id in agent_manager.agents:
            del agent_manager.agents[agent_id]
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {"success": True, "message": "Agent deleted successfully"}
    except Exception as e:
        logger.error(f"Delete agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/agents")
async def create_agent(request: Request):
    """Create new agent (Admin only)"""
    try:
        data = await request.json()
        
        agent_id = data.get("name", "").lower().replace(" ", "_").replace("-", "_")
        
        new_agent = {
            "id": agent_id,
            "name": data.get("name"),
            "description": data.get("description"),
            "avatar": data.get("avatar", "🤖"),
            "category": data.get("category", "general"),
            "type": data.get("type", "free"),
            "price": data.get("price", 0),
            "capabilities": data.get("capabilities", ["AI Assistant"]),
            "prompt": data.get("prompt", "You are a helpful AI assistant."),
            "active": True
        }
        
        # Add to agent manager
        agent_manager.agents[agent_id] = new_agent
        
        return {"success": True, "agent": new_agent}
    except Exception as e:
        logger.error(f"Agent creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File upload endpoint
@app.post("/api/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload multiple files"""
    try:
        uploaded_files = []
        
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            # Validate file type
            allowed_types = {
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'application/pdf', 'text/plain', 'text/csv',
                'application/json', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type {file.content_type} not allowed"
                )
            
            # Save file
            filename = file.filename or f"upload_{len(uploaded_files)}"
            file_path = os.path.join(upload_dir, filename)
            content = await file.read()
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            uploaded_files.append({
                "filename": filename,
                "size": len(content),
                "type": file.content_type,
                "path": file_path
            })
        
        return {"files": uploaded_files}
    
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# PDF export endpoint
@app.post("/api/export-chat")
async def export_chat(request: Request):
    """Export chat conversation as PDF"""
    try:
        data = await request.json()
        conversation_id = data.get("conversation_id")
        format_type = data.get("format", "pdf")
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="Conversation ID required")
        
        # Get conversation messages
        messages = await db.get_conversation_messages(conversation_id)
        
        if format_type == "pdf":
            # Create PDF using simple text approach
            from io import BytesIO
            import textwrap
            
            buffer = BytesIO()
            
            # Simple text-based PDF creation
            content = f"Chat Conversation Export\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            for msg in messages:
                role = msg['role'].title()
                timestamp = msg.get('timestamp', 'Unknown')
                message_content = msg['content']
                
                content += f"{role} ({timestamp}):\n"
                # Wrap long lines
                wrapped_content = textwrap.fill(message_content, width=80)
                content += f"{wrapped_content}\n\n"
            
            # Convert to bytes
            pdf_bytes = content.encode('utf-8')
            buffer.write(pdf_bytes)
            buffer.seek(0)
            
            return StreamingResponse(
                BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=chat_export.pdf"}
            )
        else:
            # Text export
            content = f"Chat Conversation Export\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            
            for msg in messages:
                role = msg['role'].title()
                timestamp = msg.get('timestamp', 'Unknown')
                content += f"{role} ({timestamp}):\n{msg['content']}\n\n"
            
            return StreamingResponse(
                BytesIO(content.encode('utf-8')),
                media_type="text/plain",
                headers={"Content-Disposition": "attachment; filename=chat_export.txt"}
            )
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_id = message_data.get("user_id")
            agent_id = message_data.get("agent_id")
            message = message_data.get("message")
            conversation_id = message_data.get("conversation_id")
            
            if not all([user_id, agent_id, message]):
                await websocket.send_text(json.dumps({
                    "error": "Missing required fields: user_id, agent_id, message"
                }))
                continue
            
            # Log message sent
            await db.log_activity(user_id, "message_sent", {
                "agent_id": agent_id,
                "conversation_id": conversation_id,
                "message_length": len(message)
            })
            
            # Check if user has access to this agent
            has_access = await db.check_agent_access(user_id, agent_id)
            if not has_access:
                await websocket.send_text(json.dumps({
                    "error": "Access denied to this agent. Payment required."
                }))
                continue
            
            # Save user message to database
            if not conversation_id:
                conversation_id = await chat_manager.create_conversation(user_id, agent_id)
            
            await chat_manager.save_message(conversation_id, "user", message)
            
            # Get agent response and stream it
            agent = agent_manager.get_agent(agent_id)
            
            try:
                full_response = ""
                async for response_chunk in chat_manager.get_agent_response_stream(agent, message):
                    full_response += response_chunk
                    
                    # Send chunk to client
                    await websocket.send_text(json.dumps({
                        "type": "chunk",
                        "content": response_chunk,
                        "conversation_id": conversation_id
                    }))
                
                # Save complete agent response
                await chat_manager.save_message(conversation_id, "assistant", full_response)
                
                # Log message received
                await db.log_activity(user_id, "message_received", {
                    "agent_id": agent_id,
                    "conversation_id": conversation_id,
                    "response_length": len(full_response)
                })
                
                # Send completion signal
                await websocket.send_text(json.dumps({
                    "type": "complete",
                    "conversation_id": conversation_id
                }))
                
            except Exception as e:
                logger.error(f"Agent response error: {str(e)}")
                await websocket.send_text(json.dumps({
                    "error": f"Failed to get agent response: {str(e)}"
                }))
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_text(json.dumps({
            "error": f"Connection error: {str(e)}"
        }))
        websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
