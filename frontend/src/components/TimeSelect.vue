<script setup lang="ts">
/* global document, HTMLElement, Event, HTMLInputElement, PointerEvent, Node, KeyboardEvent */
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
}>(), {
  label: '时间',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const root = ref<HTMLElement | null>(null)
const hoursWheel = ref<HTMLElement | null>(null)
const minutesWheel = ref<HTMLElement | null>(null)
const open = ref(false)
const inputValue = ref(props.modelValue)
const inputError = ref('')
const draftHour = ref('00')
const draftMinute = ref('00')
const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const minutes = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'))

watch(() => props.modelValue, (value) => {
  inputValue.value = value
})

function normalizeClock(raw: string) {
  const value = raw.trim().replace('：', ':')
  const colon = /^(\d{1,2}):(\d{1,2})$/.exec(value)
  const compact = /^(\d{3,4})$/.exec(value)
  const hour = colon ? Number(colon[1]) : compact ? Number(compact[1]!.slice(0, -2)) : -1
  const minute = colon ? Number(colon[2]) : compact ? Number(compact[1]!.slice(-2)) : -1
  return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59
    ? `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
    : null
}

function updateInput(event: Event) {
  inputValue.value = (event.target as HTMLInputElement).value
  inputError.value = ''
}

function commitInput() {
  if (!inputValue.value.trim()) {
    emit('update:modelValue', '')
    inputError.value = ''
    return
  }
  const normalized = normalizeClock(inputValue.value)
  if (!normalized) {
    inputError.value = '请输入 00:00 至 23:59'
    return
  }
  inputValue.value = normalized
  inputError.value = ''
  emit('update:modelValue', normalized)
}

function togglePicker() {
  if (!open.value) {
    const normalized = normalizeClock(inputValue.value) || props.modelValue || '00:00'
    ;[draftHour.value, draftMinute.value] = normalized.split(':')
    open.value = true
    void nextTick(() => {
      centerWheel(hoursWheel.value, Number(draftHour.value))
      centerWheel(minutesWheel.value, Number(draftMinute.value))
    })
    return
  }
  open.value = false
}

function centerWheel(wheel: HTMLElement | null, index: number) {
  const item = wheel?.querySelector<HTMLElement>('button')
  if (!wheel || !item) return
  if (typeof wheel.scrollTo === 'function') {
    wheel.scrollTo({ top: item.offsetHeight * index, behavior: 'smooth' })
  }
}

function chooseWheel(kind: 'hour' | 'minute', value: string) {
  if (kind === 'hour') {
    draftHour.value = value
    centerWheel(hoursWheel.value, Number(value))
  } else {
    draftMinute.value = value
    centerWheel(minutesWheel.value, Number(value))
  }
}

function syncWheel(kind: 'hour' | 'minute', event: Event) {
  const wheel = event.currentTarget as HTMLElement
  const height = wheel.querySelector<HTMLElement>('button')?.offsetHeight || 40
  const values = kind === 'hour' ? hours : minutes
  const value = values[Math.min(values.length - 1, Math.max(0, Math.round(wheel.scrollTop / height)))]
  if (kind === 'hour') draftHour.value = value!
  else draftMinute.value = value!
}

function confirmPicker() {
  const value = `${draftHour.value}:${draftMinute.value}`
  inputValue.value = value
  inputError.value = ''
  emit('update:modelValue', value)
  open.value = false
}

function closeFromOutside(event: PointerEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}

function closeFromEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('pointerdown', closeFromOutside)
  document.addEventListener('keydown', closeFromEscape)
})
onUnmounted(() => {
  document.removeEventListener('pointerdown', closeFromOutside)
  document.removeEventListener('keydown', closeFromEscape)
})
</script>

<template>
  <div ref="root" class="time-select">
    <div class="time-input-shell" :class="{ invalid: inputError }">
      <input
        class="time-picker-input"
        :value="inputValue"
        inputmode="numeric"
        maxlength="5"
        placeholder="--:--"
        :aria-label="`${label}，可直接输入`"
        @input="updateInput"
        @blur="commitInput"
        @keydown.enter.prevent="commitInput"
      >
      <button class="time-picker-toggle" type="button" :aria-label="`滑动选择${label}`" :aria-expanded="open" @click="togglePicker">⌄</button>
    </div>
    <small v-if="inputError" class="time-input-error">{{ inputError }}</small>
    <div v-if="open" class="time-picker-popover" role="dialog" :aria-label="`${label}滑动选择器`">
      <div class="time-wheel-labels"><span>时</span><span>分</span></div>
      <div class="time-wheels">
        <div ref="hoursWheel" class="time-wheel time-wheel-hours" @scroll.passive="syncWheel('hour', $event)">
          <button v-for="hour in hours" :key="hour" type="button" :data-value="hour" :class="{ selected: draftHour === hour }" @click="chooseWheel('hour', hour)">{{ hour }}</button>
        </div>
        <div class="time-wheel-separator">:</div>
        <div ref="minutesWheel" class="time-wheel time-wheel-minutes" @scroll.passive="syncWheel('minute', $event)">
          <button v-for="minute in minutes" :key="minute" type="button" :data-value="minute" :class="{ selected: draftMinute === minute }" @click="chooseWheel('minute', minute)">{{ minute }}</button>
        </div>
      </div>
      <div class="time-picker-actions">
        <button type="button" @click="open = false">取消</button>
        <button class="time-picker-confirm" type="button" @click="confirmPicker">确定 {{ draftHour }}:{{ draftMinute }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-select{position:relative;min-width:0}.time-input-shell{display:grid;grid-template-columns:1fr 38px;overflow:hidden;border:1px solid #dce8df;border-radius:10px;background:#fff}.time-input-shell:focus-within{border-color:#72ae91;box-shadow:0 0 0 3px #eaf5ed}.time-input-shell.invalid{border-color:#d99088;box-shadow:0 0 0 3px #fff0ed}.time-picker-input{width:100%;min-width:0;border:0!important;padding:10px 12px!important;background:transparent!important;color:#345243!important;font-variant-numeric:tabular-nums;outline:0!important;box-shadow:none!important}.time-picker-input::placeholder{color:#8c9b93}.time-picker-toggle{border:0;border-left:1px solid #e5ece7;background:#f6faf7;color:#3d7a5e;font-size:18px}.time-input-error{display:block;margin-top:5px;color:#aa5048;font-size:10px}.time-picker-popover{position:absolute;z-index:42;top:calc(100% + 8px);right:0;width:250px;border:1px solid #d9e8de;border-radius:16px;padding:14px;background:#fff;box-shadow:0 20px 48px rgba(31,72,52,.18)}.time-wheel-labels{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin:0 13px 7px;color:#6c8075;font-size:10px;font-weight:800;text-align:center}.time-wheels{display:grid;grid-template-columns:1fr 18px 1fr;align-items:center}.time-wheel{height:176px;overflow-y:auto;border:1px solid #e2ebe5;border-radius:12px;padding:66px 5px;scroll-snap-type:y mandatory;scrollbar-width:thin;overscroll-behavior:contain;background:linear-gradient(#f4f8f5,transparent 38%,transparent 62%,#f4f8f5)}.time-wheel button{display:block;width:100%;height:40px;border:0;border-radius:9px;background:transparent;color:#97a39c;font-size:17px;font-variant-numeric:tabular-nums;scroll-snap-align:center}.time-wheel button:hover{background:#eff7f1;color:#41735c}.time-wheel button.selected{background:#e1f2e7;color:#226d4e;font-size:20px;font-weight:800}.time-wheel-separator{color:#5d7468;font-size:21px;font-weight:800;text-align:center}.time-picker-actions{display:flex;justify-content:flex-end;gap:7px;margin-top:12px}.time-picker-actions button{border:1px solid #dce8df;border-radius:8px;padding:7px 10px;background:#fff;color:#577064;font-size:11px}.time-picker-actions .time-picker-confirm{border-color:#277e61;background:#2b8868;color:#fff;font-weight:700}@media(max-width:680px){.time-picker-popover{position:fixed;top:auto;right:12px;bottom:12px;left:12px;width:auto;border-radius:20px;padding:18px}.time-wheel{height:220px;padding:88px 5px}.time-wheel button{height:44px;font-size:20px}.time-wheel button.selected{font-size:24px}.time-picker-actions button{min-height:42px;flex:1;font-size:13px}}
</style>
