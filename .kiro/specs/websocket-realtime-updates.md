# WebSocket Real-Time Updates Architecture

## Overview
Evaluate and potentially migrate from REST polling to WebSocket-based real-time updates for party invites, join requests, and party state changes.

## Status
- **Phase**: Requirements Gathering
- **Created**: 2026-06-30
- **Last Updated**: 2026-06-30

---

## Requirements

### 1. User Experience Goals

**Current Pain Points:**
- Users experience 5-second delay before seeing incoming requests
- Party member changes (joins/leaves) aren't immediately visible
- No visual feedback when someone accepts/rejects your request
- Sidebar notification badge updates only every 5 seconds

**Desired Experience:**
- [ ] **REQ-1.1**: Incoming party invites appear instantly (< 500ms)
- [ ] **REQ-1.2**: Join requests show up immediately when sent
- [ ] **REQ-1.3**: Party member changes reflect in real-time (member joins/leaves)
- [ ] **REQ-1.4**: Notification badge updates immediately when requests arrive/resolve
- [ ] **REQ-1.5**: Visual feedback when your invite/request is accepted or rejected

### 2. Feature Scope

**Features that would benefit from real-time updates:**
- [ ] **REQ-2.1**: Incoming requests (join + invite) notifications
- [ ] **REQ-2.2**: Party member list changes (add/remove members)
- [ ] **REQ-2.3**: Party state changes (created, disbanded, leader change)
- [ ] **REQ-2.4**: Request status updates (accepted, rejected, canceled)
- [ ] **REQ-2.5**: Player availability changes (when someone goes looking_for_party)

**Features that can stay REST/polling:**
- Individual player list (doesn't change frequently, polling is fine)
- Parties list search results (user-initiated action, polling acceptable)
- User preferences updates (user-initiated, no real-time needed)

### 3. Technical Requirements

**Reliability:**
- [x] **REQ-3.1**: Handle WebSocket disconnections gracefully (exponential backoff: 1s → 2s → 4s → 8s → max 30s)
- [x] **REQ-3.2**: Block UI features with "Reconnecting..." state when WebSocket is down (no fallback to polling)
- [x] **REQ-3.3**: Maintain connection state across page visibility changes (tab switching)
- [x] **REQ-3.4**: Single WebSocket connection per user (same logged-in account) shared across tabs via localStorage/BroadcastChannel
  - **Note:** Different Google accounts in different tabs = independent connections
  - **Note:** Same user duplicating tab = shared connection (one WebSocket, synchronized state)

**Performance:**
- [x] **REQ-3.5**: Support at least 100 concurrent WebSocket connections per server
- [x] **REQ-3.6**: Message delivery latency < 1 second under normal conditions
- [x] **REQ-3.7**: Minimal memory footprint (connection state management)

**Security:**
- [ ] **REQ-3.8**: Authenticate WebSocket connections using Firebase tokens
- [ ] **REQ-3.9**: Validate all incoming WebSocket messages server-side
- [ ] **REQ-3.10**: Rate limit WebSocket messages to prevent abuse

### 4. Migration & Deployment

**Migration Strategy:**
- [x] **REQ-4.1**: Remove REST polling entirely, full WebSocket cutover (no hybrid mode)
- [x] **REQ-4.2**: Feature flag to enable/disable WebSocket globally for emergency rollback
- [x] **REQ-4.3**: Metrics to monitor WebSocket connection health and message latency
- [x] **REQ-4.4**: Database rollback plan (no schema changes, so rollback is just redeploying old code)

**Backward Compatibility:**
- [ ] **REQ-4.5**: Old clients using REST polling continue to work
- [ ] **REQ-4.6**: Database schema remains unchanged (no breaking changes)

### 5. Non-Functional Requirements

**Monitoring & Observability:**
- [ ] **REQ-5.1**: Log WebSocket connection/disconnection events
- [ ] **REQ-5.2**: Track message delivery success/failure rates
- [ ] **REQ-5.3**: Alert on excessive disconnections or failed deliveries

**Developer Experience:**
- [ ] **REQ-5.4**: Clear WebSocket message protocol documentation
- [ ] **REQ-5.5**: Easy-to-use client library/composable for Vue components
- [ ] **REQ-5.6**: Local development support (WebSocket works in dev environment)

---

## Questions & Decisions Needed

### ✅ Critical Decisions Made:
1. **Latency Target:** < 1 second (acceptable for gaming context, easy to achieve)
2. **Feature Scope:** Full WebSocket implementation (REQ-2.1 through REQ-2.5)
3. **Fallback Strategy:** Block features until WebSocket reconnects (force real-time experience)
4. **Hosting:** Render/Railway/Fly.io (WebSocket-friendly platforms)
5. **Multi-tab Support:** Use localStorage/BroadcastChannel to sync state across tabs **for the same user**
   - Same user, multiple tabs → single WebSocket connection, synchronized state
   - Different users (Google accounts), different tabs → independent WebSocket connections
   - Implementation: Use Firebase user ID as the localStorage key namespace

### Technical Decisions:
1. **Message Persistence:** No offline queuing needed (users must be online to use the app)
2. **Heartbeat/Ping-Pong:** Yes, implement keep-alive to detect dead connections early
3. **Reconnection Strategy:** Exponential backoff (1s, 2s, 4s, 8s, max 30s)
4. **Tab Coordination:** Primary tab owns WebSocket, secondary tabs listen via BroadcastChannel (keyed by Firebase UID)

---

## Success Metrics

**How we'll measure success:**
- [x] Average time from request sent → request received drops from 5s → < 1s
- [x] User sees "Reconnecting..." banner < 1% of the time (99% uptime)
- [x] WebSocket connection success rate > 99%
- [x] Server handles 100+ concurrent connections without performance degradation
- [x] Zero increase in server costs (WebSocket connections use less bandwidth than polling)

---

## Next Steps
1. ✅ Requirements defined (this document)
2. ⏭️ **Design Phase**: Create technical design document (WebSocket protocol, message formats, reconnection logic)
3. ⏭️ **Implementation Phase**: Break down into tasks (backend WebSocket endpoint, frontend client, migration)

---

## Notes
- Current system polls every 5 seconds, which is acceptable for an MVP but not ideal for competitive gaming context where immediacy matters
- FastAPI has built-in WebSocket support via Starlette, so backend framework is ready
- Vue 3 Composition API makes it easy to create a `useWebSocket` composable for clean integration
