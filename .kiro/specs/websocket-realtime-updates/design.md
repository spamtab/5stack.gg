# Technical Design: WebSocket Real-Time Updates

## Overview
This document outlines the technical architecture for implementing WebSocket-based real-time updates for the 5stack.gg Valorant matchmaking app.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Tab 1      │    │   Tab 2      │    │   Tab 3      │     │
│  │  (Primary)   │◄───┤ (Secondary)  │◄───┤ (Secondary)  │     │
│  │              │    │              │    │              │     │
│  │ useWebSocket │    │ useWebSocket │    │ useWebSocket │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                   │                   │              │
│         │         BroadcastChannel              │              │
│         │         (keyed by Firebase UID)       │              │
│         │                   │                   │              │
│         └───────────────────┴───────────────────┘              │
│                             │                                   │
│                    WebSocket Connection                         │
│                    (Primary Tab Only)                           │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              │ wss://api.5stack.gg/ws
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                     Backend (FastAPI)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │          ConnectionManager                                 │ │
│  │  {                                                         │ │
│  │    "user-uid-1": WebSocket,                               │ │
│  │    "user-uid-2": WebSocket,                               │ │
│  │    ...                                                     │ │
│  │  }                                                         │ │
│  └────────────────────┬──────────────────────────────────────┘ │
│                       │                                         │
│  ┌────────────────────▼──────────────────────────────────────┐ │
│  │         WebSocket Event Handlers                          │ │
│  │  - on_request_created()                                   │ │
│  │  - on_request_responded()                                 │ │
│  │  - on_party_member_added()                                │ │
│  │  - on_party_member_removed()                              │ │
│  │  - on_party_disbanded()                                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              REST API Routes (existing)                   │ │
│  │  Now trigger WebSocket notifications after DB changes     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
                        PostgreSQL (NeonDB)
```

---

## 2. WebSocket Protocol Design

### 2.1 Connection Lifecycle

**Authentication Flow:**
```
Client                                Server
  │                                     │
  │  1. GET /ws?token=<firebase-jwt>   │
  ├────────────────────────────────────►│
  │                                     │ 2. Verify JWT
  │                                     │    Extract UID
  │                                     │
  │  3. Connection Accepted             │
  │◄────────────────────────────────────┤
  │                                     │
  │  4. Register in ConnectionManager   │
  │    connections[uid] = websocket     │
  │◄────────────────────────────────────┤
  │                                     │
  │  5. Send initial state sync         │
  │◄────────────────────────────────────┤
  │  { type: "connected", uid: "..." }  │
  │                                     │
```

**Heartbeat/Keep-Alive:**
- **Client** sends `{"type": "ping"}` every 30 seconds
- **Server** responds with `{"type": "pong"}` immediately
- If 3 pings fail, client assumes connection is dead → reconnect

**Disconnection:**
- **Normal**: Client closes tab → `onbeforeunload` sends `{"type": "disconnect"}`
- **Abnormal**: Network failure → server detects via ping timeout → cleanup

---

### 2.2 Message Types

#### Client → Server Messages

```typescript
// Keep-alive
{
  type: "ping"
}

// Graceful disconnect
{
  type: "disconnect"
}
```

#### Server → Client Messages

```typescript
// Connection established
{
  type: "connected",
  uid: string,
  timestamp: number
}

// Keep-alive response
{
  type: "pong",
  timestamp: number
}

// Incoming request notification
{
  type: "request_created",
  data: {
    id: number,
    type: "join" | "invite",
    sender: {
      id: string,
      username: string,
      rank: string,
      mood: string,
      agent_priority: string[]
    },
    party_id?: number,
    created_at: string
  }
}

// Request status update
{
  type: "request_responded",
  data: {
    id: number,
    status: "accepted" | "rejected",
    request_type: "join" | "invite"
  }
}

// Party member joined
{
  type: "party_member_added",
  data: {
    party_id: number,
    member: {
      id: string,
      username: string,
      rank: string,
      mood: string,
      agent_priority: string[]
    }
  }
}

// Party member left/removed
{
  type: "party_member_removed",
  data: {
    party_id: number,
    member_id: string,
    reason: "left" | "kicked" | "disbanded"
  }
}

// Party disbanded
{
  type: "party_disbanded",
  data: {
    party_id: number
  }
}

