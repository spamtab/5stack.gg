<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const username = ref('')
const tagline = ref('')
const errorMsg = ref('')
const loading = ref(false)

const handleRegister = async () => {
  if (!username.value || !tagline.value) {
    errorMsg.value = 'Please enter both username and tagline'
    return
  }
  
  loading.value = true
  try {
    const fullUsername = `${username.value}#${tagline.value}`
    const token = await authStore.getToken()
    if (!token) throw new Error('Not authenticated')

    const response = await fetch('http://localhost:8000/api/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        username: fullUsername
      })
    })
    
    if (!response.ok) {
      throw new Error('Failed to register user')
    }

    // Cache the created user so MainView doesn't need to re-fetch
    const data = await response.json()
    authStore.setBackendUser(data)
    
    router.push('/')
  } catch (e: any) {
    errorMsg.value = e.message || 'An error occurred'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-container d-flex align-center justify-center">
    <div class="glass-panel register-card animate-fade-in">
      <h2 class="mb-4">Set Your Riot ID</h2>
      <p class="text-muted mb-4">You need to set your Valorant username before continuing.</p>
      
      <div class="input-group d-flex gap-2 mb-4">
        <input 
          v-model="username" 
          type="text" 
          class="input-field" 
          placeholder="Username" 
          maxlength="16"
        />
        <span class="hashtag d-flex align-center">#</span>
        <input 
          v-model="tagline" 
          type="text" 
          class="input-field tagline-input" 
          placeholder="TAG" 
          maxlength="5"
        />
      </div>
      
      <button class="btn-primary w-100" @click="handleRegister" :disabled="loading">
        {{ loading ? 'Saving...' : 'Complete Registration' }}
      </button>
      
      <p v-if="errorMsg" class="text-danger mt-4 text-center">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.register-container {
  min-height: 100vh;
  background-color: var(--dark-base);
}

.register-card {
  padding: 48px;
  max-width: 480px;
  width: 100%;
}

.hashtag {
  color: var(--text-secondary);
  font-size: 1.5rem;
  font-weight: bold;
}

.tagline-input {
  width: 100px;
}
</style>
