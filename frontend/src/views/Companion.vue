<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import DatePicker from '@/components/DatePicker.vue'
import TimeSelect from '@/components/TimeSelect.vue'
import {
  ApiError,
  api,
  type Advice,
  type Itinerary,
  type Location,
  type Memo,
  type Notification,
  type Plan,
  type Trip,
} from '@/services/api'
import MemoPanel from '@/components/MemoPanel.vue'
import { extractReferenceSources, renderMarkdown, stripReferenceSection } from '@/utils/markdown'
import { formatTripDate, tripInputFromUtc, tripInputToUtc } from '@/utils/tripTime'
import { itineraryDate, preferredItineraryDate, tripDateRange } from '@/utils/itineraryDay'
import {
  itineraryLifecycle,
  itineraryLifecycleLabel,
  tripLifecycle,
  tripLifecycleLabel,
  type TripLifecycle,
} from '@/utils/travelLifecycle'
import {
  acceptAutomaticAdjustment,
  closedAdjustment,
  openAutomaticAdjustment,
  openManualAdjustment,
  showAdjustmentCandidate,
} from '@/utils/adjustmentFlow'

type UiMessage = {
  role: 'user' | 'agent'
  text: string
  auditStatus?: string
  auditReason?: string | null
}

type DeleteTarget = {
  kind: 'trip' | 'memo' | 'itinerary'
  id: number
  label: string
}

const welcomeMessage: UiMessage = {
  role: 'agent',
  text: '你好，我是 Hikari。选择一趟行程后，我会结合实时行程、位置和历史消息陪伴你。',
}
const trips = ref<Trip[]>([])
const plans = ref<Plan[]>([])
const tripId = ref<number | null>(null)
const messages = ref<UiMessage[]>([{ ...welcomeMessage }])
const message = ref('')
const error = ref('')
const loading = ref(false)
const chatLoading = ref(false)
const adjustmentOperation = ref('')
const workspaceLoading = ref(false)
const lifecycleClock = ref(new Date())

const memos = ref<Memo[]>([])
const itineraries = ref<Itinerary[]>([])
const advice = ref<Advice[]>([])
const notifications = ref<Notification[]>([])
const unreadOnly = ref(false)
const reminderDialogOpen = ref(false)
const notificationBusy = ref(false)
const reminderError = ref('')
const memoFilter = ref<'all' | 'pending' | 'sent' | 'unscheduled'>('all')
const itineraryFilter = ref<'all' | 'upcoming' | 'ongoing' | 'change_pending' | 'completed' | 'cancelled'>('all')
const selectedItineraryDate = ref('')

const memoEditingId = ref<number | null>(null)
const memoDraft = ref({ memo_text: '', reminder_date: '', reminder_clock: '' })
const memoDialogOpen = ref(false)
const memoFormError = ref('')
const itineraryEditingId = ref<number | null>(null)
const itineraryDraft = ref({
  title: '',
  place_name: '',
  start_date: '',
  start_clock: '',
  end_date: '',
  end_clock: '',
  itinerary_type: 'play' as 'play' | 'transit',
  reminder_date: '',
  reminder_clock: '',
  status: 'pending' as Itinerary['status'],
})
const itineraryDialogOpen = ref(false)
const itineraryFormError = ref('')
const deleteTarget = ref<DeleteTarget | null>(null)
const adjustment = ref(closedAdjustment())
const adjustmentError = ref('')
const promptedAutomaticAdviceId = ref<number | null>(null)
const location = ref<Location | null>(null)
const locationRefreshing = ref(false)
const browserCoordinates = ref({
  city_adcode: '',
  place_name: '',
  latitude: null as number | null,
  longitude: null as number | null,
})
const locationContext = computed<Record<string, unknown>>(() => {
  if (!location.value?.location_context) return {}
  try { return JSON.parse(location.value.location_context) as Record<string, unknown> } catch { return {} }
})
const locationResolutionError = computed(() => (
  locationContext.value.resolution_status === 'failed'
    ? String(locationContext.value.resolution_error || '高德地址解析失败')
    : ''
))
const locationResolutionHint = computed(() => {
  const detail = locationResolutionError.value
  if (!detail) return ''
  if (detail.includes('No module named')) {
    return '后端运行依赖不完整，请重新构建并部署后端容器。'
  }
  if (detail.includes('AMAP_KEY')) {
    return '请确认 backend/.env 中已配置高德 Web 服务 Key，并重新创建后端容器。'
  }
  return '请检查高德 Web 服务 Key、接口权限及服务器网络，然后点击“刷新”重试。'
})
const locationCoordinateLabel = computed(() => (
  locationContext.value.coordinate_system === 'gcj02' ? '高德坐标' : '浏览器坐标'
))

const currentTrip = computed(() => trips.value.find((trip) => trip.id === tripId.value))
const ongoingTrip = computed(() => trips.value.find(
  (trip) => tripLifecycle(trip, lifecycleClock.value) === 'ongoing',
))
const nextTrip = computed(() => trips.value
  .filter((trip) => tripLifecycle(trip, lifecycleClock.value) === 'upcoming')
  .sort((left, right) => left.start_date.localeCompare(right.start_date))[0])
const featuredTrip = computed(() => ongoingTrip.value || currentTrip.value || nextTrip.value || trips.value[0])
const featuredTripState = computed<TripLifecycle | null>(() => (
  featuredTrip.value ? tripLifecycle(featuredTrip.value, lifecycleClock.value) : null
))
const currentTripState = computed<TripLifecycle | null>(() => (
  currentTrip.value ? tripLifecycle(currentTrip.value, lifecycleClock.value) : null
))
const replanAdvice = computed(() => advice.value.filter((item) => ['replan', 'itinerary_replan'].includes(item.advice_type)))
const pendingAutomaticAdvice = computed(() => replanAdvice.value.find((item) => (
  item.advice_type === 'itinerary_replan'
  && item.result === 'pending'
  && item.audit_status === 'pass'
)))
const pendingManualAdvice = computed(() => replanAdvice.value.find((item) => (
  item.advice_type === 'replan'
  && ['pending', 'revising'].includes(item.result)
  && item.audit_status === 'pass'
  && !automaticRootForAdvice(item)
)))
const latestReplanAdvice = computed(() => [...replanAdvice.value]
  .sort((left, right) => right.advice_id - left.advice_id)[0])
const legacyFailedAdvice = computed(() => (
  latestReplanAdvice.value?.audit_status === 'failed' ? latestReplanAdvice.value : undefined
))
const activeCandidate = computed(() => advice.value.find(
  (item) => item.advice_id === adjustment.value.candidateAdviceId,
))
const currentTripNotifications = computed(() => notifications.value
  .filter((item) => item.trip_id === tripId.value)
  .sort((left, right) => right.created_at.localeCompare(left.created_at)))
const visibleNotifications = computed(() => currentTripNotifications.value.filter(
  (item) => !unreadOnly.value || !item.read_at,
))
const unreadCount = computed(() => currentTripNotifications.value.filter((item) => !item.read_at).length)
const ongoingItinerary = computed(() => itineraries.value.find(
  (item) => itineraryLifecycle(item, lifecycleClock.value) === 'ongoing',
))
const nextItinerary = computed(() => itineraries.value
  .filter((item) => itineraryLifecycle(item, lifecycleClock.value) === 'upcoming')
  .sort((left, right) => left.start_time.localeCompare(right.start_time))[0])
const adjustableItineraries = computed(() => itineraries.value.filter(
  (item) => ['pending', 'change_pending'].includes(item.status)
    && ['upcoming', 'ongoing', 'change_pending'].includes(itineraryLifecycle(item, lifecycleClock.value)),
))
const filteredMemos = computed(() => memos.value.filter((item) => ({
  all: true,
  pending: Boolean(item.reminder_time && !item.reminded_at),
  sent: Boolean(item.reminded_at),
  unscheduled: !item.reminder_time,
}[memoFilter.value])))
const filteredItineraries = computed(() => itineraries.value.filter((item) => (
  itineraryFilter.value === 'all'
  || itineraryLifecycle(item, lifecycleClock.value) === itineraryFilter.value
)))
const itineraryDates = computed(() => tripDateRange(
  currentTrip.value?.start_date,
  currentTrip.value?.end_date,
))
const displayedItineraries = computed(() => filteredItineraries.value.filter((item) => (
  !selectedItineraryDate.value
  || itineraryDate(item.start_time) === selectedItineraryDate.value
)))

function errorMessage(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

function stripThink(text: string) {
  return text
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/<think>[\s\S]*$/gi, '')
    .trim()
}

function adviceItineraryIds(item: Advice | undefined, key: string) {
  if (!item?.proposed_itinerary || typeof item.proposed_itinerary !== 'object') return []
  const values = (item.proposed_itinerary as Record<string, unknown>)[key]
  if (!Array.isArray(values)) return []
  return values.filter((value): value is number => Number.isInteger(value))
}

function automaticConflictIds(item: Advice | undefined) {
  const eligible = new Set(adjustableItineraries.value.map((row) => row.itinerary_id))
  return adviceItineraryIds(item, 'conflicting_itinerary_ids').filter((id) => eligible.has(id))
}

function automaticRootForAdvice(item: Advice | undefined) {
  if (!item) return undefined
  const byId = new Map(advice.value.map((row) => [row.advice_id, row]))
  let current: Advice | undefined = item
  const seen = new Set<number>()
  while (current) {
    if (seen.has(current.advice_id)) return undefined
    seen.add(current.advice_id)
    if (current.advice_type === 'itinerary_replan') return current
    current = current.parent_advice_id ? byId.get(current.parent_advice_id) : undefined
  }
  return undefined
}

function latestAutomaticCandidate(root: Advice) {
  return advice.value
    .filter((item) => (
      item.advice_type === 'replan'
      && ['pending', 'revising'].includes(item.result)
      && automaticRootForAdvice(item)?.advice_id === root.advice_id
    ))
    .sort((left, right) => right.advice_id - left.advice_id)[0]
}

function notificationAdvice(item: Notification) {
  return item.advice_id
    ? advice.value.find((row) => row.advice_id === item.advice_id)
    : undefined
}

function notificationAdviceStatus(item: Notification) {
  const row = notificationAdvice(item)
  if (!row || item.category !== 'itinerary_replan') return ''
  return ({
    pending: '待处理',
    accepted: '已采纳调整',
    kept: '已保留原行程',
    cancelled_original: '已取消原行程',
    rejected: '已放弃',
  } as Record<string, string>)[row.result] || adviceResult(row.result)
}

function notificationIsActionable(item: Notification) {
  const row = notificationAdvice(item)
  return item.category === 'itinerary_replan' && row?.result === 'pending'
}

function hydrateAdjustmentScope(item: Advice) {
  const eligible = new Set(adjustableItineraries.value.map((row) => row.itinerary_id))
  const lockedSource = adviceItineraryIds(item, 'locked_itinerary_ids')
  const locked = (lockedSource.length ? lockedSource : adviceItineraryIds(item, 'conflicting_itinerary_ids'))
    .filter((id) => eligible.has(id))
  const selected = adviceItineraryIds(item, 'selected_itinerary_ids').filter((id) => eligible.has(id))
  adjustment.value.lockedItineraryIds = locked
  adjustment.value.selectedItineraryIds = [...new Set([...selected, ...locked])]
}

function toggleConflict(itineraryId: number, checked: boolean) {
  if (adjustment.value.lockedItineraryIds.includes(itineraryId)) return
  const selected = new Set(adjustment.value.selectedItineraryIds)
  if (checked) selected.add(itineraryId)
  else selected.delete(itineraryId)
  adjustment.value.selectedItineraryIds = [...selected]
}

function changeConflict(itineraryId: number, event: unknown) {
  const target = (event as { target?: { checked?: boolean } }).target
  toggleConflict(itineraryId, Boolean(target?.checked))
}

function formatDate(value?: string | null) {
  return formatTripDate(value)
}

function localInput(value?: string | null) {
  return tripInputFromUtc(value)
}

function isoOrNull(value: string) {
  return tripInputToUtc(value)
}

function splitDateTime(value?: string | null) {
  const local = localInput(value)
  return { date: local.slice(0, 10), clock: local.slice(11, 16) }
}

