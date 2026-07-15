<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ApiError,
  api,
  type Advice,
  type Itinerary,
  type Memo,
  type Notification,
  type Trip,
} from '@/services/api'

type UiMessage = {
  role: 'user' | 'agent'
  text: string
  auditStatus?: string
  auditReason?: string | null
}

const welcomeMessage: UiMessage = {
  role: 'agent',
  text: '你好，我是 Hikari。选择一趟行程后，我会结合实时行程、位置和历史消息陪伴你。',
}
const trips = ref<Trip[]>([])
const tripId = ref<number | null>(null)
const messages = ref<UiMessage[]>([{ ...welcomeMessage }])
const message = ref('')
const error = ref('')
const loading = ref(false)
const workspaceLoading = ref(false)

const memos = ref<Memo[]>([])
const itineraries = ref<Itinerary[]>([])
const advice = ref<Advice[]>([])
const notifications = ref<Notification[]>([])
const unreadOnly = ref(true)

const memoEditingId = ref<number | null>(null)
const memoDraft = ref({ memo_text: '', reminder_time: '' })
const itineraryEditingId = ref<number | null>(null)
const itineraryDraft = ref({
  title: '',
  place_name: '',
  start_time: '',
  end_time: '',
  itinerary_type: 'play' as 'play' | 'transit',
  reminder_time: '',
  status: 'pending' as Itinerary['status'],
})
const adviceReason = ref('')
const adviceExtra = ref('')
const revisingAdviceId = ref<number | null>(null)
const revisionText = ref('')
const location = ref({
  city_adcode: '',
  place_name: '',
  latitude: null as number | null,
  longitude: null as number | null,
})
const locationOpen = ref(false)

const currentTrip = computed(() => trips.value.find((trip) => trip.id === tripId.value))
const visibleNotifications = computed(() => notifications.value.filter((item) => {
  if (item.trip_id !== tripId.value) return false
  return !unreadOnly.value || !item.read_at
}))
const unreadCount = computed(() => notifications.value.filter((item) => item.trip_id === tripId.value && !item.read_at).length)

function errorMessage(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

function stripThink(text: string) {
  return text
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/<think>[\s\S]*$/gi, '')
    .trim()
}

