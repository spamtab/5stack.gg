<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useAuthStore } from './stores/authStore'
import { auth } from './firebase'
import { onAuthStateChanged } from 'firebase/auth'
import { apiUrl } from './config/api'

const authStore = useAuthStore()
const router = useRouter()

onMounted(() => {
  onAuthStateChanged(auth, async (user) => {
    authStore.setUser(user)

    if (user) {
      // Always force-refresh the token to avoid stale/expired tokens
      const token = await authStore.getToken()

      if (!token) {
        // Token refresh failed — treat as logged out
        authStore.setLoading(false)
        router.push('/login')
        return
      }

      try {
        const response = await fetch(apiUrl('/api/users/me'), {
          headers: { Authorization: `Bearer ${token}` },
        })

        if (response.status === 404) {
          // New user — no profile yet, send to registration
          authStore.setBackendUser(null)
          router.push('/register')
        } else if (response.status === 401) {
          // Token rejected by backend (shouldn't happen after force-refresh, but handle it)
          console.error('Token rejected by backend')
          await authStore.logout()
          router.push('/login')
        } else if (response.ok) {
          // Returning user — load their saved profile into the store
          const data = await response.json()
          authStore.setBackendUser(data)

          // Only redirect if still on auth pages
          const currentPath = router.currentRoute.value.path
          if (currentPath === '/login' || currentPath === '/register') {
            router.push('/app')
          }
        }
      } catch (e) {
        console.error('Backend connection failed', e)
        // Don't redirect — could be a transient network error
      }
    } else {
      // No Firebase user — clear everything and redirect if needed
      authStore.setBackendUser(null)
      if (router.currentRoute.value.meta.requiresAuth) {
        router.push('/login')
      }
    }

    authStore.setLoading(false)
  })
})
</script>

<template>
  <div v-if="authStore.loading" class="loading-screen d-flex align-center justify-center h-100">
    <div class="spinner"></div>
  </div>
  <RouterView v-else />
</template>

<style>
.loading-screen {
  min-height: 100vh;
}
</style>