function normalizeClock(value: string) {
  const compact = value.trim()
  const digits = /^\d{3,4}$/.test(compact) ? compact.padStart(4, '0') : ''
  const normalized = digits
    ? `${digits.slice(0, 2)}:${digits.slice(2)}`
    : compact.replace(/^(\d):(\d{2})$/, '0$1:$2')
  const matched = /^(\d{2}):(\d{2})$/.exec(normalized)
  return matched && Number(matched[1]) < 24 && Number(matched[2]) < 60
    ? normalized
    : ''
}

function joinDateTime(date: string, clock: string) {
  const normalizedClock = normalizeClock(clock)
  return date && normalizedClock ? `${date}T${normalizedClock}` : ''
}

function reminderSameAsStart() {
  itineraryDraft.value.reminder_date = itineraryDraft.value.start_date
  itineraryDraft.value.reminder_clock = itineraryDraft.value.start_clock
}

function clearItineraryReminder() {
  itineraryDraft.value.reminder_date = ''
  itineraryDraft.value.reminder_clock = ''
}

function dateWithinCurrentTrip(value: string) {
  if (!value || !currentTrip.value) return true
  const dateKey = value.slice(0, 10)
  return currentTrip.value.start_date <= dateKey && dateKey <= currentTrip.value.end_date
}

function locationPayload() {
  return {
    city_adcode: location.value?.city_adcode || '',
    latitude: location.value?.latitude ?? undefined,
    longitude: location.value?.longitude ?? undefined,
    location_name: location.value?.place_name || '',
  }
}

async function loadNotifications() {
  notifications.value = await api.listNotifications(false)
}

async function loadChat(targetTripId: number): Promise<UiMessage[]> {
  try {
    const history = await api.getTripChat(targetTripId)
    const restored: UiMessage[] = history.messages.map((item) => ({
      role: item.sender_type === 'user' ? 'user' : 'agent',
      text: stripThink(item.content),
      auditStatus: item.sender_type === 'ai' ? item.audit_status : undefined,
      auditReason: item.audit_reason,
    }))
    const rows = restored.filter((item, index) => {
      const previous = restored[index - 1]
      return !(
        item.role === 'user'
        && previous?.role === 'user'
        && item.text.trim() === previous.text.trim()
      )
    })
    return rows.length ? rows : [{ ...welcomeMessage }]
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      return [{ ...welcomeMessage }]
    }
    throw cause
  }
}

let workspaceRequestId = 0
async function loadWorkspace() {
  const targetTripId = tripId.value
  if (!targetTripId) return
  const requestId = ++workspaceRequestId
  workspaceLoading.value = true
  error.value = ''
  try {
    const [memoRows, itineraryRows, adviceRows, , chatRows] = await Promise.all([
      api.listMemos(targetTripId),
      api.listItineraries(targetTripId),
      api.listAdvice(targetTripId),
      loadNotifications(),
      loadChat(targetTripId),
    ])
    if (requestId !== workspaceRequestId || tripId.value !== targetTripId) return
    memos.value = memoRows
    itineraries.value = itineraryRows
    advice.value = adviceRows
    messages.value = chatRows
  } catch (cause) {
    error.value = errorMessage(cause, '无法读取旅途中数据。')
  } finally {
    if (requestId === workspaceRequestId) workspaceLoading.value = false
  }
}

async function loadTrips(preserveSelection = false) {
  const selectedTripId = tripId.value
  try {
    const tripRows = await api.listTrips()
    const fetchPlans = (api as { listPlans?: () => Promise<Plan[]> }).listPlans
    if (typeof fetchPlans === 'function') {
      try {
        const planRows = await fetchPlans()
        plans.value = planRows
        const plannedTripIds = new Set(planRows.filter((plan) => plan.companion_imported !== false).map((plan) => plan.trip_id))
        trips.value = tripRows.filter((trip) => plannedTripIds.has(trip.id))
      } catch {
        plans.value = []
        trips.value = tripRows
      }
    } else {
      plans.value = []
      trips.value = tripRows
    }
    const active = trips.value.find((trip) => tripLifecycle(trip, lifecycleClock.value) === 'ongoing')
    const upcoming = trips.value
      .filter((trip) => tripLifecycle(trip, lifecycleClock.value) === 'upcoming')
      .sort((left, right) => left.start_date.localeCompare(right.start_date))[0]
    tripId.value = preserveSelection && trips.value.some((trip) => trip.id === selectedTripId)
      ? selectedTripId
      : active?.id || upcoming?.id || trips.value[0]?.id || null
  } catch (cause) {
    error.value = errorMessage(cause, '无法读取行程。')
  }
}

async function send() {
  const text = message.value.trim()
  if (!text || !tripId.value || chatLoading.value) return
  loading.value = true
  chatLoading.value = true
  messages.value.push({ role: 'user', text })
  message.value = ''
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
    chatLoading.value = false
    loading.value = false
  }
}

function editMemo(item: Memo) {
  error.value = ''
  memoFormError.value = ''
  memoEditingId.value = item.memo_id
  const reminder = splitDateTime(item.reminder_time)
  memoDraft.value = {
    memo_text: item.memo_text,
    reminder_date: reminder.date,
    reminder_clock: reminder.clock,
  }
  memoDialogOpen.value = true
}

function openMemoDialog() {
  resetMemo()
  error.value = ''
  memoFormError.value = ''
  memoDialogOpen.value = true
}

function closeMemoDialog() {
  memoDialogOpen.value = false
  memoFormError.value = ''
  resetMemo()
}

function resetMemo() {
  memoEditingId.value = null
  memoDraft.value = { memo_text: '', reminder_date: '', reminder_clock: '' }
}

async function saveMemo() {
  if (!tripId.value || !memoDraft.value.memo_text.trim()) {
    memoFormError.value = '请填写备忘内容。'
    return
  }
  const hasReminderPart = Boolean(memoDraft.value.reminder_date || memoDraft.value.reminder_clock)
  const reminderTime = joinDateTime(memoDraft.value.reminder_date, memoDraft.value.reminder_clock)
  if (hasReminderPart && !reminderTime) {
    memoFormError.value = '提醒日期、小时和分钟需要同时选择。'
    return
  }
  if (reminderTime && !dateWithinCurrentTrip(reminderTime)) {
    memoFormError.value = '备忘提醒时间必须位于当前计划的开始与结束日期内。'
    return
  }
  error.value = ''
  memoFormError.value = ''
  try {
    const payload = {
      memo_text: memoDraft.value.memo_text.trim(),
      reminder_time: isoOrNull(reminderTime),
    }
    if (memoEditingId.value) await api.updateMemo(memoEditingId.value, payload)
    else await api.createMemo({ trip_id: tripId.value, ...payload })
    memoDialogOpen.value = false
    resetMemo()
    memos.value = await api.listMemos(tripId.value)
  } catch (cause) {
    memoFormError.value = errorMessage(cause, '备忘录保存失败。')
  }
}

function editItinerary(item: Itinerary) {
  error.value = ''
  itineraryFormError.value = ''
  itineraryEditingId.value = item.itinerary_id
  const start = splitDateTime(item.start_time)
  const end = splitDateTime(item.end_time)
  const reminder = splitDateTime(item.reminder_time)
  itineraryDraft.value = {
    title: item.title,
    place_name: item.place_name,
    start_date: start.date,
    start_clock: start.clock,
    end_date: end.date,
    end_clock: end.clock,
    itinerary_type: item.itinerary_type,
    reminder_date: reminder.date,
    reminder_clock: reminder.clock,
    status: item.status,
  }
  itineraryDialogOpen.value = true
}

function openItineraryDialog() {
  resetItinerary()
  error.value = ''
  itineraryFormError.value = ''
  itineraryDialogOpen.value = true
}

function closeItineraryDialog() {
  itineraryDialogOpen.value = false
  itineraryFormError.value = ''
  resetItinerary()
}

function resetItinerary() {
  itineraryEditingId.value = null
  const defaultDate = selectedItineraryDate.value || currentTrip.value?.start_date || ''
  itineraryDraft.value = {
    title: '', place_name: '', start_date: defaultDate, start_clock: '09:00', end_date: defaultDate, end_clock: '10:00', itinerary_type: 'play', reminder_date: '', reminder_clock: '', status: 'pending',
  }
}

watch(() => itineraryDraft.value.itinerary_type, (type) => {
  if (type === 'transit' && !joinDateTime(itineraryDraft.value.reminder_date, itineraryDraft.value.reminder_clock)) {
    reminderSameAsStart()
  }
})

async function saveItinerary() {
  if (!tripId.value) return
  const draft = itineraryDraft.value
  const startTime = joinDateTime(draft.start_date, draft.start_clock)
  const endTime = joinDateTime(draft.end_date, draft.end_clock)
  const hasReminderPart = Boolean(draft.reminder_date || draft.reminder_clock)
  const reminderTime = joinDateTime(draft.reminder_date, draft.reminder_clock)
  if (!draft.title.trim() || !draft.place_name.trim() || !startTime || !endTime) {
    itineraryFormError.value = '请填写完整的日程名称、地点和起止日期、小时、分钟。'
    return
  }
  if (hasReminderPart && !reminderTime) {
    itineraryFormError.value = '提醒日期、小时和分钟需要同时选择。'
    return
  }
  if (draft.itinerary_type === 'transit' && !reminderTime) {
    itineraryFormError.value = '交通日程必须设置提醒时间。'
    return
  }
  const start = new Date(isoOrNull(startTime)!)
  const end = new Date(isoOrNull(endTime)!)
  if (end <= start) {
    itineraryFormError.value = '结束时间必须晚于开始时间；跨夜行程请把结束日期设为下一天。'
    return
  }
  const reminder = reminderTime ? new Date(isoOrNull(reminderTime)!) : null
  if (reminder && reminder > start) {
    itineraryFormError.value = '提醒时间不能晚于当前行程的开始时间。'
    return
  }
  if (!dateWithinCurrentTrip(startTime) || !dateWithinCurrentTrip(endTime)) {
    itineraryFormError.value = '日程起止时间必须位于当前计划的开始与结束日期内。'
    return
  }
  if (reminderTime && !dateWithinCurrentTrip(reminderTime)) {
    itineraryFormError.value = '提醒时间必须位于当前计划的开始与结束日期内。'
    return
  }
  error.value = ''
  itineraryFormError.value = ''
  try {
    const payload = {
      title: draft.title.trim(),
      place_name: draft.place_name.trim(),
      start_time: isoOrNull(startTime)!,
      end_time: isoOrNull(endTime)!,
      itinerary_type: draft.itinerary_type,
      reminder_time: isoOrNull(reminderTime),
      status: draft.status,
    }
    if (itineraryEditingId.value) await api.updateItinerary(itineraryEditingId.value, payload)
    else await api.createItinerary({ trip_id: tripId.value, ...payload })
    itineraryDialogOpen.value = false
    resetItinerary()
    itineraries.value = await api.listItineraries(tripId.value)
    selectedItineraryDate.value = draft.start_date
  } catch (cause) {
    itineraryFormError.value = errorMessage(cause, '日程保存失败。')
  }
}

function requestDelete(kind: DeleteTarget['kind'], id: number, label: string) {
  error.value = ''
  deleteTarget.value = { kind, id, label }
}

