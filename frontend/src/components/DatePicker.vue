<script setup lang="ts">
/* global document, HTMLElement, Event, HTMLSelectElement, PointerEvent, Node, KeyboardEvent */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
  min?: string
  max?: string
}>(), {
  label: '日期',
  min: '',
  max: '',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const root = ref<HTMLElement | null>(null)
const open = ref(false)
const now = new Date()
const viewYear = ref(now.getFullYear())
const viewMonth = ref(now.getMonth() + 1)
const weekdays = ['日', '一', '二', '三', '四', '五', '六']

function parseDate(value: string) {
  const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!matched) return null
  const [, year, month, day] = matched.map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCFullYear() === year
    && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day
    ? date
    : null
}

function dateText(date: Date) {
  return [
    date.getUTCFullYear(),
    String(date.getUTCMonth() + 1).padStart(2, '0'),
    String(date.getUTCDate()).padStart(2, '0'),
  ].join('-')
}

function moveViewTo(value: string) {
  const target = parseDate(value)
  if (!target) return
  viewYear.value = target.getUTCFullYear()
  viewMonth.value = target.getUTCMonth() + 1
}

watch(() => props.modelValue, (value) => moveViewTo(value), { immediate: true })

const minDate = computed(() => parseDate(props.min))
const maxDate = computed(() => parseDate(props.max))
const yearOptions = computed(() => {
  const start = minDate.value?.getUTCFullYear() ?? now.getFullYear() - 10
  const end = maxDate.value?.getUTCFullYear() ?? now.getFullYear() + 10
  return Array.from({ length: Math.max(1, end - start + 1) }, (_, index) => start + index)
})
const calendarDays = computed(() => {
  const first = new Date(Date.UTC(viewYear.value, viewMonth.value - 1, 1))
  const startDay = 1 - first.getUTCDay()
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(Date.UTC(viewYear.value, viewMonth.value - 1, startDay + index))
    const value = dateText(date)
    return {
      value,
      day: date.getUTCDate(),
      adjacent: date.getUTCMonth() + 1 !== viewMonth.value,
      disabled: Boolean(
        (minDate.value && date < minDate.value)
        || (maxDate.value && date > maxDate.value),
      ),
    }
  })
})

function canShow(year: number, month: number) {
  const first = new Date(Date.UTC(year, month - 1, 1))
  const last = new Date(Date.UTC(year, month, 0))
  return !(
    (minDate.value && last < minDate.value)
    || (maxDate.value && first > maxDate.value)
  )
}

const canPrevious = computed(() => {
  const date = new Date(Date.UTC(viewYear.value, viewMonth.value - 2, 1))
  return canShow(date.getUTCFullYear(), date.getUTCMonth() + 1)
})
const canNext = computed(() => {
  const date = new Date(Date.UTC(viewYear.value, viewMonth.value, 1))
  return canShow(date.getUTCFullYear(), date.getUTCMonth() + 1)
})

function toggle() {
  if (!open.value) {
    moveViewTo(props.modelValue || props.min || dateText(new Date(Date.UTC(
      now.getFullYear(), now.getMonth(), now.getDate(),
    ))))
  }
  open.value = !open.value
}

function changeMonth(offset: number) {
  const date = new Date(Date.UTC(viewYear.value, viewMonth.value - 1 + offset, 1))
  viewYear.value = date.getUTCFullYear()
  viewMonth.value = date.getUTCMonth() + 1
}

function selectDate(value: string, disabled: boolean) {
  if (disabled) return
  emit('update:modelValue', value)
  moveViewTo(value)
  open.value = false
}

