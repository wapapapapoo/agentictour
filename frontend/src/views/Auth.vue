<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { saveSession } from '@/services/session'

const router = useRouter()
const route = useRoute()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const nickname = ref('')
const loading = ref(false)
const error = ref('')
const submitText = computed(() => (mode.value === 'login' ? '登录并继续' : '创建账号并继续'))

async function submit() {
  error.value = ''
  if (!username.value.trim() || !password.value) { error.value = '请输入用户名和密码。'; return }
  if (mode.value === 'register' && password.value.length < 6) { error.value = '密码至少需要 6 个字符。'; return }
  loading.value = true
  try {
    const result = mode.value === 'login'
      ? await api.login({ username: username.value.trim(), password: password.value })
      : await api.register({ username: username.value.trim(), password: password.value, nickname: nickname.value.trim() || undefined })
    saveSession({ accessToken: result.access_token, userId: result.user_id, username: result.username })
    await router.replace(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '暂时无法完成登录，请稍后重试。'
  } finally { loading.value = false }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-intro">
      <RouterLink class="brand" to="/"><span>A</span>AgenticTour</RouterLink>
      <p class="eyebrow">YOUR TRAVEL WORKSPACE</p>
      <h1>让每一次出发，<br>都有清晰的方向。</h1>
      <p>登录后可保存行程、调用智能规划，并在旅途中持续获得陪伴。</p>
    </div>
    <form class="auth-card" @submit.prevent="submit">
      <div class="mode-switch"><button type="button" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button><button type="button" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button></div>
      <h2>{{ mode === 'login' ? '欢迎回来' : '创建你的账号' }}</h2>
      <p class="subcopy">{{ mode === 'login' ? '继续你的旅行计划。' : '使用真实账号保存你的旅行数据。' }}</p>
      <label>用户名<input v-model="username" autocomplete="username" maxlength="64" placeholder="请输入用户名"></label>
      <label v-if="mode === 'register'">昵称（可选）<input v-model="nickname" maxlength="64" placeholder="旅行中的称呼"></label>
      <label>密码<input v-model="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" placeholder="至少 6 位"></label>
      <p v-if="error" class="form-error">{{ error }}</p>
      <button class="submit" :disabled="loading">{{ loading ? '正在处理…' : submitText }} <span>→</span></button>
    </form>
  </section>
</template>

<style scoped>
.auth-page{min-height:calc(100vh - 70px);display:grid;grid-template-columns:1.15fr .85fr;align-items:center;gap:clamp(48px,9vw,150px);padding:clamp(42px,8vw,110px);background:radial-gradient(circle at 12% 14%,#e3f1e6 0,transparent 27%),#f8faf6}.brand{color:#1c4839;text-decoration:none;font:700 21px/1 'Georgia','Microsoft YaHei',serif}.brand span{display:inline-grid;place-items:center;width:29px;height:29px;margin-right:8px;border-radius:9px;background:#2d6955;color:white;font:700 16px/1 system-ui}.eyebrow{margin:54px 0 14px;color:#5a917a;letter-spacing:.16em;font-size:11px;font-weight:700}.auth-intro h1{margin:0;color:#224637;font:700 clamp(32px,4vw,58px)/1.22 'Noto Serif SC','Microsoft YaHei',serif}.auth-intro>p:last-child{max-width:430px;color:#718078;line-height:1.9}.auth-card{width:min(100%,420px);padding:36px;border:1px solid #e3ebe2;border-radius:24px;background:rgba(255,255,255,.9);box-shadow:0 22px 55px rgba(48,91,70,.12)}.mode-switch{display:grid;grid-template-columns:1fr 1fr;padding:4px;border-radius:11px;background:#f0f4ef}.mode-switch button{border:0;border-radius:8px;background:transparent;padding:9px;color:#78857d;cursor:pointer}.mode-switch .active{background:#fff;color:#256047;box-shadow:0 2px 8px #cfdacf}.auth-card h2{margin:30px 0 5px;color:#284b3d;font:700 25px 'Noto Serif SC','Microsoft YaHei',serif}.subcopy{margin:0 0 24px;color:#849087;font-size:13px}.auth-card label{display:grid;gap:8px;margin:16px 0;color:#506359;font-size:13px;font-weight:600}.auth-card input{box-sizing:border-box;width:100%;border:1px solid #dce6dc;border-radius:11px;padding:12px;background:#fcfdfb;color:#253b31;outline:none}.auth-card input:focus{border-color:#559777;box-shadow:0 0 0 3px #e2f1e7}.form-error{margin:14px 0;color:#b85050;font-size:13px}.submit{width:100%;margin-top:12px;border:0;border-radius:12px;padding:13px 16px;background:#2c6a53;color:white;font-weight:700;cursor:pointer;transition:.2s}.submit:hover:not(:disabled){background:#235a45}.submit:disabled{opacity:.65;cursor:wait}.submit span{float:right;font-size:18px;line-height:.8}@media(max-width:760px){.auth-page{grid-template-columns:1fr;padding:44px 22px;gap:38px}.eyebrow{margin-top:35px}.auth-intro h1{font-size:36px}.auth-card{box-sizing:border-box;width:100%}}
</style>
