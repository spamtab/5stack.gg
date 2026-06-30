# WebSocket Real-Time Updates - Implementation Tasks

## Overview
This document breaks down the WebSocket implementation into discrete, actionable tasks based on the technical design.

---

## Phase 1: Backend WebSocket Infrastructure (Week 1)

### Task 1.1: Enhance ConnectionManager
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 2-3 hours  

**Description:**
Enhance the existing `ConnectionManager` class in `backend/main.py` to support:
- User ID-based connection mapping (uid → WebSocket)
- Party membership tracking for efficient message routing
- Personal message delivery
- Party-wide message broadcasting
- Connection cleanup on disconnect

**Acceptance Criteria:**
- [ ] `ConnectionManager` has methods: `connect()`, `disconnect()`, `send_personal_message()`, `send_to_party()`, `add_to_party()`, `remove_from_party()`
- [ ] Connection state is properly cleaned up on disconnect
- [ ] Party membership tracking is maintained accurately
- [ ] Error handling for dead connections (send failures)

**Files to Modify:**
- `backend/main.py` (update existing `ConnectionManager`)

**Code Reference:** See design.md Section 4.1

---

### Task 1.2: Add WebSocket Token Verification
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 1-2 hours  

**Description:**
Add `verify_token_ws()` function to `backend/auth.py` to verify Firebase JWT tokens for WebSocket connections. This should handle both production (Firebase Admin) and dev mode (JWT decode without verification).

**Acceptance Criteria:**
- [ ] `verify_token_ws(token: str)` function accepts JWT and returns decoded token with UID
- [ ] Works in both dev mode (no Firebase credentials) and production mode
- [ ] Raises `ValueError` for invalid/expired tokens
- [ ] Extracts `uid` from token claims

**Files to Modify:**
- `backend/auth.py` (add `verify_token_ws()` function)

**Code Reference:** See design.md Section 4.2

---

### Task 1.3: Update WebSocket Endpoint with Authentication
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 2-3 hours  

**Description:**
Replace the existing `/ws/{client_id}` endpoint with a new `/ws?token=<jwt>` endpoint that:
- Authenticates via JWT query parameter
- Registers connection in `ConnectionManager` with user ID
- Handles ping/pong keep-alive messages
- Syncs initial party state (if user is in a party)
- Gracefully handles disconnections

**Acceptance Criteria:**
- [ ] Endpoint URL is `/ws?token=<firebase-jwt>`
- [ ] Rejects connections with invalid/missing tokens (close with code 4001)
- [ ] Responds to `{"type": "ping"}` with `{"type": "pong", "timestamp": <ms>}`
- [ ] Sends `{"type": "connected", "uid": "...", "timestamp": <ms>}` on successful connection
- [ ] Handles `{"type": "disconnect"}` gracefully
- [ ] Cleans up connection state on disconnect
- [ ] Syncs initial party membership if user is in a party

**Files to Modify:**
- `backend/main.py` (replace existing websocket endpoint)

**Code Reference:** See design.md Section 4.2

---

### Task 1.4: Add WebSocket Notification Helpers
**Status**: ❌ Not Started  
**Priority**: Medium  
**Estimated Time**: 1-2 hours  

**Description:**
Create helper functions in `backend/routes.py` or a new `backend/websocket_notifications.py` file to send typed WebSocket messages:
- `notify_request_created()`
- `notify_request_responded()`
- `notify_party_member_added()`
- `notify_party_member_removed()`
- `notify_party_disbanded()`
- `notify_player_status_changed()`