// Player status change
{
  type: "player_status_changed",
  data: {
    user_id: string,
    looking_for_party: boolean
  }
}

// Error
{
  type: "error",
  message: string,
  code?: string
}
```

---

## 3. Frontend Implementation

### 3.1 WebSocket Composable (`useWebSocket.ts`)

```typescript
// frontend/src/composables/useWebSocket.ts
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useAuthStore } from '../stores/authStore'

interface WebSocketMessage {
  type: string
  data?: any
  [key: string]: any
}

export function useWebSocket() {
  const authStore = useAuthStore()
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectDelay = 30000 // 30 seconds
  const isPrimaryTab = ref(false)
  
  let pingInterval: number | undefined
  let reconnectTimeout: number | undefined
  let channel: BroadcastChannel | null = null
  
  // Message handlers
  const messageHandlers = new Map<string, Set<(data: any) => void>>()
  
  const channelName = computed(() => {
    return authStore.user?.uid ? `ws-sync-${authStore.user.uid}` : null
  })
  
  const connect = async () => {
    if (!authStore.user) return
    
    // Check if another tab is already primary
    if (channelName.value) {
      channel = new BroadcastChannel(channelName.value)
      
      // Request primary status
      channel.postMessage({ type: 'primary-check' })
      
      await new Promise(resolve => {
        const timeout = setTimeout(() => {
          // No response = we become primary
          isPrimaryTab.value = true
          resolve(undefined)
        }, 100)
        
        channel!.onmessage = (event) => {
          if (event.data.type === 'primary-exists') {
            clearTimeout(timeout)
            isPrimaryTab.value = false
            resolve(undefined)
          }
        }
      })
      
      // Respond to primary checks from other tabs
      channel.onmessage = (event) => {
        if (event.data.type === 'primary-check' && isPrimaryTab.value) {
          channel!.postMessage({ type: 'primary-exists' })
        } else if (event.data.type === 'ws-message') {
          // Forward WebSocket messages to secondary tabs
          handleMessage(event.data.message)
        }
      }
    }
    
    // Only primary tab creates WebSocket
    if (!isPrimaryTab.value) {
      isConnected.value = true // Treat as connected (via primary)
      return
    }
    
    try {
      const token = await authStore.getToken()
      if (!token) throw new Error('No auth token')
      
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
      ws.value = new WebSocket(`${wsUrl}/ws?token=${token}`)
      
      ws.value.onopen = () => {
        console.log('[WS] Connected')
        isConnected.value = true
        reconnectAttempts.value = 0
        
        // Start ping interval
        pingInterval = window.setInterval(() => {
          if (ws.value?.readyState === WebSocket.OPEN) {
            ws.value.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)
      }
      
      ws.value.onmessage = (event) => {
        const message: WebSocketMessage = JSON.parse(event.data)
        
        // Broadcast to other tabs
        if (channel && isPrimaryTab.value) {
          channel.postMessage({ type: 'ws-message', message })
        }
        
        handleMessage(message)
      }
      
      ws.value.onerror = (error) => {
        console.error('[WS] Error:', error)
      }
      
      ws.value.onclose = () => {
        console.log('[WS] Disconnected')
        isConnected.value = false
        
        if (pingInterval) {
          clearInterval(pingInterval)
        }
        
        // Exponential backoff reconnect
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttempts.value),
          maxReconnectDelay
        )
        reconnectAttempts.value++
        
        console.log(`[WS] Reconnecting in ${delay}ms...`)
        reconnectTimeout = window.setTimeout(connect, delay)
      }
      
    } catch (error) {
      console.error('[WS] Connection failed:', error)
      isConnected.value = false
    }
  }
  
  const disconnect = () => {
    if (ws.value) {
      ws.value.send(JSON.stringify({ type: 'disconnect' }))
      ws.value.close()
      ws.value = null
    }
    
    if (channel) {
      channel.close()
      channel = null
    }
    
    if (pingInterval) {
      clearInterval(pingInterval)
    }
    
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
    }
    
    isConnected.value = false
  }
  
  const handleMessage = (message: WebSocketMessage) => {
    const handlers = messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => handler(message.data || message))
    }
  }
  
  const on = (type: string, handler: (data: any) => void) => {
    if (!messageHandlers.has(type)) {
      messageHandlers.set(type, new Set())
    }
    messageHandlers.get(type)!.add(handler)
    
    // Return unsubscribe function
    return () => {
      messageHandlers.get(type)?.delete(handler)
    }
  }
  
  onMounted(() => {
    connect()
    
    // Handle tab visibility
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && !isConnected.value) {
        connect()
      }
    })
  })
  
  onBeforeUnmount(() => {
    disconnect()
  })
  
  return {
    isConnected,
    on,
    reconnectAttempts
  }
}
```

---

### 3.2 Integration in MainView.vue

```typescript
// In MainView.vue <script setup>
import { useWebSocket } from '@/composables/useWebSocket'

