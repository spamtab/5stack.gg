from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict
import asyncio
import json
from sqlalchemy import text

from database import engine
from models import Base
from routes import router as api_router

class ConnectionManager:
    def __init__(self):
        # uid -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Track which users are in which parties: party_id -> Set[user_id]
        self.party_members: Dict[int, set] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Clean up party membership tracking
        for party_id, members in list(self.party_members.items()):
            if user_id in members:
                members.discard(user_id)
                if not members:
                    del self.party_members[party_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                print(f"[WS] Error sending to {user_id}: {e}")
                self.disconnect(user_id)
    
    async def send_to_party(self, message: dict, party_id: int):
        """Send message to all members of a party"""
        if party_id in self.party_members:
            import asyncio
            tasks = [
                self.send_personal_message(message, user_id)
                for user_id in self.party_members[party_id]
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def add_to_party(self, user_id: str, party_id: int):
        """Track user membership in a party"""
        if party_id not in self.party_members:
            self.party_members[party_id] = set()
        self.party_members[party_id].add(user_id)
    
    def remove_from_party(self, user_id: str, party_id: int):
        """Remove user from party tracking"""
        if party_id in self.party_members:
            self.party_members[party_id].discard(user_id)
            if not self.party_members[party_id]:
                del self.party_members[party_id]
            
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (for MVP, we create all tables here)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS looking_for_party BOOLEAN NOT NULL DEFAULT FALSE"))
        await conn.execute(text("UPDATE users SET looking_for_party = FALSE WHERE looking_for_party IS NULL"))
    yield

app = FastAPI(title="Valorant Matchmaking API", lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://spamtab.github.io"], # TODO: replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint with JWT authentication via query param.
    URL: ws://api/ws?token=<firebase-jwt>
    """
    user_id = None
    try:
        # Import auth here to avoid circular imports
        from auth import verify_token_ws
        from database import AsyncSessionLocal
        from sqlalchemy.future import select
        import models
        import time
        
        # Verify token
        decoded_token = await verify_token_ws(token)
        user_id = decoded_token.get("uid")
        
        if not user_id:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        
        await manager.connect(websocket, user_id)
        print(f"[WS] User {user_id} connected")
        
        # Send connected confirmation
        await manager.send_personal_message({
            "type": "connected",
            "uid": user_id,
            "timestamp": int(time.time() * 1000)
        }, user_id)
        
        # Sync initial party state
        async with AsyncSessionLocal() as db:
            user_result = await db.execute(select(models.User).where(models.User.id == user_id))
            user = user_result.scalars().first()
            if user and user.party_id:
                manager.add_to_party(user_id, user.party_id)
        
        # Message loop
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": int(time.time() * 1000)})
            elif message.get("type") == "disconnect":
                break
                
    except WebSocketDisconnect:
        print(f"[WS] User {user_id} disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        if user_id:
            await websocket.close(code=1011, reason="Internal error")
    finally:
        if user_id:
            manager.disconnect(user_id)

@app.get("/")
def read_root():
    return {"message": "Valorant Matchmaking API is running"}
