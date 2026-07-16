<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
}>(), {
  label: '时间',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const standardMinutes = Array.from({ length: 12 }, (_, index) => String(index * 5).padStart(2, '0'))
const parts = computed(() => {
  const [hour = '', minute = ''] = props.modelValue.split(':')
  return { hour, minute }
})
const minutes = computed(() => (
  parts.value.minute && !standardMinutes.includes(parts.value.minute)
    ? [...standardMinutes, parts.value.minute].sort()
    : standardMinutes
))

function selectedValue(event: unknown) {
  const value = (event as { target?: { value?: unknown } }).target?.value
  return typeof value === 'string' ? value : ''
}

function updateHour(event: unknown) {
  const hour = selectedValue(event)
  emit('update:modelValue', hour || parts.value.minute ? `${hour}:${parts.value.minute}` : '')
}

function updateMinute(event: unknown) {
  const minute = selectedValue(event)
  emit('update:modelValue', parts.value.hour || minute ? `${parts.value.hour}:${minute}` : '')
}
</script>

<template>
  <div class="time-select">
    <select :aria-label="`${label}小时`" :value="parts.hour" @change="updateHour">
      <option value="">时</option>
      <option v-for="hour in hours" :key="hour" :value="hour">{{ hour }}</option>
    </select>
    <span>:</span>
    <select :aria-label="`${label}分钟`" :value="parts.minute" @change="updateMinute">
      <option value="">分</option>
      <option v-for="minute in minutes" :key="minute" :value="minute">{{ minute }}</option>
    </select>
  </div>
</template>

<style scoped>
.time-select{display:grid;grid-template-columns:minmax(70px,1fr) auto minmax(70px,1fr);align-items:center;gap:7px}.time-select select{width:100%;min-width:0}.time-select span{color:#809087;font-weight:800}
</style>