function parseDate(value?: string | null) {
  if (!value) return null
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  const parsed = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatDate(value?: string | null) {
  const parsed = parseDate(value)
  return parsed ? parsed.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '未设置'
}

function localInput(value?: string | null) {
  const parsed = parseDate(value)
  if (!parsed) return ''
  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function isoOrNull(value: string) {
  return value ? new Date(value).toISOString() : null
}

function locationPayload() {
  return {
    city_adcode: location.value.city_adcode,
    latitude: location.value.latitude ?? undefined,
    longitude: location.value.longitude ?? undefined,
    location_name: location.value.place_name,
  }
}

async function loadNotifications() {
  notifications.value = await api.listNotifications(false)
}

async function loadChat() {
  if (!tripId.value) return
  try {
    const history = await api.getTripChat(tripId.value)
    messages.value = history.messages.map((item) => ({
      role: item.sender_type === 'user' ? 'user' : 'agent',
      text: stripThink(item.content),
      auditStatus: item.sender_type === 'ai' ? item.audit_status : undefined,
      auditReason: item.audit_reason,
    }))
    if (!messages.value.length) messages.value = [{ ...welcomeMessage }]
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      messages.value = [{ ...welcomeMessage }]
      return
    }
    throw cause
  }
}

async function loadWorkspace() {
  if (!tripId.value) return
  workspaceLoading.value = true
  error.value = ''
  try {
    const [memoRows, itineraryRows, adviceRows] = await Promise.all([
      api.listMemos(tripId.value),
      api.listItineraries(tripId.value),
      api.listAdvice(tripId.value),
      loadNotifications(),
      loadChat(),
    ])
    memos.value = memoRows
    itineraries.value = itineraryRows
    advice.value = adviceRows
  } catch (cause) {
    error.value = errorMessage(cause, '无法读取旅途中数据。')
  } finally {
    workspaceLoading.value = false
  }
}

async function loadTrips() {
  try {
    trips.value = await api.listTrips()
    tripId.value = trips.value[0]?.id || null
  } catch (cause) {
    error.value = errorMessage(cause, '无法读取行程。')
  }
}

async function send() {
  const text = message.value.trim()
  if (!text || !tripId.value) return
  messages.value.push({ role: 'user', text })
  message.value = ''
  loading.value = true
  error.value = ''
  try {
    const reply = await api.sendChatMessage({ trip_id: tripId.value, message: text, ...locationPayload() })
    messages.value.push({
      role: 'agent',
      text: stripThink(reply.reply) || 'Hikari 本次没有生成可展示的回复。',
      auditStatus: reply.audit_status,
      auditReason: reply.audit_reason,
    })
  } catch (cause) {
    error.value = errorMessage(cause, '暂时无法获取回复。')
  } finally {
    loading.value = false
  }
}

function editMemo(item: Memo) {
  memoEditingId.value = item.memo_id
  memoDraft.value = { memo_text: item.memo_text, reminder_time: localInput(item.reminder_time) }
}

function resetMemo() {
  memoEditingId.value = null
  memoDraft.value = { memo_text: '', reminder_time: '' }
}

async function saveMemo() {
  if (!tripId.value || !memoDraft.value.memo_text.trim()) return
  error.value = ''
  try {
    const payload = {
      memo_text: memoDraft.value.memo_text.trim(),
      reminder_time: isoOrNull(memoDraft.value.reminder_time),
    }
    if (memoEditingId.value) await api.updateMemo(memoEditingId.value, payload)
    else await api.createMemo({ trip_id: tripId.value, ...payload })
    resetMemo()
    memos.value = await api.listMemos(tripId.value)
  } catch (cause) {
    error.value = errorMessage(cause, '备忘录保存失败。')
  }
}

async function removeMemo(id: number) {
  try {
    await api.deleteMemo(id)
    memos.value = memos.value.filter((item) => item.memo_id !== id)
    if (memoEditingId.value === id) resetMemo()
  } catch (cause) {
    error.value = errorMessage(cause, '备忘录删除失败。')
  }
}

function editItinerary(item: Itinerary) {
  itineraryEditingId.value = item.itinerary_id
  itineraryDraft.value = {
    title: item.title,
    place_name: item.place_name,
    start_time: localInput(item.start_time),
    end_time: localInput(item.end_time),
    itinerary_type: item.itinerary_type,
    reminder_time: localInput(item.reminder_time),
    status: item.status,
  }
}

function resetItinerary() {
  itineraryEditingId.value = null
  itineraryDraft.value = {
    title: '', place_name: '', start_time: '', end_time: '', itinerary_type: 'play', reminder_time: '', status: 'pending',
  }
}

async function saveItinerary() {
  if (!tripId.value) return
  const draft = itineraryDraft.value
  if (!draft.title.trim() || !draft.place_name.trim() || !draft.start_time || !draft.end_time) {
    error.value = '请填写完整的日程名称、地点和起止时间。'
    return
  }
  if (draft.itinerary_type === 'transit' && !draft.reminder_time) {
    error.value = '交通日程必须设置提醒时间。'
    return
  }
  error.value = ''
  try {
    const payload = {
      title: draft.title.trim(),
      place_name: draft.place_name.trim(),
      start_time: new Date(draft.start_time).toISOString(),
      end_time: new Date(draft.end_time).toISOString(),
      itinerary_type: draft.itinerary_type,
      reminder_time: isoOrNull(draft.reminder_time),
      status: draft.status,
      is_initial: false,
    }
    if (itineraryEditingId.value) await api.updateItinerary(itineraryEditingId.value, payload)
    else await api.createItinerary({ trip_id: tripId.value, ...payload })
    resetItinerary()
    itineraries.value = await api.listItineraries(tripId.value)
  } catch (cause) {
    error.value = errorMessage(cause, '日程保存失败。')
  }
}

async function removeItinerary(id: number) {
  try {
    await api.deleteItinerary(id)
    itineraries.value = await api.listItineraries(tripId.value!)
    if (itineraryEditingId.value === id) resetItinerary()
  } catch (cause) {
    error.value = errorMessage(cause, '日程删除失败。')
  }
}

async function requestAdvice() {
  if (!tripId.value || !adviceReason.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    await api.generateAdvice({
      trip_id: tripId.value,
      reason: adviceReason.value.trim(),
      additional_requirement: adviceExtra.value.trim(),
      ...locationPayload(),
    })
    adviceReason.value = ''
    adviceExtra.value = ''
    advice.value = await api.listAdvice(tripId.value)
  } catch (cause) {
    error.value = errorMessage(cause, '暂时无法生成调整建议。')
  } finally {
    loading.value = false
  }
}

async function act(item: Advice, action: 'accept' | 'reject' | 'revise') {
  const additional = action === 'revise' ? revisionText.value.trim() : ''
  if (action === 'revise' && !additional) return
  loading.value = true
  error.value = ''
  try {
    await api.actOnAdvice(item.advice_id, action, additional)
    revisingAdviceId.value = null
    revisionText.value = ''
    advice.value = await api.listAdvice(item.trip_id)
    if (action === 'accept') itineraries.value = await api.listItineraries(item.trip_id)
  } catch (cause) {
    error.value = errorMessage(cause, '建议操作失败。')
  } finally {
    loading.value = false
  }
}

async function markRead(item: Notification) {
  try {
    const updated = await api.markNotificationRead(item.notification_id)
    notifications.value = notifications.value.map((row) => row.notification_id === updated.notification_id ? updated : row)
  } catch (cause) {
    error.value = errorMessage(cause, '标记通知失败。')
  }
}

async function saveLocation() {
  if (location.value.latitude === null || location.value.longitude === null) {
    error.value = '请先填写或获取经纬度。'
    return
  }
  try {
    const saved = await api.updateLocation({
      latitude: location.value.latitude,
      longitude: location.value.longitude,
      city_adcode: location.value.city_adcode,
      place_name: location.value.place_name,
    })
    location.value.city_adcode = saved.city_adcode || location.value.city_adcode
    location.value.place_name = saved.place_name || location.value.place_name
    locationOpen.value = false
  } catch (cause) {
    error.value = errorMessage(cause, '位置保存失败。')
  }
}

function useBrowserLocation() {
  if (!navigator.geolocation) {
    error.value = '当前浏览器不支持定位。'
    return
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      location.value.latitude = position.coords.latitude
      location.value.longitude = position.coords.longitude
    },
    () => { error.value = '无法获取浏览器定位，请检查定位权限。' },
    { enableHighAccuracy: true, timeout: 10_000 },
  )
}

