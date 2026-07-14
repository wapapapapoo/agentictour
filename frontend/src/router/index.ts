import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '@/services/session'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'planner', component: () => import('@/views/Home.vue'), meta: { requiresAuth: true } },
    { path: '/companion', name: 'companion', component: () => import('@/views/Companion.vue'), meta: { requiresAuth: true } },
    { path: '/create', name: 'create', component: () => import('@/views/Create.vue'), meta: { requiresAuth: true } },
    { path: '/search', name: 'search', component: () => import('@/views/Search.vue'), meta: { requiresAuth: true } },
    { path: '/auth', name: 'auth', component: () => import('@/views/Auth.vue'), meta: { guestOnly: true } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthenticated()) return { name: 'auth', query: { redirect: to.fullPath } }
  if (to.meta.guestOnly && isAuthenticated()) return { name: 'planner' }
  return true
})

export default router
