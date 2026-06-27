import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import LoginView from '../views/LoginView.vue'
import MainView from '../views/MainView.vue'
import RegisterView from '../views/RegisterView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
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
      path: '/',
      name: 'home',
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
  } else if (to.path === '/login' && authStore.user) {
    return '/'
  }
})

export default router
