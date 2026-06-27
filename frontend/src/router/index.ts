import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import LandingView from '../views/LandingView.vue'
import LoginView from '../views/LoginView.vue'
import MainView from '../views/MainView.vue'
import RegisterView from '../views/RegisterView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { requiresAuth: true }
    },
    {
      path: '/app',
      name: 'app',
      component: MainView,
      meta: { requiresAuth: true }
    }
  ],
})

router.beforeEach(async (to, from) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

  if (requiresAuth && !authStore.user && !authStore.loading) {
    return '/login'
  }

  if (authStore.user && !authStore.loading) {
    if (to.path === '/login' || to.path === '/') {
      return '/app'
    }
  }
})

export default router