async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  loading.value = true
  error.value = ''
  try {
    if (target.kind === 'memo') {
      await api.deleteMemo(target.id)
      memos.value = memos.value.filter((item) => item.memo_id !== target.id)
      if (memoEditingId.value === target.id) closeMemoDialog()
    } else if (target.kind === 'itinerary') {
      await api.deleteItinerary(target.id)
      itineraries.value = itineraries.value.filter((item) => item.itinerary_id !== target.id)
      if (itineraryEditingId.value === target.id) closeItineraryDialog()
    } else {
      await api.deleteTrip(target.id)
      trips.value = trips.value.filter((item) => item.id !== target.id)
      tripId.value = trips.value[0]?.id || null
      if (!tripId.value) {
        memos.value = []
        itineraries.value = []
        advice.value = []
        messages.value = [{ ...welcomeMessage }]
      }
    }
    deleteTarget.value = null
  } catch (cause) {
    error.value = errorMessage(cause, '删除失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function automaticNotice(item: Advice) {
  return stripThink(item.reason_text || item.advice_text)
}

function openAdjustment() {
  adjustmentError.value = ''
  if (pendingManualAdvice.value) {
    adjustment.value = showAdjustmentCandidate(
      openManualAdjustment(),
      pendingManualAdvice.value.advice_id,
    )
    hydrateAdjustmentScope(pendingManualAdvice.value)
    return
  }
  adjustment.value = openManualAdjustment()
}

async function closeAdjustment() {
  if (loading.value) return
  if (adjustment.value.mode === 'automatic' && adjustment.value.sourceAdviceId) {
    promptedAutomaticAdviceId.value = adjustment.value.sourceAdviceId
    await markAdviceNotificationRead(adjustment.value.sourceAdviceId)
  }
  adjustment.value = closedAdjustment()
  adjustmentError.value = ''
}

function openAutomaticAdvice(item: Advice) {
  const root = automaticRootForAdvice(item) || item
  let next = openAutomaticAdjustment(
    root.advice_id,
    automaticNotice(root),
    automaticConflictIds(root),
  )
  const candidate = latestAutomaticCandidate(root)
  if (candidate) {
    next = showAdjustmentCandidate(next, candidate.advice_id)
  }
  adjustment.value = next
  hydrateAdjustmentScope(candidate || root)
  promptedAutomaticAdviceId.value = root.advice_id
  adjustmentError.value = ''
}

async function openNotificationAdjustment(item: Notification) {
  const row = notificationAdvice(item)
  if (!row) return
  if (!item.read_at) await markRead(item)
  reminderDialogOpen.value = false
  openAutomaticAdvice(row)
}

function continueAutomaticAdjustment() {
  adjustment.value = acceptAutomaticAdjustment(adjustment.value)
  adjustmentError.value = ''
}

async function markAdviceNotificationRead(adviceId: number) {
  const notification = notifications.value.find((item) => (
    item.advice_id === adviceId && !item.read_at
  ))
  if (notification) await markRead(notification)
}

async function resolveAutomaticAdjustment(action: 'keep_original' | 'cancel_original') {
  const adviceId = activeCandidate.value?.advice_id || adjustment.value.sourceAdviceId
  if (!adviceId) return
  loading.value = true
  adjustmentOperation.value = action === 'keep_original'
    ? '正在保留原行程…'
    : '正在取消原行程…'
  adjustmentError.value = ''
  try {
    await api.actOnAdvice(adviceId, action)
    if (adjustment.value.sourceAdviceId) {
      await markAdviceNotificationRead(adjustment.value.sourceAdviceId)
    }
    adjustment.value = closedAdjustment()
    if (tripId.value) {
      [advice.value, itineraries.value] = await Promise.all([
        api.listAdvice(tripId.value),
        api.listItineraries(tripId.value),
      ])
      await loadNotifications()
    }
  } catch (cause) {
    adjustmentError.value = errorMessage(cause, '暂时无法处理这条自动变化。')
  } finally {
    adjustmentOperation.value = ''
    loading.value = false
  }
}

async function submitAdjustmentRequest() {
  if (!tripId.value) return
  const requirement = adjustment.value.requirement.trim()
  if (adjustment.value.mode === 'manual' && !requirement) return
  loading.value = true
  adjustmentOperation.value = 'Hikari 正在生成候选方案，请稍候…'
  adjustmentError.value = ''
  try {
    let generated: Advice
    if (adjustment.value.mode === 'automatic') {
      if (!adjustment.value.sourceAdviceId) return
      generated = await api.actOnAdvice(
        adjustment.value.sourceAdviceId,
        'accept',
        adjustment.value.supplement.trim(),
        adjustment.value.selectedItineraryIds,
      )
      await markAdviceNotificationRead(adjustment.value.sourceAdviceId)
    } else {
      generated = await api.generateAdvice({
        trip_id: tripId.value,
        reason: requirement,
        selected_itinerary_ids: adjustment.value.selectedItineraryIds,
        ...locationPayload(),
      })
    }
    advice.value = await api.listAdvice(tripId.value)
    adjustment.value = showAdjustmentCandidate(adjustment.value, generated.advice_id)
  } catch (cause) {
    adjustmentError.value = errorMessage(cause, '候选方案未通过审核，请修改要求后重试。')
  } finally {
    adjustmentOperation.value = ''
    loading.value = false
  }
}

async function acceptCandidate() {
  const item = activeCandidate.value
  if (!item) return
  loading.value = true
  adjustmentOperation.value = '正在采纳方案并更新实时日程…'
  adjustmentError.value = ''
  try {
    await api.actOnAdvice(item.advice_id, 'accept')
    advice.value = await api.listAdvice(item.trip_id)
    itineraries.value = await api.listItineraries(item.trip_id)
    await loadNotifications()
    adjustment.value = closedAdjustment()
  } catch (cause) {
    adjustmentError.value = errorMessage(cause, '暂时无法采纳这个方案。')
  } finally {
    adjustmentOperation.value = ''
    loading.value = false
  }
}

async function rejectCandidate() {
  const item = activeCandidate.value
  if (!item) return
  loading.value = true
  adjustmentOperation.value = '正在放弃候选方案…'
  adjustmentError.value = ''
  try {
    await api.actOnAdvice(item.advice_id, 'reject')
    advice.value = await api.listAdvice(item.trip_id)
    adjustment.value = closedAdjustment()
  } catch (cause) {
    adjustmentError.value = errorMessage(cause, '暂时无法放弃这个方案。')
  } finally {
    adjustmentOperation.value = ''
    loading.value = false
  }
}

async function reviseCandidate() {
  const item = activeCandidate.value
  const revision = adjustment.value.revision.trim()
  if (!item || !revision) return
  loading.value = true
  adjustmentOperation.value = 'Hikari 正在根据新要求重新生成…'
  adjustmentError.value = ''
  try {
    const generated = await api.actOnAdvice(
      item.advice_id,
      'revise',
      revision,
      adjustment.value.selectedItineraryIds,
    )
    advice.value = await api.listAdvice(item.trip_id)
    adjustment.value = showAdjustmentCandidate(adjustment.value, generated.advice_id)
  } catch (cause) {
    adjustmentError.value = errorMessage(cause, '修改后的方案未通过审核，请调整要求后重试。')
  } finally {
    adjustmentOperation.value = ''
    loading.value = false
  }
}

async function markRead(item: Notification) {
  try {
    const updated = await api.markNotificationRead(item.notification_id)
    notifications.value = notifications.value.map((row) => row.notification_id === updated.notification_id ? updated : row)
  } catch (cause) {
    reminderError.value = errorMessage(cause, '标记通知失败。')
  }
}

async function openReminderInbox() {
  reminderDialogOpen.value = true
  reminderError.value = ''
  try {
    await loadNotifications()
  } catch (cause) {
    reminderError.value = errorMessage(cause, '读取提醒失败。')
  }
}

async function markAllNotificationsRead() {
  const unread = currentTripNotifications.value.filter((item) => !item.read_at)
  if (!unread.length) return
  notificationBusy.value = true
  reminderError.value = ''
  try {
    const updated = await Promise.all(unread.map((item) => api.markNotificationRead(item.notification_id)))
    const updatedById = new Map(updated.map((item) => [item.notification_id, item]))
    notifications.value = notifications.value.map((item) => updatedById.get(item.notification_id) || item)
  } catch (cause) {
    reminderError.value = errorMessage(cause, '批量标记提醒失败。')
    await loadNotifications().catch(() => undefined)
  } finally {
    notificationBusy.value = false
  }
}

function useBrowserLocation() {
  return new Promise<{ latitude: number; longitude: number }>((resolve, reject) => {
    if (!globalThis.navigator.geolocation) {
      reject(new Error('当前浏览器不支持定位。'))
      return
    }
    globalThis.navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      () => reject(new Error('无法获取浏览器定位，请检查定位权限。')),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 },
    )
  })
}

async function loadSavedLocation() {
  const getter = (api as { getLocation?: () => Promise<Location> }).getLocation
  if (typeof getter !== 'function') return
  try { location.value = await getter() } catch (cause) {
    if (!(cause instanceof ApiError && cause.status === 404)) throw cause
  }
}

async function refreshAll() {
  if (locationRefreshing.value) return
  locationRefreshing.value = true
  error.value = ''
  let locationError = ''
  try {
    try {
      const coordinates = await useBrowserLocation()
      browserCoordinates.value = { ...browserCoordinates.value, ...coordinates }
      location.value = await api.updateLocation(coordinates)
    } catch (cause) {
      locationError = errorMessage(cause, '定位刷新失败，其他数据已继续刷新。')
    }
    await loadTrips(true)
    if (tripId.value) await loadWorkspace()
    if (locationError) error.value = `${locationError} 其他数据已完成刷新。`
  } catch (cause) {
    error.value = errorMessage(cause, '刷新失败，请稍后重试。')
  } finally {
    locationRefreshing.value = false
  }
}

function adviceResult(result: string) {
  return ({ pending: '待处理', accepted: '已采纳', rejected: '已忽略', revising: '修改中', kept: '已保留原行程', cancelled_original: '已取消原行程', superseded: '已被新版本替代', delivered: '已送达', not_required: '无需处理' } as Record<string, string>)[result] || result
}

function featuredTripMarker(state: TripLifecycle | null) {
  return ({ upcoming: 'UPCOMING · 尚未开始', ongoing: 'TRIP · 计划进行中', completed: 'ARCHIVE · 已结束', cancelled: 'CANCELLED · 已取消' } as Record<string, string>)[state || ''] || 'TRIP STATUS'
}

function featuredTripSummary(state: TripLifecycle | null) {
  if (state === 'ongoing') {
    if (ongoingItinerary.value) return `正在进行：${ongoingItinerary.value.title}`
    if (nextItinerary.value) return `下一项：${nextItinerary.value.title}`
    return '当前暂无执行中的日程'
  }
  return state === 'upcoming' ? '计划尚未开始' : state === 'completed' ? '查看已结束日程' : state === 'cancelled' ? '查看取消记录' : ''
}

function focusFeaturedTrip() {
  if (featuredTrip.value) tripId.value = featuredTrip.value.id
}

function shortTripDate(value: string) {
  return value.slice(5).replace('-', '.')
}

function adviceType(type: string) {
  return ({ replan: '调整方案', itinerary_replan: '突发变化', proactive_recommendation: '主动建议', itinerary_check: '自动检查' } as Record<string, string>)[type] || type
}

function notificationType(type: string) {
  return ({ memo: '备忘提醒', memo_reminder: '备忘提醒', itinerary_reminder: '日程提醒', initial_start: '出发提醒', next_itinerary: '下一行程', itinerary_replan: '行程变化', agent_audit_failed: '自动处理未通过审核' } as Record<string, string>)[type] || type
}

function itineraryState(item: Itinerary) {
  return itineraryLifecycle(item, lifecycleClock.value)
}

let notificationTimer: number | undefined
let lifecycleTimer: number | undefined
watch(tripId, () => {
  workspaceRequestId += 1
  memos.value = []
  itineraries.value = []
  advice.value = []
  resetMemo()
  resetItinerary()
  memoDialogOpen.value = false
  itineraryDialogOpen.value = false
  deleteTarget.value = null
  adjustment.value = closedAdjustment()
  adjustmentError.value = ''
  promptedAutomaticAdviceId.value = null
  selectedItineraryDate.value = preferredItineraryDate(itineraryDates.value)
  messages.value = [{ ...welcomeMessage }]
  if (tripId.value) void loadWorkspace()
})
watch([pendingAutomaticAdvice, () => adjustment.value.open], ([item, modalOpen]) => {
  const linkedNotification = item
    ? notifications.value.find((notification) => notification.advice_id === item.advice_id)
    : undefined
  if (
    !item
    || modalOpen
    || promptedAutomaticAdviceId.value === item.advice_id
    || Boolean(linkedNotification?.read_at)
  ) return
  openAutomaticAdvice(item)
})
onMounted(async () => {
  await Promise.all([loadTrips(), loadSavedLocation()])
  notificationTimer = globalThis.setInterval(() => { void loadNotifications() }, 30_000)
  lifecycleTimer = globalThis.setInterval(() => { lifecycleClock.value = new Date() }, 30_000)
})
onUnmounted(() => {
  globalThis.clearInterval(notificationTimer)
  globalThis.clearInterval(lifecycleTimer)
})
</script>

