<script setup lang="ts">
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { clearSession, session } from '@/services/session'

const route = useRoute()
const router = useRouter()
const navItems = [
  { to: '/', label: '旅行规划', icon: '✦' },
  { to: '/companion', label: '旅途陪伴', icon: '◌' },
  { to: '/create', label: '旅行创作', icon: '✎' },
]

async function logout() { clearSession(); await router.replace('/auth') }
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/" class="brand" aria-label="AgenticTour 首页"><span class="brand-mark">A</span><span>Agentic<span>Tour</span></span></RouterLink>
      <nav aria-label="主导航">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link"><span>{{ item.icon }}</span>{{ item.label }}</RouterLink>
      </nav>
      <div class="topbar-right">
        <span class="status-dot" /><span class="status-text">{{ session.username || '未登录' }}</span>
        <button class="avatar" type="button" aria-label="账户操作" :title="session.username ? '退出登录' : '去登录'" @click="session.username ? logout() : router.push('/auth')">{{ session.username ? session.username.slice(0, 1).toUpperCase() : '登' }}</button>
      </div>
    </header>
    <main><RouterView :key="route.path" /></main>
  </div>
</template>
