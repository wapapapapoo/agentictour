<script setup lang="ts">
/* global DOMTokenList, HTMLInputElement */
import { onMounted, onUpdated, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { clearSession, session } from '@/services/session'

const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const navItems = [
  { to: '/', label: '旅行规划', icon: '✦' },
  { to: '/companion', label: '旅途陪伴', icon: '◌' },
  { to: '/create', label: '旅行创作', icon: '✎' },
]

function refreshDatePlaceholder(input: { value: string; classList: DOMTokenList }) {
  input.classList.toggle('date-empty', !input.value)
}

onMounted(() => {
  globalThis.document.querySelectorAll<HTMLInputElement>('input[type="date"], input[type="datetime-local"]').forEach(refreshDatePlaceholder)
  globalThis.document.addEventListener('input', (event) => {
    const input = event.target as HTMLInputElement
    if (input.matches('input[type="date"], input[type="datetime-local"]')) {
      refreshDatePlaceholder(input)
    }
  })
})

onUpdated(() => {
  globalThis.document.querySelectorAll<HTMLInputElement>('input[type="date"], input[type="datetime-local"]').forEach(refreshDatePlaceholder)
})

function toggleAccountMenu() {
  if (!session.username) { router.push('/auth'); return }
  menuOpen.value = !menuOpen.value
}

async function logout() {
  menuOpen.value = false
  clearSession()
  await router.replace('/auth')
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/" class="brand" aria-label="AgenticTour 首页"><span class="brand-mark">A</span><span>Agentic<span>Tour</span></span></RouterLink>
      <nav aria-label="主导航"><RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link"><span>{{ item.icon }}</span>{{ item.label }}</RouterLink></nav>
      <div class="topbar-right">
        <span class="status-dot" /><span class="status-text">{{ session.username || '未登录' }}</span>
        <div class="account-menu">
          <button class="avatar" type="button" aria-label="账户菜单" :aria-expanded="menuOpen" :title="session.username ? '账户菜单' : '去登录'" @click="toggleAccountMenu">{{ session.username ? session.username.slice(0, 1).toUpperCase() : '登' }}</button>
          <div v-if="menuOpen" class="account-popover">
            <p class="account-name">{{ session.username }}</p>
            <button type="button" class="logout-action" @click="logout"><span>↪</span>退出登录</button>
          </div>
        </div>
      </div>
    </header>
    <main @click="menuOpen = false"><RouterView :key="route.path" /></main>
  </div>
</template>

<style scoped>
.account-menu{position:relative}.account-popover{position:absolute;top:44px;right:0;z-index:20;min-width:158px;padding:8px;border:1px solid #deeadf;border-radius:13px;background:rgba(255,255,255,.98);box-shadow:0 14px 30px rgba(37,80,59,.16)}.account-name{overflow:hidden;margin:4px 8px 8px;padding-bottom:8px;border-bottom:1px solid #edf2ee;color:#486055;font-size:12px;font-weight:700;text-overflow:ellipsis;white-space:nowrap}.logout-action{display:flex;width:100%;align-items:center;gap:8px;border:0;border-radius:8px;padding:9px 10px;background:transparent;color:#a04c4c;font-size:13px;text-align:left;cursor:pointer}.logout-action:hover{background:#fff1ef}.logout-action span{font-size:16px}
:global(input[type="date"].date-empty::-webkit-datetime-edit),:global(input[type="datetime-local"].date-empty::-webkit-datetime-edit){color:transparent}:global(input[type="date"].date-empty),:global(input[type="datetime-local"].date-empty){position:relative;background-image:linear-gradient(90deg,transparent,transparent)}:global(input[type="date"].date-empty::before),:global(input[type="datetime-local"].date-empty::before){position:absolute;left:11px;color:#9aa79f;content:'请选择日期';pointer-events:none}:global(input[type="datetime-local"].date-empty::before){content:'请选择日期和时间'}
</style>