<template>
  <div class="page companion-page">
    <section
      class="active-trip-section"
      aria-label="旅行计划状态"
    >
      <button
        v-if="featuredTrip"
        :class="['active-trip-card', `state-${featuredTripState}`]"
        type="button"
        @click="focusFeaturedTrip"
      >
        <span class="active-trip-marker"><i />{{ featuredTripMarker(featuredTripState) }}</span>
        <span class="active-trip-main">
          <small>{{ featuredTrip.title }}</small>
          <template v-if="featuredTrip.id === currentTrip?.id && ongoingItinerary">
            <strong>{{ ongoingItinerary.title }}</strong>
            <span>{{ ongoingItinerary.place_name }} · {{ formatDate(ongoingItinerary.start_time) }} — {{ formatDate(ongoingItinerary.end_time) }}</span>
          </template>
          <template v-else>
            <strong>{{ featuredTrip.origin_city }} <i>→</i> {{ featuredTrip.destination_city }}</strong>
            <span>{{ shortTripDate(featuredTrip.start_date) }} — {{ shortTripDate(featuredTrip.end_date) }}</span>
          </template>
        </span>
        <span class="active-trip-side"><b>{{ featuredTripState ? tripLifecycleLabel[featuredTripState] : '' }}</b><span>{{ currentTrip?.id === featuredTrip.id ? featuredTripSummary(featuredTripState) : '进入计划' }}</span></span>
      </button>
      <div
        v-else
        class="active-trip-empty"
      >
        <span class="active-trip-marker idle"><i />TRIP STATUS</span>
        <div><b>目前还没有旅行计划</b><small>创建计划后，这里会按时间显示待出发、进行中、已结束或已取消。</small></div>
      </div>
    </section>
    <p
      v-if="error"
      class="error"
    >
      {{ error }}<button @click="error = ''">
        ×
      </button>
    </p>

    <section class="workspace-bar">
      <label>当前行程<select v-model="tripId"><option :value="null">请选择行程</option><option
        v-for="trip in trips"
        :key="trip.id"
        :value="trip.id"
      >{{ trip.origin_city }} → {{ trip.destination_city }}旅行</option></select></label>
      <div class="workspace-actions">
        <button
          class="notification-inbox-trigger"
          type="button"
          :class="{ 'has-unread': unreadCount > 0 }"
          @click="openReminderInbox"
        >
          <span
            class="mail-icon"
            aria-hidden="true"
          >✉</span><span>提醒</span><b
            v-if="unreadCount"
            class="unread-badge"
          >{{ unreadCount > 99 ? '99+' : unreadCount }}</b><small v-else>已读</small>
        </button><button
          class="secondary"
          :disabled="locationRefreshing"
          @click="refreshAll"
        >
          {{ locationRefreshing ? '定位并刷新中…' : '刷新' }}
        </button><button
          v-if="currentTrip"
          class="danger-button"
          @click="requestDelete('trip', currentTrip.id, currentTrip.title)"
        >
          删除当前计划
        </button>
      </div>
    </section>

    <section
      v-if="currentTrip"
      class="card trip-overview"
      aria-label="当前计划基本信息"
    >
      <div class="trip-overview-title">
        <p class="eyebrow">
          CURRENT PLAN
        </p><h2>{{ currentTrip.title }}</h2><span :class="`state-${currentTripState}`">{{ currentTripState ? tripLifecycleLabel[currentTripState] : '' }}</span>
      </div>
      <dl>
        <div><dt>路线</dt><dd>{{ currentTrip.origin_city }} → {{ currentTrip.destination_city }}</dd></div>
        <div><dt>计划日期</dt><dd>{{ currentTrip.start_date }} — {{ currentTrip.end_date }}</dd></div>
        <div><dt>时区</dt><dd>{{ currentTrip.timezone || 'Asia/Shanghai' }}</dd></div>
        <div><dt>当前日程</dt><dd>{{ ongoingItinerary ? `${ongoingItinerary.title} · ${ongoingItinerary.place_name}` : (nextItinerary ? `下一项：${nextItinerary.title}` : '暂无待执行日程') }}</dd></div>
      </dl>
    </section>

    <section
      class="card current-location-card"
      aria-label="当前地理位置"
    >
      <div class="location-heading">
        <p class="eyebrow">
          LIVE LOCATION
        </p><h2>当前地理位置</h2><small>点击“刷新”会重新请求浏览器定位，并同步刷新当前计划的日程、备忘、提醒与对话。</small>
      </div>
      <dl v-if="location">
        <div><dt>位置</dt><dd>{{ location.place_name || '已获取坐标，地址暂未解析' }}</dd></div>
        <div><dt>城市编码</dt><dd>{{ location.city_adcode || '待解析' }}</dd></div>
        <div><dt>{{ locationCoordinateLabel }}</dt><dd>{{ location.longitude.toFixed(6) }}, {{ location.latitude.toFixed(6) }}</dd></div>
        <div><dt>更新时间</dt><dd>{{ formatDate(location.updated_at) }}</dd></div>
      </dl>
      <p
        v-if="locationResolutionError"
        class="location-resolution-error"
      >
        {{ locationResolutionError }}。{{ locationResolutionHint }}
      </p>
      <p
        v-if="!location"
        class="location-empty"
      >
        尚未获取位置。点击右上方“刷新”并允许浏览器定位即可自动补全。
      </p>
    </section>

    <p
      v-if="workspaceLoading"
      class="loading-line"
    >
      正在同步旅途数据…
    </p>

    <div class="main-grid">
      <section class="card chat">
        <header>
          <div>
            <p class="eyebrow">
              CONVERSATION
            </p><h2>和 Hikari 对话</h2>
          </div>
        </header>
        <div
          class="messages"
          :aria-busy="chatLoading"
        >
          <div
            v-for="(item, index) in messages"
            :key="index"
            class="message-row"
            :class="item.role"
          >
            <span
              class="chat-avatar"
              :aria-label="item.role === 'agent' ? 'Hikari' : '我'"
            >{{ item.role === 'agent' ? 'H' : '我' }}</span>
            <div
              class="message"
              :class="item.role"
            >
              <div
                v-if="item.role === 'agent'"
                class="markdown-body"
                v-html="renderMarkdown(stripReferenceSection(item.text))"
              /><span v-else>{{ item.text }}</span>
              <nav
                v-if="item.role === 'agent' && extractReferenceSources(item.text).length"
                class="message-sources"
                aria-label="参考来源"
              >
                <span>参考来源</span>
                <a
                  v-for="source in extractReferenceSources(item.text)"
                  :key="source.url"
                  :href="source.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ source.title }}</a>
              </nav>
              <small
                v-if="item.role === 'agent' && item.auditStatus"
                :class="['audit-mark', item.auditStatus]"
              >审核 {{ item.auditStatus === 'pass' ? '通过' : '未通过' }}<i v-if="item.auditReason"> · {{ item.auditReason }}</i></small>
            </div>
          </div>
          <div
            v-if="chatLoading"
            class="message-row agent"
          >
            <span
              class="chat-avatar"
              aria-label="Hikari"
            >H</span>
            <div class="message agent typing">
              <i /><span>Hikari 正在思考并核对旅途信息…</span>
            </div>
          </div>
        </div>
        <form
          class="composer"
          @submit.prevent="send"
        >
          <input
            v-model="message"
            :disabled="chatLoading || !tripId"
            placeholder="问问 Hikari 当前安排、提醒或附近建议…"
          ><button :disabled="chatLoading || !tripId">
            {{ chatLoading ? '等待回复…' : '发送' }}
          </button>
        </form>
      </section>

      <aside class="side-stack">
        <section class="card advice-card">
          <header>
            <div>
              <p class="eyebrow">
                ADVICE
              </p><h2>调整建议</h2>
            </div>
          </header>
          <div class="advice-entry">
            <p>在弹窗内说明变化、查看候选日程并完成采纳或修改。</p>
            <button
              class="primary"
              :disabled="loading || !tripId"
              @click="openAdjustment"
            >
              {{ pendingManualAdvice ? '继续处理候选方案' : '调整行程' }}
            </button>
            <button
              v-if="pendingAutomaticAdvice"
              class="pending-change"
              type="button"
              @click="openAutomaticAdvice(pendingAutomaticAdvice)"
            >
              <span>有一条自动变化等待确认</span><b>进入处理 →</b>
            </button>
            <details
              v-if="legacyFailedAdvice"
              class="audit-failure-summary"
            >
              <summary>最近一次调整未生成成功</summary><p class="audit-failure-only">
                {{ legacyFailedAdvice.audit_reason || stripThink(legacyFailedAdvice.advice_text) }}
              </p>
            </details>
          </div>
        </section>
        <MemoPanel
          :memos="memos"
          :items="filteredMemos"
          :filter="memoFilter"
          :disabled="!tripId"
          :format-date="formatDate"
          @update:filter="memoFilter = $event"
          @create="openMemoDialog"
          @edit="editMemo"
          @remove="requestDelete('memo', $event.memo_id, $event.memo_text)"
        />
      </aside>
    </div>

    <div class="tool-grid">
      <section
        v-if="false"
        class="card tool"
      >
        <header>
          <div>
            <p class="eyebrow">
              MEMOS
            </p><h2>旅途备忘</h2>
          </div><div class="header-tools">
            <label>筛选<select v-model="memoFilter"><option value="all">全部</option><option value="pending">待提醒</option><option value="sent">已发送</option><option value="unscheduled">无定时</option></select></label><button
              class="header-action"
              :disabled="!tripId"
              @click="openMemoDialog"
            >
              添加备忘
            </button>
          </div>
        </header>
        <div
          v-for="item in filteredMemos"
          :key="item.memo_id"
          class="data-row"
        >
          <div><b>{{ item.memo_text }}</b><small>提醒：{{ formatDate(item.reminder_time) }}<i v-if="item.reminded_at"> · 已发送</i></small></div><div class="row-actions">
            <button
              class="quiet"
              @click="editMemo(item)"
            >
              编辑
            </button><button
              class="delete-button"
              @click="requestDelete('memo', item.memo_id, item.memo_text)"
            >
              删除
            </button>
          </div>
        </div>
        <p
          v-if="!filteredMemos.length"
          class="muted"
        >
          {{ memos.length ? '当前筛选下没有备忘。' : '暂无备忘。' }}
        </p>
      </section>

      <section class="card tool itinerary-tool">
        <header>
          <div>
            <p class="eyebrow">
              ITINERARY
            </p><h2>实时日程</h2>
          </div><div class="header-tools">
            <label>筛选<select v-model="itineraryFilter"><option value="all">全部</option><option value="upcoming">待开始</option><option value="ongoing">进行中</option><option value="change_pending">变更待确认</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></label><button
              class="header-action"
              :disabled="!tripId"
              @click="openItineraryDialog"
            >
              添加日程
            </button>
          </div>
        </header>
        <div
          v-if="itineraryDates.length"
          class="itinerary-day-bar"
          aria-label="选择日程日期"
        >
          <button
            v-for="date in itineraryDates"
            :key="date"
            type="button"
            :class="{ active: selectedItineraryDate === date }"
            @click="selectedItineraryDate = date"
          >
            {{ date.slice(5).replace('-', '月') }}日
          </button>
        </div>
        <div class="itinerary-list">
          <div
            v-for="item in displayedItineraries"
            :key="item.itinerary_id"
            class="data-row itinerary-row"
            :class="`state-${itineraryState(item)}`"
          >
            <div>
              <div class="tag-line">
                <span>{{ item.itinerary_type === 'transit' ? '交通' : '游玩' }}</span><i
                  class="itinerary-status"
                  :class="itineraryState(item)"
                >{{ itineraryLifecycleLabel[itineraryState(item)] }}</i><em v-if="item.is_initial">当日首项</em>
              </div><b>{{ item.title }} · {{ item.place_name }}</b><small>{{ formatDate(item.start_time) }} — {{ formatDate(item.end_time) }}<br>提醒：{{ formatDate(item.reminder_time) }}<i v-if="item.reminded_at"> · 已发送</i></small>
            </div><div class="row-actions">
              <button
                class="quiet"
                @click="editItinerary(item)"
              >
                编辑
              </button><button
                class="delete-button"
                @click="requestDelete('itinerary', item.itinerary_id, item.title)"
              >
                删除
              </button>
            </div>
          </div>
          <p
            v-if="!displayedItineraries.length"
            class="muted"
          >
            {{ itineraries.length ? '当天没有符合条件的日程。' : '暂无实时日程。' }}
          </p>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <div
        v-if="adjustment.open"
        class="adjustment-overlay"
        role="presentation"
      >
        <section
          class="adjustment-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="adjustment-title"
        >
          <header class="dialog-header">
            <div>
              <p class="eyebrow">
                ITINERARY ADJUSTMENT
              </p><h2 id="adjustment-title">
                {{ adjustment.mode === 'automatic' ? '处理自动变化' : '调整行程' }}
              </h2>
            </div>
            <button
              class="dialog-close"
              :disabled="loading"
              aria-label="关闭调整弹窗"
              @click="closeAdjustment"
            >
              ×
            </button>
          </header>

          <div class="dialog-body">
            <p
              v-if="adjustmentError"
              class="audit-failure-only"
            >
              {{ adjustmentError }}
            </p>
            <div
              v-if="loading && adjustmentOperation"
              class="adjustment-progress"
              role="status"
              aria-live="polite"
            >
              <span /><div><b>{{ adjustmentOperation }}</b><small>请求已经发送，请不要重复点击或关闭页面。</small></div>
            </div>

            <template v-if="adjustment.stage === 'auto-confirm'">
              <div class="system-change">
                <span>系统自动提示</span>
                <div
                  class="markdown-body compact"
                  v-html="renderMarkdown(adjustment.systemNotice)"
                />
              </div>
              <p class="dialog-hint">
                是否根据这项变化重新生成一份待确认的行程方案？
              </p>
              <div class="dialog-actions automatic-resolution-actions">
                <button
                  class="danger-soft"
                  :disabled="loading"
                  @click="resolveAutomaticAdjustment('cancel_original')"
                >
                  取消原行程
                </button>
                <button
                  class="quiet"
                  :disabled="loading"
                  @click="resolveAutomaticAdjustment('keep_original')"
                >
                  保留原行程
                </button>
                <button
                  class="primary"
                  :disabled="loading"
                  @click="continueAutomaticAdjustment"
                >
                  同意更改
                </button>
              </div>
            </template>

            <template v-else-if="adjustment.stage === 'request'">
              <div
                v-if="adjustment.mode === 'automatic'"
                class="request-fields"
              >
                <label>系统自动提示<textarea
                  :value="adjustment.systemNotice"
                  readonly
                /></label>
                <label>用户补充<textarea
                  v-model="adjustment.supplement"
                  placeholder="可选：补充时间、地点或偏好"
                /></label>
              </div>
              <div
                v-else
                class="request-fields single-field"
              >
                <label>调整要求<textarea
                  v-model="adjustment.requirement"
                  autofocus
                  placeholder="例如：把明天下午的室外活动改成室内活动"
                /></label>
              </div>
              <section class="conflict-picker">
                <div class="conflict-picker-head">
                  <div><b>选择可能冲突的日程</b><small>只允许候选方案替换勾选项；未勾选日程必须保持不变。</small></div><span>{{ adjustment.selectedItineraryIds.length }} 项已选</span>
                </div>
                <div
                  v-if="adjustableItineraries.length"
                  class="conflict-list"
                >
                  <label
                    v-for="item in adjustableItineraries"
                    :key="item.itinerary_id"
                    class="conflict-choice"
                    :class="{ locked: adjustment.lockedItineraryIds.includes(item.itinerary_id) }"
                  >
                    <input
                      :checked="adjustment.selectedItineraryIds.includes(item.itinerary_id)"
                      :disabled="adjustment.lockedItineraryIds.includes(item.itinerary_id)"
                      type="checkbox"
                      @change="changeConflict(item.itinerary_id, $event)"
                    >
                    <span><b>{{ item.title }}</b><small>{{ item.place_name }} · {{ formatDate(item.start_time) }} — {{ formatDate(item.end_time) }} · {{ itineraryLifecycleLabel[itineraryState(item)] }}</small></span>
                    <em v-if="adjustment.lockedItineraryIds.includes(item.itinerary_id)">系统冲突 · 已锁定</em>
                  </label>
                </div>
                <p
                  v-else
                  class="conflict-empty"
                >
                  当前没有可调整的待执行日程。Hikari 只会在不影响现有安排的空档中推荐。
                </p>
                <p
                  v-if="!adjustment.selectedItineraryIds.length"
                  class="conflict-tip"
                >
                  未选择冲突项：Hikari 不会取消或改动任何已有日程，只能在可用空档中新增建议。
                </p>
              </section>
              <div class="dialog-actions">
                <button
                  class="quiet"
                  :disabled="loading"
                  @click="closeAdjustment"
                >
                  取消
                </button>
                <button
                  class="primary"
                  :disabled="loading || (adjustment.mode === 'manual' && !adjustment.requirement.trim())"
                  @click="submitAdjustmentRequest"
                >
                  {{ loading ? '正在生成…' : '生成候选方案' }}
                </button>
              </div>
            </template>

            <template v-else-if="adjustment.stage === 'candidate' && activeCandidate">
              <div class="candidate-heading">
                <div class="tag-line">
                  <span>{{ adviceType(activeCandidate.advice_type) }}</span><i>{{ adviceResult(activeCandidate.result) }}</i>
                </div>
                <small>方案尚未写入实时日程</small>
              </div>
              <p
                v-if="activeCandidate.audit_status === 'failed'"
                class="audit-failure-only"
              >
                {{ activeCandidate.audit_reason || stripThink(activeCandidate.advice_text) }}
              </p>
              <div
                v-else
                class="candidate-content markdown-body"
                v-html="renderMarkdown(stripThink(activeCandidate.advice_text))"
              />
              <div class="dialog-actions candidate-actions">
                <template v-if="adjustment.mode === 'automatic'">
                  <button
                    class="danger-soft"
                    :disabled="loading"
                    @click="resolveAutomaticAdjustment('cancel_original')"
                  >
                    取消原行程
                  </button>
                  <button
                    class="quiet"
                    :disabled="loading"
                    @click="resolveAutomaticAdjustment('keep_original')"
                  >
                    保留原行程
                  </button>
                </template>
                <button
                  v-else
                  class="quiet"
                  :disabled="loading"
                  @click="rejectCandidate"
                >
                  放弃方案
                </button>
                <button
                  class="quiet"
                  :disabled="loading"
                  @click="adjustment.stage = 'revision'"
                >
                  进一步修改
                </button>
                <button
                  class="primary"
                  :disabled="loading || activeCandidate.audit_status !== 'pass'"
                  @click="acceptCandidate"
                >
                  采纳并更新日程
                </button>
              </div>
            </template>

            <template v-else-if="adjustment.stage === 'revision' && activeCandidate">
              <div
                class="candidate-summary markdown-body compact"
                v-html="renderMarkdown(stripThink(activeCandidate.advice_text))"
              />
              <label class="revision-field">进一步修改要求<textarea
                v-model="adjustment.revision"
                autofocus
                placeholder="例如：不要安排博物馆，改为室内运动"
              /></label>
              <div class="dialog-actions">
                <button
                  class="quiet"
                  :disabled="loading"
                  @click="adjustment.stage = 'candidate'"
                >
                  返回方案
                </button>
                <button
                  class="primary"
                  :disabled="loading || !adjustment.revision.trim()"
                  @click="reviseCandidate"
                >
                  重新生成
                </button>
              </div>
            </template>
          </div>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="reminderDialogOpen"
        class="adjustment-overlay"
        role="presentation"
      >
        <section
          class="adjustment-dialog notification-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="notification-dialog-title"
        >
          <header class="dialog-header">
            <div>
              <p class="eyebrow">
                REMINDER INBOX
              </p><h2 id="notification-dialog-title">
                自动提醒
              </h2>
            </div>
            <button
              class="dialog-close"
              aria-label="关闭提醒弹窗"
              @click="reminderDialogOpen = false"
            >
              ×
            </button>
          </header>
          <div class="inbox-toolbar">
            <div><b>{{ currentTripNotifications.length }}</b> 条消息<span v-if="unreadCount"> · {{ unreadCount }} 条未读</span><span v-else> · 已全部读完</span></div>
            <div class="inbox-actions">
              <label><input
                v-model="unreadOnly"
                type="checkbox"
              >仅看未读</label>
              <button
                class="quiet"
                :disabled="notificationBusy || !unreadCount"
                @click="markAllNotificationsRead"
              >
                全部标为已读
              </button>
            </div>
          </div>
          <div class="inbox-list">
            <p
              v-if="reminderError"
              class="audit-failure-only"
            >
              {{ reminderError }}
            </p>
            <article
              v-for="item in visibleNotifications"
              :key="item.notification_id"
              class="mail-row"
              :class="{ unread: !item.read_at }"
            >
              <span
                class="mail-state-dot"
                aria-hidden="true"
              />
              <div class="mail-content">
                <div class="mail-meta">
                  <b>{{ notificationType(item.category) }}</b><time>{{ formatDate(item.created_at) }}</time>
                </div>
                <div
                  class="markdown-body compact"
                  v-html="renderMarkdown(stripThink(item.content))"
                />
              </div>
              <div class="mail-row-actions">
                <span
                  v-if="notificationAdviceStatus(item)"
                  class="advice-state"
                  :class="{ pending: notificationIsActionable(item) }"
                >{{ notificationAdviceStatus(item) }}</span>
                <button
                  v-if="notificationIsActionable(item)"
                  class="mail-advice-action"
                  @click="openNotificationAdjustment(item)"
                >
                  处理变化 →
                </button>
                <button
                  v-else-if="!item.read_at"
                  class="mail-read-action"
                  @click="markRead(item)"
                >
                  标为已读
                </button>
                <span
                  v-else
                  class="read-state"
                >已读</span>
              </div>
            </article>
            <div
              v-if="!visibleNotifications.length"
              class="inbox-empty"
            >
              <span>✓</span><b>{{ unreadOnly ? '没有未读提醒' : '还没有自动提醒' }}</b><small>{{ unreadOnly ? '所有消息都已处理。' : '系统产生提醒后会集中显示在这里。' }}</small>
            </div>
          </div>
        </section>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="memoDialogOpen"
        class="adjustment-overlay"
        role="presentation"
      >
        <section
          class="adjustment-dialog entry-dialog memo-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="memo-dialog-title"
        >
          <header class="dialog-header">
            <div>
              <p class="eyebrow">
                MEMO
              </p><h2 id="memo-dialog-title">
                {{ memoEditingId ? '编辑旅途备忘' : '新增旅途备忘' }}
              </h2>
            </div>
            <button
              class="dialog-close"
              aria-label="关闭备忘弹窗"
              @click="closeMemoDialog"
            >
              ×
            </button>
          </header>
          <form
            class="dialog-body modal-form"
            @submit.prevent="saveMemo"
          >
            <p
              v-if="error"
              class="audit-failure-only"
            >
              {{ error }}
            </p>
            <label>备忘内容<textarea
              v-model="memoDraft.memo_text"
              autofocus
              placeholder="例如：出发前带好证件和充电宝"
            /></label>
            <p
              v-if="memoFormError"
              class="form-error"
              role="alert"
            >
              {{ memoFormError }}
            </p>
            <fieldset class="date-time-field">
              <legend>提醒时间（可选）</legend><label class="date-picker-field">日期<DatePicker
                v-model="memoDraft.reminder_date"
                label="备忘提醒日期"
                :min="currentTrip?.start_date"
                :max="currentTrip?.end_date"
              /></label><label>时间<TimeSelect
                v-model="memoDraft.reminder_clock"
                label="备忘提醒"
              /></label>
            </fieldset>
            <div class="dialog-actions">
              <button
                class="quiet"
                type="button"
                @click="closeMemoDialog"
              >
                取消
              </button><button
                class="primary"
                :disabled="!memoDraft.memo_text.trim()"
              >
                {{ memoEditingId ? '保存修改' : '添加备忘' }}
              </button>
            </div>
          </form>
        </section>
      </div>

      <div
        v-if="itineraryDialogOpen"
        class="adjustment-overlay"
        role="presentation"
      >
        <section
          class="adjustment-dialog entry-dialog itinerary-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="itinerary-dialog-title"
        >
          <header class="dialog-header">
            <div>
              <p class="eyebrow">
                ITINERARY
              </p><h2 id="itinerary-dialog-title">
                {{ itineraryEditingId ? '编辑实时日程' : '新增实时日程' }}
              </h2>
            </div>
            <button
              class="dialog-close"
              aria-label="关闭日程弹窗"
              @click="closeItineraryDialog"
            >
              ×
            </button>
          </header>
          <form
            class="dialog-body modal-form"
            @submit.prevent="saveItinerary"
          >
            <p
              v-if="error"
              class="audit-failure-only"
            >
              {{ error }}
            </p>
            <div class="itinerary-form-grid">
              <label>事项名称<input
                v-model="itineraryDraft.title"
                autofocus
                placeholder="例如：参观博物馆"
              ></label>
              <label>地点<input
                v-model="itineraryDraft.place_name"
                placeholder="填写具体地点"
              ></label>
              <p
                v-if="itineraryFormError"
                class="form-error wide-field"
                role="alert"
              >
                {{ itineraryFormError }}
              </p>
              <fieldset class="date-time-field">
                <legend>开始时间</legend><label class="date-picker-field">日期<DatePicker
                  v-model="itineraryDraft.start_date"
                  label="日程开始日期"
                  :min="currentTrip?.start_date"
                  :max="currentTrip?.end_date"
                /></label><label>时间<TimeSelect
                  v-model="itineraryDraft.start_clock"
                  label="日程开始"
                /></label>
              </fieldset>
              <fieldset class="date-time-field">
                <legend>结束时间</legend><label class="date-picker-field">日期<DatePicker
                  v-model="itineraryDraft.end_date"
                  label="日程结束日期"
                  :min="currentTrip?.start_date"
                  :max="currentTrip?.end_date"
                /></label><label>时间<TimeSelect
                  v-model="itineraryDraft.end_clock"
                  label="日程结束"
                /></label>
              </fieldset>
              <label>日程类型<select v-model="itineraryDraft.itinerary_type"><option value="play">游玩</option><option value="transit">交通</option></select></label>
              <label>执行状态<select v-model="itineraryDraft.status"><option value="pending">待执行</option><option
                value="change_pending"
                disabled
              >变更待确认（系统）</option><option value="done">已完成</option><option value="cancelled">已取消</option></select></label>
              <fieldset class="date-time-field wide-field">
                <legend>提醒时间</legend><label class="date-picker-field">日期<DatePicker
                  v-model="itineraryDraft.reminder_date"
                  label="日程提醒日期"
                  :min="currentTrip?.start_date"
                  :max="currentTrip?.end_date"
                /></label><label>时间<TimeSelect
                  v-model="itineraryDraft.reminder_clock"
                  label="日程提醒"
                /></label><div class="time-shortcuts">
                  <button
                    class="quiet"
                    type="button"
                    @click="reminderSameAsStart"
                  >
                    同开始时间
                  </button><button
                    class="quiet"
                    type="button"
                    @click="clearItineraryReminder"
                  >
                    清空提醒
                  </button>
                </div><small>可以早于开始时间，例如 10:30 开始、09:30 提醒；不得晚于开始时间。</small>
              </fieldset>
            </div>
            <div class="dialog-actions">
              <button
                class="quiet"
                type="button"
                @click="closeItineraryDialog"
              >
                取消
              </button><button class="primary">
                {{ itineraryEditingId ? '保存修改' : '添加日程' }}
              </button>
            </div>
          </form>
        </section>
      </div>

      <div
        v-if="deleteTarget"
        class="adjustment-overlay"
        role="presentation"
      >
        <section
          class="adjustment-dialog confirm-dialog"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
        >
          <div class="dialog-body delete-confirmation">
            <span class="danger-symbol">!</span>
            <div>
              <p class="eyebrow">
                DELETE
              </p><h2 id="delete-dialog-title">
                {{ deleteTarget.kind === 'trip' ? '确认删除计划' : '确认删除' }}
              </h2>
            </div>
            <p
              v-if="error"
              class="audit-failure-only"
            >
              {{ error }}
            </p>
            <p>将删除“{{ deleteTarget.label }}”{{ deleteTarget.kind === 'trip' ? '及其日程、备忘和陪伴记录，此操作无法撤销。' : '，此操作无法撤销。' }}</p>
            <div class="dialog-actions split-actions">
              <button
                class="quiet"
                :disabled="loading"
                @click="deleteTarget = null"
              >
                取消
              </button><button
                class="danger-primary"
                :disabled="loading"
                @click="confirmDelete"
              >
                确认删除{{ deleteTarget.kind === 'trip' ? '计划' : '' }}
              </button>
            </div>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.companion-page{max-width:1180px;margin:auto;padding:42px 26px 70px}.hero{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:18px;padding:30px 35px;border:1px solid #dcebdd;border-radius:24px;background:radial-gradient(circle at 90% 35%,#d8f0df 0,transparent 24%),linear-gradient(115deg,#fff,#eef9f1)}.eyebrow{margin:0 0 7px;color:#579379;letter-spacing:.13em;font-size:11px;font-weight:700}.hero h1{margin:0;color:#254838;font:700 clamp(28px,4vw,40px)/1.3 'Noto Serif SC','Microsoft YaHei',serif}.hero p:last-child,.muted{color:#728178;font-size:13px;line-height:1.7}.hero-status{display:grid;min-width:130px;gap:4px;padding:16px;border-radius:18px;background:#fff9;color:#315745;text-align:center}.hero-status b{font-size:16px}.hero-status span{color:#7f9187;font-size:11px}.error{display:flex;justify-content:space-between;align-items:center;border:1px solid #f0d0cc;border-radius:10px;padding:10px 13px;background:#fff5f3;color:#ad4d4d;font-size:13px}.error button{border:0;background:transparent;color:inherit;cursor:pointer}.workspace-bar{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:17px}.workspace-bar label{display:flex;align-items:center;gap:10px;color:#52675c;font-size:13px;font-weight:700}.workspace-bar select{min-width:250px;border:1px solid #dce8df;border-radius:9px;padding:9px;background:#fff}.workspace-actions{display:flex;align-items:center;gap:8px}.notice-count{border-radius:999px;padding:5px 9px;background:#e5f4e9;color:#2d795a;font-size:11px;font-weight:700}.card{border:1px solid #e0e9e2;border-radius:18px;background:#fff;box-shadow:0 10px 28px rgba(39,91,66,.06)}.card header{display:flex;justify-content:space-between;align-items:center;padding:18px 20px;border-bottom:1px solid #edf2ee}.card h2{margin:0;color:#345344;font-size:17px}.card header small,.card header label{color:#849188;font-size:11px}.main-grid{display:grid;grid-template-columns:minmax(0,1fr) 365px;gap:18px}.chat{display:flex;min-height:560px;overflow:hidden;flex-direction:column}.messages{display:flex;min-height:360px;max-height:560px;flex:1;overflow:auto;flex-direction:column}.message{display:grid;max-width:88%;gap:6px;padding:11px 14px;border-radius:11px;font-size:14px;line-height:1.65}.message.agent{align-self:flex-start;background:#ecf7f0;color:#3e5e51}.message.user{align-self:flex-end;background:#2b8668;color:#fff}.message.typing{opacity:.7}.markdown-body{min-width:0;overflow-wrap:anywhere}.markdown-body :deep(> :first-child){margin-top:0}.markdown-body :deep(> :last-child){margin-bottom:0}.markdown-body :deep(p){margin:.45em 0}.markdown-body :deep(h1),.markdown-body :deep(h2),.markdown-body :deep(h3),.markdown-body :deep(h4){margin:.8em 0 .35em;color:#294f3d;line-height:1.35}.markdown-body :deep(h1){font-size:1.35em}.markdown-body :deep(h2){font-size:1.2em}.markdown-body :deep(h3){font-size:1.08em}.markdown-body :deep(ul),.markdown-body :deep(ol){margin:.45em 0;padding-left:1.5em}.markdown-body :deep(li){margin:.2em 0}.markdown-body :deep(strong){color:#244b39}.markdown-body :deep(blockquote){margin:.6em 0;padding:.2em .8em;border-left:3px solid #7eb397;background:#ffffff80}.markdown-body :deep(table){display:block;width:100%;overflow-x:auto;border-collapse:collapse;margin:.65em 0;background:#fff9}.markdown-body :deep(th),.markdown-body :deep(td){min-width:85px;border:1px solid #cfe1d5;padding:6px 8px;text-align:left;white-space:normal}.markdown-body :deep(th){background:#dff0e5;color:#2d5a44}.markdown-body :deep(code){border-radius:4px;padding:.1em .35em;background:#dcebe1;font-family:Consolas,monospace}.markdown-body.compact{font-size:13px;color:#52675d;line-height:1.65}.audit-mark{font-size:10px;font-style:normal}.audit-mark.pass{color:#4c8a6d}.audit-mark.failed{color:#b55b55}.audit-mark i{font-style:normal}.composer{display:flex;gap:8px;padding:12px;border-top:1px solid #edf2ee}.composer input,.advice-form input,.memo-form input,.schedule-form input,.schedule-form select,.revision-box input,.location-grid input{box-sizing:border-box;min-width:0;border:1px solid #dfe9e1;border-radius:8px;padding:9px;outline:none}.composer input{flex:1}.composer input:focus,.advice-form input:focus,.memo-form input:focus,.schedule-form input:focus,.location-grid input:focus{border-color:#72ae91;box-shadow:0 0 0 3px #eaf5ed}.composer button,.advice-form button,.memo-form button,.schedule-form button,.revision-box button,.primary{border:0;border-radius:8px;padding:9px 13px;background:#2f8063;color:#fff;font-weight:700;cursor:pointer}.composer button:disabled,.advice-form button:disabled{opacity:.55;cursor:wait}.secondary,.quiet,.icon{border:1px solid #dce8df;border-radius:8px;padding:8px 10px;background:#fff;color:#4f7563;cursor:pointer}.side-stack{display:grid;gap:18px;align-content:start}.advice-form{display:grid;gap:8px;padding:14px}.advice-item,.notification-item{padding:14px 16px;border-top:1px solid #edf2ee}.advice-item p,.notification-item p{margin:8px 0;color:#52675d;font-size:13px;line-height:1.65}.tag-line{display:flex;align-items:center;gap:6px}.tag-line span,.tag-line i,.tag-line em{border-radius:999px;padding:3px 7px;background:#eaf5ee;color:#4b8068;font-size:10px;font-style:normal}.tag-line i{background:#f3f5f2;color:#758279}.tag-line em.failed{background:#fff0ee;color:#b15c56}.audit-reason{display:block;margin-bottom:8px;color:#aa625d;line-height:1.5}.item-actions,.revision-box,.panel-actions,.schedule-actions{display:flex;gap:7px}.item-actions button{border:0;border-radius:7px;padding:7px 9px;background:#e6f3ea;color:#397458;cursor:pointer}.revision-box{margin-top:9px}.revision-box input{flex:1}.notifications-card header label{display:flex;align-items:center;gap:4px}.notification-item{display:flex;justify-content:space-between;gap:10px}.notification-item>div{min-width:0}.notification-item>div>span{color:#458064;font-size:10px;font-weight:700}.notification-item small{color:#929e97;font-size:10px}.notification-item button{align-self:center}.tool-grid{display:grid;grid-template-columns:1fr 1.3fr;gap:18px;margin-top:18px}.tool{padding-bottom:12px}.memo-form{display:grid;grid-template-columns:minmax(0,1fr) 190px auto auto;gap:8px;padding:14px}.schedule-form{display:grid;grid-template-columns:1fr 1fr;gap:9px;padding:14px}.schedule-form label{display:grid;gap:5px;color:#6f8077;font-size:11px}.schedule-actions{align-items:end}.data-row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 14px;padding:12px 2px;border-top:1px solid #edf2ee;color:#566b60;font-size:13px}.data-row>div:first-child{display:grid;gap:5px}.data-row small{color:#89958e;font-size:10px;line-height:1.55}.data-row small i{color:#4f876d;font-style:normal}.data-row .icon{margin-left:5px;border:0;color:#ae6262}.itinerary-row{align-items:start}.location-panel{margin-bottom:17px;padding:18px 20px}.location-panel h2{margin:0;color:#345344;font-size:17px}.location-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0}.panel-actions{justify-content:flex-end}.loading-line{color:#6e8679;font-size:12px;text-align:center}
.active-trip-section{margin-bottom:17px}.active-trip-card,.active-trip-empty{box-sizing:border-box;width:100%;min-height:112px;border:1px solid #bedfca;border-radius:20px;padding:20px 24px;background:linear-gradient(120deg,#1f7456 0%,#2f8d69 55%,#65a982 100%);box-shadow:0 14px 34px rgba(31,116,86,.18);color:#fff}.active-trip-card{display:grid;grid-template-columns:160px minmax(0,1fr) auto;align-items:center;gap:24px;font:inherit;text-align:left;cursor:pointer;transition:transform .18s ease,box-shadow .18s ease}.active-trip-card:hover{transform:translateY(-2px);box-shadow:0 18px 40px rgba(31,116,86,.24)}.active-trip-marker{display:flex;align-items:center;gap:8px;letter-spacing:.1em;font-size:10px;font-weight:800}.active-trip-marker i{width:8px;height:8px;border:3px solid #ffffff42;border-radius:50%;background:#b9ffd9;box-shadow:0 0 0 5px #ffffff12}.active-trip-main{display:grid;gap:5px}.active-trip-main small{color:#e2f3e8;font-size:11px}.active-trip-main strong{font-size:22px;line-height:1.3}.active-trip-main strong i{margin:0 7px;color:#bce6cc;font-style:normal}.active-trip-main>span{color:#d7eee0;font-size:11px}.active-trip-side{display:grid;justify-items:end;gap:12px}.active-trip-side b{border-radius:999px;padding:5px 10px;background:#fff;color:#267152;font-size:11px}.active-trip-side span{color:#eff9f2;font-size:12px;font-weight:700}.active-trip-empty{display:flex;align-items:center;gap:28px;border-color:#dce8df;background:#f7faf8;box-shadow:none;color:#536a5d}.active-trip-marker.idle{color:#728479}.active-trip-marker.idle i{border-color:#dfe9e2;background:#98aa9f;box-shadow:none}.active-trip-empty>div{display:grid;gap:5px}.active-trip-empty small{color:#8a9890}.notification-inbox-trigger{position:relative;display:flex;align-items:center;gap:7px;border:1px solid #cfe2d5;border-radius:10px;padding:8px 10px;background:#fff;color:#376650;font-weight:700;cursor:pointer}.notification-inbox-trigger.has-unread{border-color:#7fbaa0;background:#eff9f2;box-shadow:0 0 0 3px #e9f5ed}.notification-inbox-trigger small{color:#8d9992;font-size:10px;font-weight:500}.mail-icon{font-size:15px}.unread-badge{display:grid;min-width:19px;height:19px;box-sizing:border-box;place-items:center;border-radius:999px;padding:0 5px;background:#d85f55;color:#fff;font-size:10px}.notification-dialog{width:min(780px,100%)}.inbox-toolbar{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:14px 22px;border-bottom:1px solid #e8efea;background:#f8fbf9;color:#6d7d74;font-size:12px}.inbox-toolbar b{color:#2f684e;font-size:17px}.inbox-actions{display:flex;align-items:center;gap:12px}.inbox-actions label{display:flex;align-items:center;gap:6px;white-space:nowrap;cursor:pointer}.inbox-actions input{accent-color:#2f8063}.inbox-actions button:disabled{opacity:.45;cursor:not-allowed}.inbox-list{display:grid;overflow:auto;max-height:min(590px,calc(100vh - 190px));padding:0}.mail-row{display:grid;grid-template-columns:10px minmax(0,1fr) auto;align-items:start;gap:13px;padding:17px 22px;border-bottom:1px solid #edf2ee;background:#fff}.mail-row.unread{background:#f2faf5}.mail-state-dot{width:8px;height:8px;margin-top:7px;border-radius:50%;background:#c6d1ca}.mail-row.unread .mail-state-dot{background:#2f8b66;box-shadow:0 0 0 4px #dcefe4}.mail-content{display:grid;min-width:0;gap:7px}.mail-meta{display:flex;justify-content:space-between;gap:12px}.mail-meta b{color:#355a47;font-size:12px}.mail-row.unread .mail-meta b{color:#216c4d}.mail-meta time{color:#98a39d;font-size:10px}.mail-read-action{align-self:center;border:0;border-radius:8px;padding:7px 9px;background:#e3f2e8;color:#347256;font-size:11px;cursor:pointer}.read-state{align-self:center;color:#9aa49e;font-size:11px}.inbox-empty{display:grid;justify-items:center;gap:7px;padding:70px 20px;color:#536b5e}.inbox-empty>span{display:grid;width:42px;height:42px;place-items:center;border-radius:50%;background:#e6f3ea;color:#2e7b5c;font-size:19px}.inbox-empty small{color:#91a097}
.mail-row-actions{display:grid;justify-items:end;gap:7px;align-self:center}.advice-state{border-radius:999px;padding:4px 7px;background:#edf1ee;color:#68766e;font-size:10px}.advice-state.pending{background:#fff2d2;color:#826324}.mail-advice-action{border:0;border-radius:8px;padding:7px 9px;background:#2f8063;color:#fff;font-size:11px;font-weight:700;cursor:pointer}
.advice-entry{display:grid;gap:10px;padding:16px}.advice-entry>p{margin:0;color:#728178;font-size:13px;line-height:1.65}.advice-entry .primary{justify-self:start}.pending-change{display:flex;justify-content:space-between;align-items:center;gap:12px;border:0;border-radius:12px;padding:9px 11px;background:#fff5dc;color:#806028;font-size:11px;text-align:left;cursor:pointer}.pending-change b{white-space:nowrap;color:#6f5120}.audit-failure-only{margin:0;border:1px solid #f1ceca;border-radius:9px;padding:10px 12px;background:#fff3f1!important;color:#b84f49!important;font-size:13px;line-height:1.65}.adjustment-overlay{position:fixed;z-index:1000;inset:0;display:grid;place-items:center;padding:22px;background:rgba(24,48,37,.48);backdrop-filter:blur(3px)}.adjustment-dialog{display:flex;width:min(720px,100%);max-height:min(760px,calc(100vh - 44px));overflow:hidden;flex-direction:column;border:1px solid #dce9df;border-radius:20px;background:#fff;box-shadow:0 24px 70px rgba(19,52,37,.24)}.dialog-header{display:flex;justify-content:space-between;align-items:center;padding:20px 22px;border-bottom:1px solid #eaf0ec}.dialog-header h2{margin:0;color:#2f513f;font-size:20px}.dialog-close{width:34px;height:34px;border:1px solid #dce8df;border-radius:50%;background:#fff;color:#577064;font-size:21px;cursor:pointer}.dialog-close:disabled{opacity:.45;cursor:wait}.dialog-body{display:grid;gap:18px;overflow:auto;padding:22px}.system-change{border:1px solid #d8e9dd;border-radius:14px;padding:15px;background:#f2faf4}.system-change>span{display:inline-block;margin-bottom:8px;border-radius:999px;padding:4px 8px;background:#dff0e5;color:#347054;font-size:11px;font-weight:700}.dialog-hint{margin:0;color:#61736a;line-height:1.7}.dialog-actions{display:flex;justify-content:flex-end;gap:9px;padding-top:4px}.dialog-actions button{min-width:96px}.automatic-resolution-actions{flex-wrap:wrap}.danger-soft{border:1px solid #efc7c2;border-radius:8px;padding:8px 10px;background:#fff5f3;color:#a9514b;cursor:pointer}.request-fields{display:grid;grid-template-columns:1fr 1fr;gap:14px}.request-fields.single-field{grid-template-columns:1fr}.request-fields label,.revision-field{display:grid;gap:7px;color:#486556;font-size:12px;font-weight:700}.request-fields textarea,.revision-field textarea{box-sizing:border-box;min-height:120px;resize:vertical;border:1px solid #dce8df;border-radius:10px;padding:11px;background:#fff;color:#344c40;font:inherit;line-height:1.6;outline:none}.request-fields textarea:focus,.revision-field textarea:focus{border-color:#72ae91;box-shadow:0 0 0 3px #eaf5ed}.request-fields textarea[readonly]{background:#f5f7f5;color:#627269}.candidate-heading{display:flex;justify-content:space-between;align-items:center;gap:12px}.candidate-heading small{color:#819087}.candidate-content,.candidate-summary{max-height:420px;overflow:auto;border:1px solid #e2ebe4;border-radius:12px;padding:16px;background:#fbfdfb;color:#41594d;line-height:1.7}.candidate-actions{flex-wrap:wrap}.revision-field textarea{margin-top:7px}
.adjustment-progress{display:flex;align-items:center;gap:12px;border:1px solid #cce4d5;border-radius:12px;padding:12px 14px;background:#eff9f2;color:#315e49}.adjustment-progress>span{width:18px;height:18px;flex:0 0 auto;border:3px solid #c4dfcf;border-top-color:#2f8063;border-radius:50%;animation:adjustment-spin .8s linear infinite}.adjustment-progress>div{display:grid;gap:3px}.adjustment-progress b{font-size:12px}.adjustment-progress small{color:#71857a;font-size:10px}@keyframes adjustment-spin{to{transform:rotate(360deg)}}.conflict-picker{display:grid;gap:10px;border:1px solid #dfe9e2;border-radius:13px;padding:14px;background:#fafcfb}.conflict-picker-head{display:flex;justify-content:space-between;align-items:start;gap:12px}.conflict-picker-head>div{display:grid;gap:4px}.conflict-picker-head b{color:#355b48;font-size:13px}.conflict-picker-head small{color:#829087;font-size:10px;font-weight:400}.conflict-picker-head>span{white-space:nowrap;border-radius:999px;padding:4px 8px;background:#e5f3e9;color:#397357;font-size:10px;font-weight:700}.conflict-list{display:grid;max-height:230px;overflow:auto;border:1px solid #e7eee9;border-radius:10px;background:#fff}.conflict-choice{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:10px;padding:11px 12px;border-bottom:1px solid #edf2ee;cursor:pointer}.conflict-choice:last-child{border-bottom:0}.conflict-choice:hover{background:#f5faf6}.conflict-choice.locked{background:#eef7f1;cursor:default}.conflict-choice input{width:16px;height:16px;accent-color:#2f8063}.conflict-choice>span{display:grid;gap:3px}.conflict-choice>span b{color:#3f5e4f;font-size:12px}.conflict-choice>span small{color:#87938c;font-size:10px}.conflict-choice em{white-space:nowrap;border-radius:999px;padding:4px 7px;background:#dcefe3;color:#337052;font-size:9px;font-style:normal;font-weight:700}.conflict-empty,.conflict-tip{margin:0;border-radius:8px;padding:9px 10px;background:#f1f5f2;color:#748178;font-size:10px;line-height:1.55}.conflict-tip{background:#fff8e9;color:#846d3f}
.header-action{border:0;border-radius:8px;padding:8px 11px;background:#e6f3ea;color:#397458;font-weight:700;cursor:pointer}.header-action:disabled{opacity:.5;cursor:not-allowed}.row-actions{display:flex;gap:6px;align-items:center}.delete-button,.danger-button{border:1px solid #efcfcb;border-radius:8px;padding:8px 10px;background:#fff7f5;color:#b0524d;cursor:pointer}.danger-button{white-space:nowrap}.entry-dialog{width:min(620px,100%)}.modal-form label,.itinerary-form-grid label{display:grid;gap:7px;color:#486556;font-size:12px;font-weight:700}.modal-form input,.modal-form textarea,.modal-form select{box-sizing:border-box;width:100%;min-width:0;border:1px solid #dce8df;border-radius:10px;padding:10px;background:#fff;color:#344c40;font:inherit;outline:none}.modal-form textarea{min-height:120px;resize:vertical;line-height:1.6}.modal-form input:focus,.modal-form textarea:focus,.modal-form select:focus{border-color:#72ae91;box-shadow:0 0 0 3px #eaf5ed}.itinerary-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.itinerary-form-grid .wide-field{grid-column:1/-1}.itinerary-form-grid small{color:#849188;font-weight:400;line-height:1.5}.confirm-dialog{width:min(440px,100%)}.delete-confirmation{text-align:center}.delete-confirmation h2{margin:0;color:#733b38}.delete-confirmation>p{margin:0;color:#6d7771;line-height:1.7}.danger-symbol{display:grid;width:46px;height:46px;place-items:center;justify-self:center;border-radius:50%;background:#fff0ee;color:#b84f49;font-size:24px;font-weight:800}.danger-primary{border:0;border-radius:8px;padding:9px 13px;background:#b95750;color:#fff;font-weight:700;cursor:pointer}.danger-primary:disabled{opacity:.55}
.message-sources{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:3px;padding-top:8px;border-top:1px solid #d5e9dc}.message-sources span{color:#71877b;font-size:10px;font-weight:700;letter-spacing:.08em}.message-sources a{max-width:210px;overflow:hidden;border:1px solid #cfe2d6;border-radius:999px;padding:3px 8px;background:#fff;color:#327358;font-size:11px;text-decoration:none;text-overflow:ellipsis;white-space:nowrap}.message-sources a:hover{border-color:#75aa91;background:#f7fcf8}
.active-trip-card.state-upcoming{border-color:#c6dce7;background:linear-gradient(120deg,#476f82 0%,#5e8898 58%,#87aeba 100%)}.active-trip-card.state-completed{border-color:#d7ded9;background:linear-gradient(120deg,#68776f 0%,#7f8e86 58%,#a7b2ac 100%);box-shadow:0 12px 30px rgba(55,72,63,.14)}.active-trip-card.state-cancelled{border-color:#e5c9c6;background:linear-gradient(120deg,#875b58 0%,#a06f6a 58%,#bb918c 100%);box-shadow:0 12px 30px rgba(104,60,57,.14)}.itinerary-status.upcoming{background:#eef3f0;color:#687a70}.itinerary-status.ongoing{background:#dcf2e4;color:#277052}.itinerary-status.change_pending{background:#fff2ce;color:#876523}.itinerary-status.completed{background:#e7ece9;color:#647169}.itinerary-status.cancelled{background:#fff0ee;color:#ad5751}.itinerary-row.state-change_pending{background:#fffdf7}.itinerary-row.state-completed{background:#fafbfa}.itinerary-row.state-cancelled{opacity:.68}.itinerary-row.state-cancelled b{text-decoration:line-through}
.trip-overview{display:grid;grid-template-columns:minmax(210px,.8fr) 2fr;align-items:center;gap:24px;margin-bottom:18px;padding:18px 20px}.trip-overview-title{position:relative;min-width:0;padding-right:72px}.trip-overview-title h2{overflow:hidden;margin:0;color:#315342;font-size:18px;text-overflow:ellipsis;white-space:nowrap}.trip-overview-title>span{position:absolute;top:0;right:0;border-radius:999px;padding:4px 8px;background:#e5f3e9;color:#39755a;font-size:10px;font-weight:700}.trip-overview-title>span.state-upcoming{background:#eef4f7;color:#527586}.trip-overview-title>span.state-completed{background:#edf0ee;color:#69766f}.trip-overview-title>span.state-cancelled{background:#fff0ee;color:#a85a55}.trip-overview dl{display:grid;grid-template-columns:1fr 1.15fr .8fr 1.4fr;gap:10px;margin:0}.trip-overview dl>div{min-width:0;border-left:1px solid #e6ede8;padding-left:12px}.trip-overview dt{margin-bottom:5px;color:#8a9890;font-size:10px}.trip-overview dd{overflow:hidden;margin:0;color:#476052;font-size:12px;font-weight:700;text-overflow:ellipsis;white-space:nowrap}.message.typing{display:flex;align-items:center;gap:8px}.message.typing i{width:8px;height:8px;border-radius:50%;background:#4b9875;box-shadow:12px 0 #79b397,24px 0 #a9cdb9;animation:typing-pulse 1.1s infinite ease-in-out}.message.typing span{margin-left:24px}@keyframes typing-pulse{0%,100%{opacity:.35;transform:translateY(0)}50%{opacity:1;transform:translateY(-2px)}}
.current-location-card{display:grid;grid-template-columns:minmax(230px,.8fr) 2fr;align-items:center;gap:22px;margin-bottom:18px;padding:18px 20px;background:linear-gradient(120deg,#fff,#f4faf6)}.location-heading h2{margin:0;color:#315342;font-size:17px}.location-heading small{display:block;margin-top:5px;color:#839188;font-size:10px;line-height:1.55}.current-location-card dl{display:grid;grid-template-columns:1.4fr .7fr 1fr .9fr;gap:10px;margin:0}.current-location-card dl>div{min-width:0;border-left:1px solid #e3ece6;padding-left:12px}.current-location-card dt{margin-bottom:5px;color:#8a9890;font-size:10px}.current-location-card dd{overflow:hidden;margin:0;color:#456052;font-size:12px;font-weight:700;text-overflow:ellipsis;white-space:nowrap}.location-empty{margin:0;border:1px dashed #d3e4d8;border-radius:10px;padding:13px;color:#7a8b81;font-size:12px}
.location-resolution-error{grid-column:1/-1;margin:0;border:1px solid #f0d2b0;border-radius:10px;padding:10px 12px;background:#fff8ee;color:#8b6437;font-size:11px;line-height:1.55}
.audit-failure-summary{border-top:1px solid #edf2ee;padding-top:9px}.audit-failure-summary summary{color:#a05e59;font-size:11px;cursor:pointer}.audit-failure-summary .audit-failure-only{margin-top:8px}
.message-row{display:flex;align-items:flex-start;gap:9px;margin:10px 14px}.message-row.user{flex-direction:row-reverse}.message-row .message{margin:0}.chat-avatar{display:grid;width:32px;height:32px;box-sizing:border-box;flex:0 0 auto;place-items:center;border:1px solid #cce3d5;border-radius:11px;background:linear-gradient(145deg,#e8f6ed,#cfeadb);box-shadow:0 4px 12px rgba(39,91,66,.1);color:#246a4e;font-size:12px;font-weight:800}.message-row.user .chat-avatar{border-color:#2c8266;background:#2b8668;color:#fff}.header-tools{display:flex;align-items:center;gap:8px}.header-tools label{display:flex;align-items:center;gap:6px}.header-tools select{border:1px solid #dce8df;border-radius:8px;padding:7px 28px 7px 8px;background:#fff;color:#4f6d5e;font:inherit}.tool>.muted{margin:0;padding:22px;text-align:center}.date-time-field{display:grid;grid-template-columns:minmax(170px,.9fr) minmax(190px,1.1fr);gap:10px;min-width:0;margin:0;border:1px solid #dfe9e2;border-radius:12px;padding:12px;background:#f9fcfa}.date-time-field legend{padding:0 5px;color:#486556;font-size:12px;font-weight:700}.date-time-field label{display:grid;align-content:start;gap:6px;font-size:10px}.date-picker-field input{cursor:pointer}.date-time-field .time-shortcuts{display:flex;align-items:center;gap:7px}.date-time-field>small{grid-column:1/-1}.time-shortcuts .quiet{padding:7px 9px;font-size:11px}.form-error{margin:0;border:1px solid #f0c8c2;border-radius:10px;padding:9px 11px;background:#fff2ef;color:#aa5048;font-size:11px;line-height:1.5}
@media(max-width:920px){.main-grid,.tool-grid{grid-template-columns:1fr}.chat{min-height:480px}.side-stack{grid-template-columns:1fr}.location-grid{grid-template-columns:1fr 1fr}.active-trip-card{grid-template-columns:135px minmax(0,1fr) auto;gap:16px}.trip-overview,.current-location-card{grid-template-columns:1fr}.trip-overview dl,.current-location-card dl{grid-template-columns:1fr 1fr}}
@media(max-width:680px){.companion-page{padding:26px 16px 55px}.hero{display:block;padding:25px 22px}.hero-status{display:none}.active-trip-card{grid-template-columns:1fr;gap:13px;padding:19px}.active-trip-side{grid-template-columns:auto 1fr;align-items:center;justify-items:start}.active-trip-side span{justify-self:end}.active-trip-empty{align-items:flex-start;flex-direction:column;gap:15px;padding:19px}.workspace-bar,.workspace-bar label{align-items:stretch;flex-direction:column}.workspace-bar select{width:100%;min-width:0}.workspace-actions{display:grid;grid-template-columns:1fr 1fr}.notification-inbox-trigger{justify-content:center}.danger-button{grid-column:1/-1}.trip-overview{padding:16px}.trip-overview dl{grid-template-columns:1fr}.trip-overview dl>div{border-left:0;border-top:1px solid #edf2ee;padding:9px 0 0}.inbox-toolbar{align-items:flex-start;flex-direction:column}.inbox-actions{width:100%;justify-content:space-between}.mail-row{grid-template-columns:10px minmax(0,1fr);padding:15px}.mail-row-actions{grid-column:2;justify-items:start}.mail-meta{align-items:flex-start;flex-direction:column;gap:4px}.conflict-picker-head{align-items:stretch;flex-direction:column}.conflict-choice{grid-template-columns:auto minmax(0,1fr)}.conflict-choice em{grid-column:2;justify-self:start}.memo-form,.schedule-form,.location-grid,.request-fields,.itinerary-form-grid,.date-time-field{grid-template-columns:1fr}.itinerary-form-grid .wide-field{grid-column:auto}.date-time-field>small{grid-column:auto}.message{max-width:92%}.message-row{margin:9px 10px}.chat-avatar{width:29px;height:29px;border-radius:9px}.card header{padding:15px}.tool header{align-items:flex-start;gap:10px}.header-tools{align-items:stretch;flex-direction:column}.notification-item{align-items:flex-start}.schedule-actions{align-items:center}.adjustment-overlay{align-items:end;padding:0}.adjustment-dialog{width:100%;max-height:92vh;border-radius:20px 20px 0 0}.dialog-body{padding:18px}.dialog-actions button{min-width:0}.candidate-actions{display:grid;grid-template-columns:1fr 1fr}.candidate-actions .primary{grid-column:1/-1}.row-actions{align-items:stretch;flex-direction:column}}
.itinerary-dialog{width:min(880px,100%)}
@media(min-width:681px){.wide-field :deep(.date-picker-popover),.wide-field :deep(.time-picker-popover){top:auto;bottom:calc(100% + 8px)}}
</style>

<style scoped>

.main-grid {
  align-items: stretch;
}

.side-stack {
  min-height: 560px;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: stretch;
}

.tool-grid {
  grid-template-columns: minmax(0, 1fr);
}

.itinerary-tool {
  display: flex;
  height: 220px;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.itinerary-list {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.itinerary-list > .muted {
  display: grid;
  box-sizing: border-box;
  min-height: 100%;
  place-items: center;
  margin: 0;
  padding: 16px;
  text-align: center;
}

.itinerary-day-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding: 12px 20px;
  border-bottom: 1px solid #edf2ee;
}

.itinerary-day-bar button {
  flex: 0 0 auto;
  border: 1px solid #dce8df;
  border-radius: 999px;
  padding: 7px 12px;
  background: #fff;
  color: #60766a;
  font-size: 12px;
  cursor: pointer;
}

.itinerary-day-bar button.active {
  border-color: #2f8063;
  background: #2f8063;
  color: #fff;
  font-weight: 700;
}

.itinerary-day-bar .sync-plan-button {
  margin-left: auto;
  border-color: #b8d8c3;
  background: #eef8f1;
  color: #397458;
  font-weight: 700;
}

.itinerary-day-bar .sync-plan-button:disabled {
  cursor: wait;
  opacity: .65;
}

.plan-sync-message {
  margin: 10px 20px 0;
  color: #4c8066;
  font-size: 12px;
}

@media (max-width: 920px) {
  .side-stack {
    min-height: auto;
    grid-template-rows: auto;
  }

  .itinerary-day-bar {
    padding: 11px 14px;
  }
}
</style>
