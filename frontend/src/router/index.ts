import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'planner', component: () => import('@/views/Home.vue') },
    { path: '/companion', name: 'companion', component: () => import('@/views/Companion.vue') },
    { path: '/create', name: 'create', component: () => import('@/views/Create.vue') },
    { path: '/discover', name: 'discover', component: () => import('@/views/Discover.vue') },
    { path: '/search', name: 'search', component: () => import('@/views/Search.vue') },
  ],
})

export default router