function selectedValue(event: Event) {
  return Number((event.target as HTMLSelectElement).value)
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
  <div ref="root" class="date-picker">
    <button
      class="date-picker-trigger"
      type="button"
      :aria-label="label"
      :aria-expanded="open"
      @click="toggle"
    >
      <span :class="{ placeholder: !modelValue }">{{ modelValue || '请选择日期' }}</span>
      <i aria-hidden="true">▦</i>
    </button>
    <div v-if="open" class="date-picker-popover" role="dialog" :aria-label="`${label}选择器`">
      <div class="calendar-heading">
        <button type="button" aria-label="上个月" :disabled="!canPrevious" @click="changeMonth(-1)">‹</button>
        <div>
          <select aria-label="选择月份" :value="viewMonth" @change="viewMonth = selectedValue($event)">
            <option v-for="month in 12" :key="month" :value="month">{{ month }}月</option>
          </select>
          <select aria-label="选择年份" :value="viewYear" @change="viewYear = selectedValue($event)">
            <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}年</option>
          </select>
        </div>
        <button type="button" aria-label="下个月" :disabled="!canNext" @click="changeMonth(1)">›</button>
      </div>
      <div class="calendar-weekdays" aria-hidden="true">
        <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
      </div>
      <div class="calendar-grid">
        <button
          v-for="item in calendarDays"
          :key="item.value"
          type="button"
          :data-date="item.value"
          :disabled="item.disabled"
          :class="{ adjacent: item.adjacent, selected: item.value === modelValue }"
          @click="selectDate(item.value, item.disabled)"
        >{{ item.day }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.date-picker{position:relative;min-width:0}.date-picker-trigger{display:flex;width:100%;min-height:42px;align-items:center;justify-content:space-between;gap:10px;border:1px solid #dce8df;border-radius:10px;padding:10px 12px;background:#fff;color:#345243;font:inherit;text-align:left;outline:none}.date-picker-trigger:hover{border-color:#a9cfb9;background:#fbfefc}.date-picker-trigger:focus-visible{border-color:#72ae91;box-shadow:0 0 0 3px #eaf5ed}.date-picker-trigger .placeholder{color:#8c9b93;font-weight:500}.date-picker-trigger i{color:#438266;font-size:15px;font-style:normal}.date-picker-popover{position:absolute;z-index:40;top:calc(100% + 8px);left:0;width:min(330px,calc(100vw - 56px));border:1px solid #d9e8de;border-radius:16px;padding:14px;background:#fff;box-shadow:0 20px 48px rgba(31,72,52,.18)}.calendar-heading{display:grid;grid-template-columns:32px 1fr 32px;align-items:center;gap:8px;margin-bottom:12px}.calendar-heading>button{width:32px;height:32px;border:0;border-radius:9px;background:#eff7f1;color:#377257;font-size:22px}.calendar-heading>button:disabled{opacity:.35;cursor:not-allowed}.calendar-heading>div{display:flex;justify-content:center;gap:6px}.calendar-heading select{appearance:none;border:1px solid transparent;border-radius:8px;padding:6px 9px;background:#fff;color:#2f5d47;font-size:13px;font-weight:800;text-align:center;outline:none}.calendar-heading select:hover,.calendar-heading select:focus{border-color:#cce2d4;background:#f4faf6}.calendar-weekdays,.calendar-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}.calendar-weekdays{margin-bottom:5px}.calendar-weekdays span{padding:5px 0;color:#8a9890;font-size:10px;font-weight:700;text-align:center}.calendar-grid button{aspect-ratio:1;border:0;border-radius:10px;background:transparent;color:#334d40;font-size:12px}.calendar-grid button:hover:not(:disabled){background:#eaf6ee;color:#226f50}.calendar-grid button.adjacent{color:#acb7b0}.calendar-grid button.selected{background:linear-gradient(145deg,#21856a,#51a77f);color:#fff;font-weight:800;box-shadow:0 6px 14px rgba(36,132,101,.24)}.calendar-grid button:disabled{color:#d4dbd6;cursor:not-allowed}.calendar-grid button:focus-visible{outline:2px solid #69a98a;outline-offset:1px}@media(max-width:680px){.date-picker-popover{position:fixed;top:auto;right:12px;bottom:12px;left:12px;width:auto;border-radius:20px;padding:18px}.calendar-grid button{min-height:40px}.calendar-heading select{font-size:15px}}
</style>
