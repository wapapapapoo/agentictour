<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const navItems = [
  { to: '/', label: '旅行规划', icon: '✦' },
  { to: '/companion', label: '旅途陪伴', icon: '◌' },
  { to: '/create', label: '旅行创作', icon: '✎' },
]

navItems.push({ to: '/discover', label: '旅行社区', icon: '⌁' })
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink
        to="/"
        class="brand"
        aria-label="AgenticTour 首页"
      >
        <span class="brand-mark">A</span>
        <span>Agentic<span>Tour</span></span>
      </RouterLink>
      <nav aria-label="主导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
        >
          <span>{{ item.icon }}</span>{{ item.label }}
        </RouterLink>
      </nav>
      <div class="topbar-right">
        <span class="status-dot" />
        <span class="status-text">智能体在线</span>
        <button
          class="avatar"
          type="button"
          aria-label="用户菜单"
        >
          旅
        </button>
      </div>
    </header>
    <main>
      <RouterView :key="route.path" />
    </main>
  </div>
</template>
