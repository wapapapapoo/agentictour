import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/Home.vue'),
    },
    {
      path: '/plan',
      name: 'plan',
      component: () => import('@/views/Plan.vue'),
    },
    {
      path: '/companion',
      name: 'companion',
      component: () => import('@/views/Companion.vue'),
    },
    {
      path: '/blog',
      name: 'blog',
      component: () => import('@/views/Blog.vue'),
    },
  ],
})

export default router