function adviceResult(result: string) {
  return ({ pending: '待处理', accepted: '已采纳', rejected: '已忽略', revising: '修改中', delivered: '已送达', not_required: '无需处理' } as Record<string, string>)[result] || result
}

function adviceType(type: string) {
  return ({ replan: '调整方案', itinerary_replan: '突发变化', proactive_recommendation: '主动建议', itinerary_check: '自动检查' } as Record<string, string>)[type] || type
}

function notificationType(type: string) {
  return ({ memo: '备忘提醒', initial_start: '出发提醒', next_itinerary: '下一行程', itinerary_replan: '行程变化' } as Record<string, string>)[type] || type
}

let notificationTimer: number | undefined
watch(tripId, () => {
  resetMemo()
  resetItinerary()
  messages.value = [{ ...welcomeMessage }]
  void loadWorkspace()
})
onMounted(async () => {
  await loadTrips()
  notificationTimer = window.setInterval(() => { void loadNotifications() }, 30_000)
})
onUnmounted(() => window.clearInterval(notificationTimer))
</script>

<template>
  <div class="page companion-page">
    <section class="hero">
      <div>
        <p class="eyebrow">TRAVEL COMPANION · HIKARI</p>
        <h1>旅程在发生，建议也应及时抵达。</h1>
        <p>对话、提醒、实时日程、位置与调整建议，都围绕同一趟旅行协同工作。</p>
      </div>
      <div class="hero-status"><b>{{ currentTrip?.destination_city || '等待选择' }}</b><span>{{ currentTrip?.status || '未关联行程' }}</span></div>
    </section>

    <p v-if="error" class="error">{{ error }}<button @click="error = ''">×</button></p>

    <section class="workspace-bar">
      <label>当前行程<select v-model="tripId"><option :value="null">请选择行程</option><option v-for="trip in trips" :key="trip.id" :value="trip.id">{{ trip.destination_city }} · {{ trip.title }}</option></select></label>
      <div class="workspace-actions"><button class="secondary" @click="locationOpen = !locationOpen">位置与城市</button><button class="secondary" @click="loadWorkspace">刷新数据</button><span v-if="unreadCount" class="notice-count">{{ unreadCount }} 条未读</span></div>
    </section>

    <section v-if="locationOpen" class="card location-panel">
      <div><p class="eyebrow">LIVE LOCATION</p><h2>提供给 Hikari 的当前位置</h2></div>
      <div class="location-grid"><input v-model="location.city_adcode" placeholder="城市 adcode，如 310000"><input v-model="location.place_name" placeholder="位置名称"><input v-model.number="location.longitude" type="number" step="any" placeholder="经度"><input v-model.number="location.latitude" type="number" step="any" placeholder="纬度"></div>
      <div class="panel-actions"><button class="secondary" @click="useBrowserLocation">获取浏览器定位</button><button class="primary" @click="saveLocation">保存位置</button></div>
    </section>

    <p v-if="workspaceLoading" class="loading-line">正在同步旅途数据…</p>

    <div class="main-grid">
      <section class="card chat">
        <header><div><p class="eyebrow">CONVERSATION</p><h2>和 Hikari 对话</h2></div><small>历史消息会随行程恢复</small></header>
        <div class="messages">
          <div v-for="(item, index) in messages" :key="index" class="message" :class="item.role">
            <span>{{ item.text }}</span>
            <small v-if="item.role === 'agent' && item.auditStatus" :class="['audit-mark', item.auditStatus]">审核 {{ item.auditStatus === 'pass' ? '通过' : '未通过' }}<i v-if="item.auditReason"> · {{ item.auditReason }}</i></small>
          </div>
          <div v-if="loading" class="message agent typing">Hikari 正在核对信息…</div>
        </div>
        <form class="composer" @submit.prevent="send"><input v-model="message" :disabled="loading || !tripId" placeholder="问问 Hikari 当前安排、提醒或附近建议…"><button :disabled="loading || !tripId">发送</button></form>
      </section>

      <aside class="side-stack">
        <section class="card advice-card">
          <header><div><p class="eyebrow">ADVICE</p><h2>调整建议</h2></div></header>
          <div class="advice-form"><input v-model="adviceReason" placeholder="发生了什么变化？"><input v-model="adviceExtra" placeholder="补充要求（可选）"><button :disabled="loading || !tripId" @click="requestAdvice">生成候选方案</button></div>
          <article v-for="item in advice.slice(0, 5)" :key="item.advice_id" class="advice-item">
            <div class="tag-line"><span>{{ adviceType(item.advice_type) }}</span><i>{{ adviceResult(item.result) }}</i><em :class="item.audit_status">审核{{ item.audit_status === 'pass' ? '通过' : '未通过' }}</em></div>
            <p>{{ stripThink(item.advice_text) }}</p><small v-if="item.audit_reason" class="audit-reason">{{ item.audit_reason }}</small>
            <div v-if="item.result === 'pending' || item.result === 'revising'" class="item-actions"><button @click="act(item, 'accept')">采纳</button><button class="quiet" @click="revisingAdviceId = item.advice_id">进一步修改</button><button class="quiet" @click="act(item, 'reject')">忽略</button></div>
            <div v-if="revisingAdviceId === item.advice_id" class="revision-box"><input v-model="revisionText" placeholder="说明希望如何修改"><button @click="act(item, 'revise')">提交</button></div>
          </article>
          <p v-if="!advice.length" class="muted">输入变化原因后获取待确认的调整方案。</p>
        </section>

        <section class="card notifications-card">
          <header><div><p class="eyebrow">REMINDERS</p><h2>自动提醒</h2></div><label><input v-model="unreadOnly" type="checkbox">仅未读</label></header>
          <article v-for="item in visibleNotifications.slice(0, 6)" :key="item.notification_id" class="notification-item"><div><span>{{ notificationType(item.category) }}</span><p>{{ stripThink(item.content) }}</p><small>{{ formatDate(item.created_at) }}</small></div><button v-if="!item.read_at" class="quiet" @click="markRead(item)">已读</button></article>
          <p v-if="!visibleNotifications.length" class="muted">当前没有{{ unreadOnly ? '未读' : '' }}提醒。</p>
        </section>
      </aside>
    </div>

    <div class="tool-grid">
      <section class="card tool">
        <header><div><p class="eyebrow">MEMOS</p><h2>旅途备忘</h2></div></header>
        <div class="memo-form"><input v-model="memoDraft.memo_text" placeholder="记下一件要做的事"><input v-model="memoDraft.reminder_time" type="datetime-local"><button @click="saveMemo">{{ memoEditingId ? '保存' : '添加' }}</button><button v-if="memoEditingId" class="quiet" @click="resetMemo">取消</button></div>
        <div v-for="item in memos" :key="item.memo_id" class="data-row"><div><b>{{ item.memo_text }}</b><small>提醒：{{ formatDate(item.reminder_time) }}<i v-if="item.reminded_at"> · 已发送</i></small></div><div><button class="quiet" @click="editMemo(item)">编辑</button><button class="icon" @click="removeMemo(item.memo_id)">×</button></div></div>
        <p v-if="!memos.length" class="muted">暂无备忘。</p>
      </section>

      <section class="card tool itinerary-tool">
        <header><div><p class="eyebrow">ITINERARY</p><h2>实时日程</h2></div></header>
        <div class="schedule-form"><input v-model="itineraryDraft.title" placeholder="事项名称"><input v-model="itineraryDraft.place_name" placeholder="地点"><label>开始<input v-model="itineraryDraft.start_time" type="datetime-local"></label><label>结束<input v-model="itineraryDraft.end_time" type="datetime-local"></label><select v-model="itineraryDraft.itinerary_type"><option value="play">游玩</option><option value="transit">交通</option></select><label>提醒<input v-model="itineraryDraft.reminder_time" type="datetime-local"></label><select v-model="itineraryDraft.status"><option value="pending">待执行</option><option value="done">已完成</option><option value="cancelled">已取消</option></select><div class="schedule-actions"><button @click="saveItinerary">{{ itineraryEditingId ? '保存修改' : '添加日程' }}</button><button v-if="itineraryEditingId" class="quiet" @click="resetItinerary">取消</button></div></div>
        <div v-for="item in itineraries" :key="item.itinerary_id" class="data-row itinerary-row"><div><div class="tag-line"><span>{{ item.itinerary_type === 'transit' ? '交通' : '游玩' }}</span><i>{{ item.status }}</i><em v-if="item.is_initial">当日首项</em></div><b>{{ item.title }} · {{ item.place_name }}</b><small>{{ formatDate(item.start_time) }} — {{ formatDate(item.end_time) }}<br>提醒：{{ formatDate(item.reminder_time) }}<i v-if="item.reminded_at"> · 已发送</i></small></div><div><button class="quiet" @click="editItinerary(item)">编辑</button><button class="icon" @click="removeItinerary(item.itinerary_id)">×</button></div></div>
        <p v-if="!itineraries.length" class="muted">暂无实时日程。</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.companion-page{max-width:1180px;margin:auto;padding:42px 26px 70px}.hero{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:18px;padding:30px 35px;border:1px solid #dcebdd;border-radius:24px;background:radial-gradient(circle at 90% 35%,#d8f0df 0,transparent 24%),linear-gradient(115deg,#fff,#eef9f1)}.eyebrow{margin:0 0 7px;color:#579379;letter-spacing:.13em;font-size:11px;font-weight:700}.hero h1{margin:0;color:#254838;font:700 clamp(28px,4vw,40px)/1.3 'Noto Serif SC','Microsoft YaHei',serif}.hero p:last-child,.muted{color:#728178;font-size:13px;line-height:1.7}.hero-status{display:grid;min-width:130px;gap:4px;padding:16px;border-radius:18px;background:#fff9;color:#315745;text-align:center}.hero-status b{font-size:16px}.hero-status span{color:#7f9187;font-size:11px}.error{display:flex;justify-content:space-between;align-items:center;border:1px solid #f0d0cc;border-radius:10px;padding:10px 13px;background:#fff5f3;color:#ad4d4d;font-size:13px}.error button{border:0;background:transparent;color:inherit;cursor:pointer}.workspace-bar{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:17px}.workspace-bar label{display:flex;align-items:center;gap:10px;color:#52675c;font-size:13px;font-weight:700}.workspace-bar select{min-width:250px;border:1px solid #dce8df;border-radius:9px;padding:9px;background:#fff}.workspace-actions{display:flex;align-items:center;gap:8px}.notice-count{border-radius:999px;padding:5px 9px;background:#e5f4e9;color:#2d795a;font-size:11px;font-weight:700}.card{border:1px solid #e0e9e2;border-radius:18px;background:#fff;box-shadow:0 10px 28px rgba(39,91,66,.06)}.card header{display:flex;justify-content:space-between;align-items:center;padding:18px 20px;border-bottom:1px solid #edf2ee}.card h2{margin:0;color:#345344;font-size:17px}.card header small,.card header label{color:#849188;font-size:11px}.main-grid{display:grid;grid-template-columns:minmax(0,1fr) 365px;gap:18px}.chat{display:flex;min-height:560px;overflow:hidden;flex-direction:column}.messages{display:flex;min-height:360px;max-height:560px;flex:1;overflow:auto;flex-direction:column;gap:11px;padding:20px}.message{display:grid;max-width:82%;gap:6px;padding:10px 12px;border-radius:11px;font-size:14px;line-height:1.6}.message.agent{align-self:flex-start;background:#ecf7f0;color:#3e5e51}.message.user{align-self:flex-end;background:#2b8668;color:#fff}.message.typing{opacity:.7}.audit-mark{font-size:10px;font-style:normal}.audit-mark.pass{color:#4c8a6d}.audit-mark.failed{color:#b55b55}.audit-mark i{font-style:normal}.composer{display:flex;gap:8px;padding:12px;border-top:1px solid #edf2ee}.composer input,.advice-form input,.memo-form input,.schedule-form input,.schedule-form select,.revision-box input,.location-grid input{box-sizing:border-box;min-width:0;border:1px solid #dfe9e1;border-radius:8px;padding:9px;outline:none}.composer input{flex:1}.composer input:focus,.advice-form input:focus,.memo-form input:focus,.schedule-form input:focus,.location-grid input:focus{border-color:#72ae91;box-shadow:0 0 0 3px #eaf5ed}.composer button,.advice-form button,.memo-form button,.schedule-form button,.revision-box button,.primary{border:0;border-radius:8px;padding:9px 13px;background:#2f8063;color:#fff;font-weight:700;cursor:pointer}.composer button:disabled,.advice-form button:disabled{opacity:.55;cursor:wait}.secondary,.quiet,.icon{border:1px solid #dce8df;border-radius:8px;padding:8px 10px;background:#fff;color:#4f7563;cursor:pointer}.side-stack{display:grid;gap:18px;align-content:start}.advice-form{display:grid;gap:8px;padding:14px}.advice-item,.notification-item{padding:14px 16px;border-top:1px solid #edf2ee}.advice-item p,.notification-item p{margin:8px 0;color:#52675d;font-size:13px;line-height:1.65}.tag-line{display:flex;align-items:center;gap:6px}.tag-line span,.tag-line i,.tag-line em{border-radius:999px;padding:3px 7px;background:#eaf5ee;color:#4b8068;font-size:10px;font-style:normal}.tag-line i{background:#f3f5f2;color:#758279}.tag-line em.failed{background:#fff0ee;color:#b15c56}.audit-reason{display:block;margin-bottom:8px;color:#aa625d;line-height:1.5}.item-actions,.revision-box,.panel-actions,.schedule-actions{display:flex;gap:7px}.item-actions button{border:0;border-radius:7px;padding:7px 9px;background:#e6f3ea;color:#397458;cursor:pointer}.revision-box{margin-top:9px}.revision-box input{flex:1}.notifications-card header label{display:flex;align-items:center;gap:4px}.notification-item{display:flex;justify-content:space-between;gap:10px}.notification-item>div>span{color:#458064;font-size:10px;font-weight:700}.notification-item small{color:#929e97;font-size:10px}.notification-item button{align-self:center}.tool-grid{display:grid;grid-template-columns:1fr 1.3fr;gap:18px;margin-top:18px}.tool{padding-bottom:12px}.memo-form{display:grid;grid-template-columns:minmax(0,1fr) 190px auto auto;gap:8px;padding:14px}.schedule-form{display:grid;grid-template-columns:1fr 1fr;gap:9px;padding:14px}.schedule-form label{display:grid;gap:5px;color:#6f8077;font-size:11px}.schedule-actions{align-items:end}.data-row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 14px;padding:12px 2px;border-top:1px solid #edf2ee;color:#566b60;font-size:13px}.data-row>div:first-child{display:grid;gap:5px}.data-row small{color:#89958e;font-size:10px;line-height:1.55}.data-row small i{color:#4f876d;font-style:normal}.data-row .icon{margin-left:5px;border:0;color:#ae6262}.itinerary-row{align-items:start}.location-panel{margin-bottom:17px;padding:18px 20px}.location-panel h2{margin:0;color:#345344;font-size:17px}.location-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0}.panel-actions{justify-content:flex-end}.loading-line{color:#6e8679;font-size:12px;text-align:center}
@media(max-width:920px){.main-grid,.tool-grid{grid-template-columns:1fr}.chat{min-height:480px}.side-stack{grid-template-columns:1fr 1fr}.location-grid{grid-template-columns:1fr 1fr}}
@media(max-width:680px){.companion-page{padding:26px 16px 55px}.hero{display:block;padding:25px 22px}.hero-status{display:none}.workspace-bar,.workspace-bar label{align-items:stretch;flex-direction:column}.workspace-bar select{width:100%;min-width:0}.workspace-actions{flex-wrap:wrap}.side-stack{grid-template-columns:1fr}.memo-form,.schedule-form,.location-grid{grid-template-columns:1fr}.message{max-width:92%}.card header{padding:15px}.notification-item{align-items:flex-start}.schedule-actions{align-items:center}}
</style>