**Acceptance Criteria:**
- [ ] Each helper function constructs the correct message format (see design.md Section 2.2)
- [ ] Functions use `manager.send_personal_message()` or `manager.send_to_party()` appropriately
- [ ] Error handling for connection failures (don't crash if WebSocket send fails)
- [ ] All message types from design.md Section 2.2 are covered

**Files to Create:**
- `backend/websocket_notifications.py` (new file)

**Files to Modify:**
- `backend/routes.py` (import helpers)
- `backend/main.py` (make `manager` globally accessible)

**Code Reference:** See design.md Section 2.2

---

## Phase 2: Backend Integration with REST Endpoints (Week 2)

### Task 2.1: Add WebSocket Notifications to Request Creation
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 1-2 hours  

**Description:**
Update `POST /api/requests` endpoint to send WebSocket notifications:
- For JOIN requests: notify party leader
- For INVITE requests: notify receiver

**Acceptance Criteria:**
- [ ] After creating a JOIN request, send `request_created` message to party leader
- [ ] After creating an INVITE request, send `request_created` message to receiver
- [ ] Message includes full sender profile (username, rank, mood, agent_priority)
- [ ] Endpoint still works if WebSocket send fails (non-blocking)

**Files to Modify:**
- `backend/routes.py` (`create_request` function)

**Code Reference:** See design.md Section 4.3

---

### Task 2.2: Add WebSocket Notifications to Request Response
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 2-3 hours  

**Description:**
Update `POST /api/requests/{request_id}/respond` endpoint to send WebSocket notifications:
- Notify sender when their request is accepted/rejected
- If accepted and JOIN request: notify all party members of new member
- If accepted and INVITE request: notify receiver they joined

**Acceptance Criteria:**
- [ ] Send `request_responded` message to sender (accept/reject status)
- [ ] For accepted JOIN: send `party_member_added` to all party members
- [ ] For accepted INVITE: send `party_member_added` to receiver
- [ ] Track party membership in ConnectionManager when user joins

**Files to Modify:**
- `backend/routes.py` (`respond_to_request` function)

**Code Reference:** See design.md Section 4.3

---

### Task 2.3: Add WebSocket Notifications to Party Disbanding
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 1-2 hours  

**Description:**
Update party leave/disband endpoints to send WebSocket notifications:
- When leader disbands: notify all party members
- When member leaves: notify remaining party members
- When member is kicked: notify kicked member and remaining members

**Acceptance Criteria:**
- [ ] `DELETE /api/parties/leave` sends `party_disbanded` if leader leaves and party disbands
- [ ] `DELETE /api/parties/leave` sends `party_member_removed` to remaining members if non-leader leaves
- [ ] `DELETE /api/parties/members/{member_id}` sends `party_member_removed` to kicked member and party
- [ ] `DELETE /api/parties/disband` sends `party_disbanded` to all members
- [ ] ConnectionManager party membership is cleaned up

**Files to Modify:**
- `backend/routes.py` (`leave_party`, `remove_party_member`, `disband_party` functions)

**Code Reference:** See design.md Section 4.3

---

### Task 2.4: Add WebSocket Notifications to Looking-For-Party Status
**Status**: ❌ Not Started  
**Priority**: Medium  
**Estimated Time**: 1 hour  

**Description:**
Update `POST /api/users` endpoint to send WebSocket notifications when a user changes their `looking_for_party` status. This helps other users see real-time availability changes.

**Acceptance Criteria:**
- [ ] When `looking_for_party` changes from `false` to `true`, broadcast to all connected users
- [ ] When `looking_for_party` changes from `true` to `false`, broadcast to all connected users
- [ ] Message type is `player_status_changed` with `user_id` and `looking_for_party` boolean

**Files to Modify:**
- `backend/routes.py` (`create_user` function)

**Notes:**
- This is a "nice-to-have" for Phase 2; can be deferred if time is tight

---

## Phase 3: Frontend WebSocket Client (Week 2-3)

### Task 3.1: Create `useWebSocket` Composable
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 4-5 hours  

**Description:**
Create a Vue 3 composable at `frontend/src/composables/useWebSocket.ts` that:
- Manages WebSocket connection lifecycle
- Handles multi-tab coordination via BroadcastChannel (keyed by Firebase UID)
- Implements primary/secondary tab election
- Provides event subscription API (`on()` method)
- Handles reconnection with exponential backoff
- Implements ping/pong keep-alive (30s interval)

**Acceptance Criteria:**
- [ ] `useWebSocket()` returns `{ isConnected, on, reconnectAttempts }`
- [ ] Only primary tab creates WebSocket connection
- [ ] Secondary tabs receive messages via BroadcastChannel
- [ ] BroadcastChannel is keyed by `ws-sync-${firebase_uid}` (different users = independent channels)
- [ ] Reconnection uses exponential backoff (1s, 2s, 4s, 8s, max 30s)
- [ ] Ping sent every 30 seconds, reconnect if 3 pings fail
- [ ] `on(type, handler)` registers event listeners and returns unsubscribe function
- [ ] Cleans up on component unmount

**Files to Create:**
- `frontend/src/composables/useWebSocket.ts` (new file)

**Code Reference:** See design.md Section 3.1

---

### Task 3.2: Add WebSocket Environment Variable
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 15 minutes  

**Description:**
Add `VITE_WS_URL` environment variable to frontend `.env` files for WebSocket endpoint URL.

**Acceptance Criteria:**
- [ ] `frontend/.env` has `VITE_WS_URL=ws://localhost:8000` (dev)
- [ ] `frontend/.env.production` has `VITE_WS_URL=wss://api.5stack.gg` (prod)
- [ ] `useWebSocket` composable reads from `import.meta.env.VITE_WS_URL`

**Files to Modify:**
- `frontend/.env`
- `frontend/.env.production`

---

### Task 3.3: Integrate WebSocket in MainView
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 3-4 hours  

**Description:**
Integrate `useWebSocket()` composable in `MainView.vue` and subscribe to all WebSocket events:
- `request_created` → update `incomingRequests`
- `request_responded` → update party state or remove request
- `party_member_added` → update `currentParty.members`
- `party_member_removed` → update `currentParty.members`
- `party_disbanded` → clear `currentParty`, reset mode to 'none'
- `player_status_changed` → update `individualPlayers` list

**Acceptance Criteria:**
- [ ] `useWebSocket()` is called in `<script setup>`
- [ ] All 6 message types have event listeners registered in `onMounted`
- [ ] Incoming requests appear instantly without polling
- [ ] Party member changes reflect in real-time
- [ ] Player status changes update individual players list
- [ ] No console errors related to WebSocket

**Files to Modify:**
- `frontend/src/views/MainView.vue`

**Code Reference:** See design.md Section 3.2

---

### Task 3.4: Remove REST Polling Code
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 1-2 hours  

**Description:**
Remove all `setInterval` polling code from `MainView.vue`:
- Remove `refreshTimer` for incoming requests (currently fetches every 5s)
- Remove any other polling intervals
- Keep initial data fetch on mount (for bootstrapping state)

**Acceptance Criteria:**
- [ ] No `setInterval` calls remain in MainView.vue
- [ ] `fetchIncomingRequests()` is only called once on mount (for initial state)
- [ ] `fetchMyParty()` is only called once on mount or when mode changes
- [ ] `fetchIndividualPlayers()` polling is removed (optional: keep manual refresh button)

**Files to Modify:**
- `frontend/src/views/MainView.vue`

---

### Task 3.5: Add Reconnection UI Banner
**Status**: ❌ Not Started  
**Priority**: Medium  
**Estimated Time**: 1-2 hours  

**Description:**
Add a "Reconnecting..." banner at the top of MainView that appears when WebSocket is disconnected. Should show:
- Spinner animation
- "Reconnecting to server..." message
- Current reconnection attempt number

**Acceptance Criteria:**
- [ ] Banner appears when `isConnected === false`
- [ ] Banner shows attempt number from `reconnectAttempts`
- [ ] Banner disappears when connection is restored
- [ ] Banner is fixed position (always visible even when scrolling)
- [ ] Styled consistently with existing UI (dark theme, red/warning color)

**Files to Modify:**
- `frontend/src/views/MainView.vue` (template + styles)

**Code Reference:** See design.md Section 3.2

---

## Phase 4: Testing & Deployment (Week 3-4)

### Task 4.1: Test Single-User Flow
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 2-3 hours  

**Description:**
Manually test single-user WebSocket flow:
- User logs in → WebSocket connects
- User creates party → no errors
- User sends/receives requests → notifications appear instantly
- User disconnects → reconnection works

**Acceptance Criteria:**
- [ ] WebSocket connects successfully on login
- [ ] Incoming requests appear without delay
- [ ] Reconnection works after network interruption (simulate by pausing backend)
- [ ] No console errors or WebSocket connection failures

**Testing Approach:**
- Use browser DevTools Network tab to monitor WebSocket messages
- Simulate network interruption (pause backend, wait, resume)
- Verify exponential backoff in reconnection attempts

---

### Task 4.2: Test Multi-User Flow
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 3-4 hours  

**Description:**
Test WebSocket notifications between multiple users:
- User A sends invite to User B → User B sees request instantly
- User B accepts → User A sees party update instantly
- User C requests to join User A's party → User A sees request instantly
- User A kicks User C → User C sees they were removed

**Acceptance Criteria:**
- [ ] All request notifications deliver in < 1 second
- [ ] Party member changes reflect for all members instantly
- [ ] No duplicate notifications
- [ ] No missed notifications

**Testing Approach:**
- Use two browsers (Chrome + Firefox) or two browser profiles
- Log in with different Google accounts
- Test all 5 WebSocket message types (REQ-2.1 through REQ-2.5)

---

### Task 4.3: Test Multi-Tab Behavior
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 2-3 hours  

**Description:**
Test multi-tab coordination:
- **Same user, multiple tabs**: Only one WebSocket connection, state synced via BroadcastChannel
- **Different users, multiple tabs**: Independent WebSocket connections

**Acceptance Criteria:**
- [ ] Same user opens 3 tabs → only 1 WebSocket connection exists (check Network tab)
- [ ] Message received in primary tab → appears in all secondary tabs instantly
- [ ] Primary tab closes → one secondary tab becomes new primary
- [ ] Different Google accounts in different tabs → separate WebSocket connections (verified in backend logs)

**Testing Approach:**
- Log in with User A in Tab 1 & Tab 2
- Log in with User B in Tab 3
- Send request to User A → verify appears in both User A tabs
- Check backend logs to confirm only 2 WebSocket connections (User A + User B)

---

### Task 4.4: Performance Testing
**Status**: ❌ Not Started  
**Priority**: Medium  
**Estimated Time**: 2-3 hours  

**Description:**
Test WebSocket performance under load:
- Simulate 50+ concurrent connections
- Measure message delivery latency
- Verify no memory leaks

**Acceptance Criteria:**
- [ ] Backend handles 100 concurrent WebSocket connections without performance degradation
- [ ] Message delivery latency < 1 second (average)
- [ ] No memory leaks after 1 hour of runtime

**Testing Approach:**
- Use tools like `wscat` or custom script to simulate connections
- Monitor backend CPU/memory usage
- Use browser DevTools Performance tab to check for frontend memory leaks

---

### Task 4.5: Add WebSocket Logging & Monitoring
**Status**: ❌ Not Started  
**Priority**: Medium  
**Estimated Time**: 1-2 hours  

**Description:**
Add logging for WebSocket events to help debug production issues:
- Connection/disconnection events (with user ID)
- Message delivery successes/failures
- Reconnection attempts

**Acceptance Criteria:**
- [ ] Backend logs `[WS] User {uid} connected` on connection
- [ ] Backend logs `[WS] User {uid} disconnected` on disconnect
- [ ] Backend logs `[WS] Error sending to {uid}: {error}` on send failure
- [ ] Frontend logs `[WS] Connected`, `[WS] Disconnected`, `[WS] Reconnecting in {delay}ms...`

**Files to Modify:**
- `backend/main.py` (add logging in ConnectionManager and endpoint)
- `frontend/src/composables/useWebSocket.ts` (add console.log statements)

---

### Task 4.6: Update CORS Configuration for Production
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 30 minutes  

**Description:**
Update `allow_origins` in CORS middleware to support production frontend URL.

**Acceptance Criteria:**
- [ ] CORS allows `https://spamtab.github.io` (current production URL)
- [ ] CORS allows `wss://` protocol for WebSocket connections
- [ ] Test in production to confirm no CORS errors

**Files to Modify:**
- `backend/main.py` (CORS middleware configuration)

**Notes:**
- Already configured correctly: `allow_origins=["https://spamtab.github.io"]`

---

### Task 4.7: Deploy Backend to Production
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 1-2 hours  

**Description:**
Deploy updated backend with WebSocket support to production (Render/Railway/Fly.io).

**Acceptance Criteria:**
- [ ] Backend deployed with no breaking changes
- [ ] WebSocket endpoint `/ws` is accessible via `wss://api.5stack.gg/ws`
- [ ] Health check confirms backend is running
- [ ] Firebase authentication works in production

**Deployment Steps:**
1. Commit all backend changes
2. Push to main branch
3. Trigger deployment (or manual deploy if needed)
4. Verify deployment via health check endpoint
5. Test WebSocket connection from frontend

---

### Task 4.8: Deploy Frontend to Production
**Status**: ❌ Not Started  
**Priority**: High  
**Estimated Time**: 1 hour  

**Description:**
Deploy updated frontend with WebSocket integration to production (GitHub Pages).

**Acceptance Criteria:**
- [ ] Frontend deployed with `VITE_WS_URL=wss://api.5stack.gg`
- [ ] WebSocket connection works in production
- [ ] All features work end-to-end in production
- [ ] No console errors in production build

**Deployment Steps:**
1. Update `frontend/.env.production` with production WebSocket URL
2. Run `npm run build` to verify production build
3. Commit and push to main branch
4. GitHub Actions deploys to GitHub Pages
5. Test production URL: `https://spamtab.github.io/proj2/`

---

## Phase 5: Optional Enhancements (Future)

### Task 5.1: Add Toast Notifications for WebSocket Events
**Status**: ❌ Not Started  
**Priority**: Low  
**Estimated Time**: 2-3 hours  

**Description:**
Show toast notifications when WebSocket events occur (e.g., "New party invite from [username]").

**Acceptance Criteria:**
- [ ] Toast appears for incoming requests
- [ ] Toast appears for request accepted/rejected
- [ ] Toast appears for party member joined/left
- [ ] Toast auto-dismisses after 5 seconds

---

### Task 5.2: Add Redis Pub/Sub for Multi-Instance Load Balancing
**Status**: ❌ Not Started  
**Priority**: Low  
**Estimated Time**: 4-5 hours  

**Description:**
If deploying multiple backend instances, implement Redis pub/sub to broadcast WebSocket messages across instances.

**Acceptance Criteria:**
- [ ] Redis client initialized in backend
- [ ] ConnectionManager publishes messages to Redis channel
- [ ] All instances subscribe to Redis and forward messages to their connections
- [ ] Works correctly with 2+ backend instances

**Notes:**
- Not needed for MVP (single backend instance)
- Required only if scaling to multiple instances

---

## Summary

**Total Estimated Time:** ~35-50 hours (3-4 weeks part-time)

**Critical Path Tasks:**
1. Task 1.1, 1.2, 1.3 (Backend infrastructure)
2. Task 3.1 (Frontend composable)
3. Task 3.3 (Integration in MainView)
4. Task 2.1, 2.2 (Request notifications)
5. Task 4.2, 4.3 (Multi-user testing)
6. Task 4.7, 4.8 (Production deployment)

**Task Dependencies:**
- Phase 2 depends on Phase 1 completion
- Phase 3 can run parallel with Phase 2 (frontend/backend work independently)
- Phase 4 depends on Phases 1-3 completion

**Risk Mitigation:**
- Test multi-tab behavior early (Task 4.3) to catch BroadcastChannel issues
- Test multi-user flow (Task 4.2) before production deployment
- Keep polling code in git history for easy rollback if needed