const { isConnected, on } = useWebSocket()

// Subscribe to events
onMounted(() => {
  // Incoming request
  on('request_created', (data) => {
    incomingRequests.value.push(data)
    // Optional: Show toast notification
  })
  
  // Request responded
  on('request_responded', (data) => {
    if (data.status === 'accepted') {
      // Refresh party state
      fetchMyParty()
    } else {
      // Remove from pending requests
      incomingRequests.value = incomingRequests.value.filter(
        req => req.id !== data.id
      )
    }
  })
  
  // Party member added
  on('party_member_added', (data) => {
    if (currentParty.value?.id === data.party_id) {
      currentParty.value.members.push(data.member)
    }
  })
  
  // Party member removed
  on('party_member_removed', (data) => {
    if (currentParty.value?.id === data.party_id) {
      currentParty.value.members = currentParty.value.members.filter(
        m => m.id !== data.member_id
      )
    }
  })
  
  // Party disbanded
  on('party_disbanded', (data) => {
    if (currentParty.value?.id === data.party_id) {
      currentParty.value = null
      currentMode.value = 'none'
    }
  })
  
  // Player status changed
  on('player_status_changed', (data) => {
    // Update individual players list
    const player = individualPlayers.value.find(p => p.id === data.user_id)
    if (player) {
      if (!data.looking_for_party) {
        individualPlayers.value = individualPlayers.value.filter(
          p => p.id !== data.user_id
        )
      }
    } else if (data.looking_for_party) {
      fetchIndividualPlayers() // Refetch to add new player
    }
  })
})
```

```html
<!-- Reconnecting banner in template -->
<div v-if="!isConnected" class="reconnecting-banner">
  <span class="spinner"></span>
  Reconnecting to server... (Attempt {{ reconnectAttempts }})
