<script setup lang="ts">
import { useAuthStore } from '../stores/authStore'
import { useRouter } from 'vue-router'
import { ref } from 'vue'

const authStore = useAuthStore()
const router = useRouter()
const errorMsg = ref('')

const handleLogin = async () => {
  try {
    errorMsg.value = ''
    await authStore.loginWithGoogle()
    // App.vue router logic will handle redirect after checking backend
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to login'
  }
}
</script>

<template>
  <div class="login-container d-flex align-center justify-center">
    <div class="glass-panel login-card text-center animate-fade-in">
      <h1 class="mb-4 title">V-Match</h1>
      <p class="text-muted mb-4">Find your perfect Valorant squad.</p>
      
      <button class="btn-primary w-100 justify-center" @click="handleLogin">
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><path d="M22.54 11.42L12.42 1.3a1 1 0 0 0-1.41 0L1.3 11.42a1 1 0 0 0 0 1.41l10.12 10.12a1 1 0 0 0 1.41 0l10.12-10.12a1 1 0 0 0 0-1.41z"></path><path d="M12.92 12l2.3-2.3a.5.5 0 0 0 0-.7l-2.3-2.3a.5.5 0 0 0-.7 0l-2.3 2.3a.5.5 0 0 0 0 .7l2.3 2.3"></path></svg>
        Sign in with Google
      </button>
      
      <p v-if="errorMsg" class="text-danger mt-4">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  background: radial-gradient(circle at center, rgba(255, 70, 85, 0.15) 0%, var(--dark-base) 60%);
}

.login-card {
  padding: 48px;
  max-width: 400px;
  width: 100%;
}

.title {
  color: var(--riot-red);
  font-size: 2.5rem;
  letter-spacing: 2px;
}
</style>
