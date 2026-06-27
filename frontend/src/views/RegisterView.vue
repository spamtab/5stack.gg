<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useRouter } from 'vue-router'
import { apiUrl } from '../config/api'

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

    const response = await fetch(apiUrl('/api/users'), {
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
    
    router.push('/app')
  } catch (e: any) {
    errorMsg.value = e.message || 'An error occurred'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-container d-flex align-center justify-center">
    <div class="register-bg"></div>
    <div class="glass-panel register-card animate-fade-in">
      <div class="register-accent"></div>
      <p class="register-step">Step 1 of 1</p>
      <h2 class="mb-4">Set Your Riot ID</h2>
      <p class="text-muted mb-4 register-desc">You need to set your Valorant username before continuing.</p>
      
      <label class="field-label">Riot ID</label>
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
        <span v-if="loading" class="spinner mr-2"></span>
        {{ loading ? 'Saving...' : 'Complete Registration' }}
      </button>
      
      <p v-if="errorMsg" class="text-danger mt-4 text-center error-msg">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.register-container {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.register-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 80% 20%, rgba(255, 70, 85, 0.12), transparent),
    radial-gradient(ellipse 50% 30% at 10% 80%, rgba(15, 139, 141, 0.08), transparent);
  pointer-events: none;
}

.register-card {
  position: relative;
  padding: 48px;
  max-width: 480px;
  width: calc(100% - 32px);
  border-left: 3px solid var(--riot-red);
}

.register-accent {
  position: absolute;
  top: 24px;
  right: 24px;
  width: 8px;
  height: 8px;
  background: var(--riot-red);
  clip-path: polygon(0 0, 100% 0, 100% 100%);
}

.register-step {
  color: var(--riot-red);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 8px;
}

.register-desc {
  line-height: 1.6;
}

.hashtag {
  color: var(--riot-red);
  font-size: 1.5rem;
  font-weight: 800;
}

.tagline-input {
  width: 100px;
  flex-shrink: 0;
}

.error-msg {
  font-size: 0.85rem;
  padding: 10px;
  background: var(--riot-red-dim);
  border-radius: var(--radius-md);
}
</style>
