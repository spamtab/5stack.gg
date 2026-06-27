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
    <div class="login-bg"></div>
    <div class="glass-panel login-card text-center animate-fade-in">
      <div class="login-accent"></div>
      <p class="login-eyebrow">Valorant squad finder</p>
      <h1 class="mb-4 title">5stack.gg</h1>
      <p class="text-muted mb-4 login-subtitle">Find your perfect Valorant squad.</p>
      
      <button class="btn-primary w-100 justify-center login-btn" @click="handleLogin">
        <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M22.54 11.42L12.42 1.3a1 1 0 0 0-1.41 0L1.3 11.42a1 1 0 0 0 0 1.41l10.12 10.12a1 1 0 0 0 1.41 0l10.12-10.12a1 1 0 0 0 0-1.41z"></path><path d="M12.92 12l2.3-2.3a.5.5 0 0 0 0-.7l-2.3-2.3a.5.5 0 0 0-.7 0l-2.3 2.3a.5.5 0 0 0 0 .7l2.3 2.3"></path></svg>
        Sign in with Google
      </button>
      
      <p v-if="errorMsg" class="text-danger mt-4 error-msg">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 40%, rgba(255, 70, 85, 0.2) 0%, transparent 50%),
    repeating-linear-gradient(
      135deg,
      transparent,
      transparent 40px,
      rgba(255, 70, 85, 0.03) 40px,
      rgba(255, 70, 85, 0.03) 41px
    );
  pointer-events: none;
}

.login-card {
  position: relative;
  padding: 56px 48px;
  max-width: 420px;
  width: calc(100% - 32px);
  border-top: 2px solid var(--riot-red);
}

.login-accent {
  position: absolute;
  top: 0;
  left: 0;
  width: 48px;
  height: 3px;
  background: var(--riot-red);
}

.login-eyebrow {
  color: var(--riot-red);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  margin-bottom: 12px;
}

.title {
  color: var(--text-primary);
  font-size: 2.75rem;
  letter-spacing: 0.12em;
}

.title::after {
  content: '';
  display: block;
  width: 48px;
  height: 3px;
  background: var(--riot-red);
  margin: 16px auto 0;
}

.login-subtitle {
  font-size: 1.05rem;
  line-height: 1.6;
}

.login-btn {
  padding: 14px 28px;
}

.error-msg {
  font-size: 0.85rem;
  padding: 10px;
  background: var(--riot-red-dim);
  border-radius: var(--radius-md);
}
</style>
