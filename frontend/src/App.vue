<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <div class="app-shell">
    <header>
      <div class="brand">
        <span class="logo">🧳</span>
        <span class="title">AgenticTour</span>
      </div>
      <nav>
        <RouterLink
          to="/"
          :class="{ active: route.path === '/' }"
        >
          <span class="icon">🏠</span> 首页
        </RouterLink>
        <RouterLink
          to="/plan"
          :class="{ active: route.path === '/plan' }"
        >
          <span class="icon">📋</span> 旅行计划
        </RouterLink>
        <RouterLink
          to="/companion"
          :class="{ active: route.path === '/companion' }"
        >
          <span class="icon">🤖</span> AI陪伴
        </RouterLink>
        <RouterLink
          to="/blog"
          :class="{ active: route.path === '/blog' }"
        >
          <span class="icon">✍️</span> 游记创作
        </RouterLink>
      </nav>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  padding: 0 2rem;
  height: 64px;
  background: rgba(15, 15, 30, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.logo {
  font-size: 1.8rem;
}

.title {
  font-size: 1.25rem;
  font-weight: 700;
  background: linear-gradient(135deg, #42b883, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

nav {
  display: flex;
  gap: 0.25rem;
}

nav a {
  color: #94a3b8;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.9rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

nav a:hover {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
}

nav a.active {
  color: #42b883;
  background: rgba(66, 184, 131, 0.1);
}

.icon {
  font-size: 1rem;
}

main {
  flex: 1;
}
</style>