</div>
```

---

## 4. Backend Implementation

### 4.1 Enhanced ConnectionManager

```python
# backend/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # uid -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Track which users are in which parties
        self.party_members: Dict[int, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Send connected confirmation
        await self.send_personal_message({
            "type": "connected",
            "uid": user_id,
            "timestamp": int(time.time() * 1000)
        }, user_id)
        
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
        # Clean up party membership tracking
        for party_id, members in list(self.party_members.items()):
            if user_id in members:
                members.remove(user_id)
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

manager = ConnectionManager()
```

---

### 4.2 WebSocket Endpoint with Authentication

```python
# backend/main.py (update websocket endpoint)
from auth import verify_token_ws

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint with JWT authentication via query param.
    URL: ws://api/ws?token=<firebase-jwt>
    """
    try:
        # Verify token
        decoded_token = await verify_token_ws(token)
        user_id = decoded_token.get("uid")
        
        if not user_id:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        
        await manager.connect(websocket, user_id)
        print(f"[WS] User {user_id} connected")
        
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
    finally:
        manager.disconnect(user_id)
```

```python
# backend/auth.py (add WebSocket token verification)
async def verify_token_ws(token: str) -> dict:
    """Verify JWT for WebSocket connections"""
    if not cred_path:
        # Dev mode
        claims = _decode_jwt_claims(token)
        uid = claims.get("user_id") or claims.get("sub")
        if uid:
            return {"uid": uid}
        raise ValueError("Invalid token")
    
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")
```

---

### 4.3 Trigger WebSocket Notifications from REST Endpoints

Update existing REST endpoints to send WebSocket notifications after DB changes:

```python
# backend/routes.py (add after each DB operation)

# Example: Create request
@router.post("/requests", response_model=schemas.PartyRequestResponse)
async def create_request(...):
    db_request = models.PartyRequest(...)
    db.add(db_request)
    await db.commit()
    await db.refresh(db_request)
    
    # ✅ NEW: Send WebSocket notification
    if db_request.type == models.RequestType.JOIN:
        # Notify party leader
        party_result = await db.execute(select(models.Party).where(models.Party.id == db_request.party_id))
        party = party_result.scalars().first()
        if party:
            await manager.send_personal_message({
                "type": "request_created",
                "data": {
                    "id": db_request.id,
                    "type": "join",
                    "sender": {
                        "id": db_request.sender_id,
                        # ... full sender data
                    },
                    "party_id": db_request.party_id
                }
            }, party.leader_id)
    elif db_request.type == models.RequestType.INVITE:
        # Notify receiver
        await manager.send_personal_message({
            "type": "request_created",
            "data": {...}
        }, db_request.receiver_id)
    
    return db_request

# Example: Respond to request
@router.post("/requests/{request_id}/respond")
async def respond_to_request(...):
    db_request.status = ...
    
    if accept and db_request.type == models.RequestType.JOIN:
        sender.party_id = db_request.party_id
        
        # ✅ NEW: Notify all party members
        await manager.send_to_party({
            "type": "party_member_added",
            "data": {
                "party_id": db_request.party_id,
                "member": {...}
            }
        }, db_request.party_id)
        
        # ✅ Notify sender their request was accepted
        await manager.send_personal_message({
            "type": "request_responded",
            "data": {
                "id": db_request.id,
                "status": "accepted",
                "request_type": "join"
            }
        }, db_request.sender_id)
    
    await db.commit()
    return {"message": "Request processed"}
```

---

## 5. Deployment Considerations

### 5.1 Environment Variables

```env
# Frontend (.env)
VITE_WS_URL=wss://api.5stack.gg

# Backend (.env)
# No additional vars needed (FastAPI handles WebSocket natively)
```

### 5.2 Platform-Specific Notes

**Render / Railway / Fly.io:**
- ✅ Native WebSocket support
- ✅ Sticky sessions (connection stays on same instance)
- ✅ No special configuration needed

**Load Balancing:**
- If using multiple backend instances, implement Redis pub/sub to broadcast messages across instances
- For MVP (single instance), current implementation is sufficient

---

## 6. Migration Plan

### Phase 1: Add WebSocket Infrastructure (Week 1)
- [ ] Implement `useWebSocket` composable
- [ ] Update backend ConnectionManager
- [ ] Add WebSocket endpoint with auth
- [ ] Test connection/reconnection logic

### Phase 2: Migrate Request Notifications (Week 2)
- [ ] Add WebSocket notifications to `/requests` endpoints
- [ ] Remove polling from `fetchIncomingRequests`
- [ ] Test end-to-end flow

### Phase 3: Migrate Party Updates (Week 3)
- [ ] Add WebSocket notifications for party changes
- [ ] Remove polling from `fetchMyParty`
- [ ] Test multi-user scenarios

### Phase 4: Full Cutover (Week 4)
- [ ] Remove all `setInterval` polling code
- [ ] Add reconnection UI (banner)
- [ ] Performance testing & monitoring
- [ ] Deploy to production

---

## 7. Testing Strategy

### Unit Tests
- ConnectionManager add/remove users
- Message routing logic
- Token verification

### Integration Tests
- WebSocket connection with valid/invalid tokens
- Message delivery to correct recipients
- Reconnection after disconnect

### E2E Tests
- User A sends invite → User B receives instantly
- Party member joins → All members see update
- Multi-tab behavior (primary/secondary sync)

---

## 8. Monitoring & Observability

**Metrics to Track:**
- Active WebSocket connections (gauge)
- Connection success/failure rate
- Average message latency
- Reconnection frequency per user
- Messages sent/received per second

**Logging:**
- Connection/disconnection events (with user ID)
- Message delivery failures
- Reconnection attempts

**Alerts:**
- Connection success rate < 95%
- Average latency > 2 seconds
- Reconnection rate > 10% of users

---

## 9. Rollback Plan

If issues arise:
1. **Feature Flag**: Set `WEBSOCKET_ENABLED=false` → app reverts to REST polling
2. **Git Revert**: Rollback to previous version (polling-based)
3. **Database**: No schema changes, so no DB rollback needed

---

## Next Steps
- ✅ Requirements finalized
- ✅ Technical design complete
- ⏭️ **Task Breakdown**: Generate implementation tasks from this design

