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
    if (!authStore.user) {
      console.log('[WS] No user, skipping connection')
      return
    }
    
    // Check if another tab is already primary
    if (channelName.value) {
      channel = new BroadcastChannel(channelName.value)
      
      // Request primary status
      channel.postMessage({ type: 'primary-check' })
      
      await new Promise<void>(resolve => {
        const timeout = setTimeout(() => {
          // No response = we become primary
          isPrimaryTab.value = true
          console.log('[WS] This tab is primary')
          resolve()
        }, 100)
        
        const handleMessage = (event: MessageEvent) => {
          if (event.data.type === 'primary-exists') {
            clearTimeout(timeout)
            isPrimaryTab.value = false
            console.log('[WS] Another tab is primary, this is secondary')
            resolve()
          }
        }
        
        channel!.addEventListener('message', handleMessage, { once: true })
      })
      
      // Set up permanent message handler
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
      console.log('[WS] Secondary tab ready')
      return
    }
    
    try {
      const token = await authStore.user?.getIdToken()
      if (!token) {
        console.error('[WS] No auth token')
        throw new Error('No auth token')
      }
      
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
      const fullUrl = `${wsUrl}/ws?token=${token}`
      console.log('[WS] Connecting to:', wsUrl)
      
      ws.value = new WebSocket(fullUrl)
      
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
        
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value})...`)
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
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isConnected.value) {
        connect()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // Cleanup visibility listener on unmount
    onBeforeUnmount(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
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
