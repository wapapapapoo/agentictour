<script setup lang="ts">
import { computed } from 'vue'
import type { Plan } from '@/services/api'

const props = defineProps<{ plan: Plan }>()
const emit = defineEmits<{ close: [] }>()

function parseJsonObject(source: string): Record<string, unknown> {
  const cleaned = source.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/```(?:json)?/gi, '').trim()
  for (let start = cleaned.indexOf('{'); start >= 0; start = cleaned.indexOf('{', start + 1)) {
    let depth = 0; let quoted = false; let escaped = false
    for (let end = start; end < cleaned.length; end += 1) {
      const character = cleaned[end]
      if (quoted) { if (escaped) escaped = false; else if (character === '\\') escaped = true; else if (character === '"') quoted = false; continue }
      if (character === '"') { quoted = true; continue }
      if (character === '{') depth += 1
      if (character === '}') { depth -= 1; if (depth === 0) { try { const value = JSON.parse(cleaned.slice(start, end + 1)); if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown> } catch { /* Continue looking for a JSON object. */ } break } }
    }
  }
  return {}
}

function readPlan(value: unknown): Record<string, unknown> {
  if (typeof value === 'string') return parseJsonObject(value)
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  const object = value as Record<string, unknown>
  if (Array.isArray(object.days) || typeof object.title === 'string') return object
  for (const key of ['plan_json', 'result', 'answer', 'output', 'data', 'content']) {
    const nested = readPlan(object[key])
    if (Object.keys(nested).length) return nested
  }
  return {}
}

const data = computed(() => readPlan(props.plan.latest_version?.plan_json))
const days = computed(() => Array.isArray(data.value.days) ? data.value.days as Array<Record<string, unknown>> : [])
const title = computed(() => typeof data.value.title === 'string' ? data.value.title : `${props.plan.destination_city}旅行规划`)
function items(day: Record<string, unknown>) { const value = Array.isArray(day.items) ? day.items : Array.isArray(day.activities) ? day.activities : []; return value.map((item) => item && typeof item === 'object' ? item as Record<string, unknown> : { name: String(item) }) }
</script>

<template>
  <div class="modal-backdrop" role="presentation" @click.self="emit('close')">
    <section class="modal" role="dialog" aria-modal="true" aria-label="历史旅行规划详情">
      <header><div><p>HISTORICAL TRIP PLAN</p><h2>{{ title }}</h2><span>{{ plan.origin_city }} → {{ plan.destination_city }} · {{ plan.start_date }} 至 {{ plan.end_date }}</span></div><button type="button" aria-label="关闭详情" @click="emit('close')">×</button></header>
      <main>
        <p v-if="typeof data.summary === 'string'" class="summary">{{ data.summary }}</p>
        <div v-if="days.length" class="days"><article v-for="(day, index) in days" :key="index"><span>DAY {{ index + 1 }}</span><h3>{{ String(day.theme || day.title || `第 ${index + 1} 天`) }}</h3><p>{{ String(day.date || day.summary || day.description || '') }}</p><div v-if="items(day).length" class="items"><div v-for="(item, itemIndex) in items(day)" :key="itemIndex"><b>{{ String(item.time || '待定') }}</b><span>{{ String(item.name || item.title || item.description || '行程安排') }}</span><small v-if="item.tips">{{ String(item.tips) }}</small></div></div></article></div>
        <div v-else class="empty"><b>暂时无法整理这份历史规划</b><p>该规划没有可识别的日程 JSON 内容。</p></div>
      </main>
    </section>
  </div>
</template>

<style scoped>
.modal-backdrop{position:fixed;z-index:100;inset:0;display:grid;place-items:center;padding:24px;background:rgba(24,47,36,.48);backdrop-filter:blur(5px)}.modal{display:flex;width:min(850px,100%);max-height:min(82vh,780px);overflow:hidden;flex-direction:column;border:1px solid #dbe9df;border-radius:22px;background:#fff;box-shadow:0 28px 70px rgba(16,45,31,.3)}.modal header{display:flex;justify-content:space-between;gap:18px;padding:23px 26px;border-bottom:1px solid #eaf0eb;background:linear-gradient(120deg,#fff,#eff9f1)}.modal header p{margin:0 0 7px;color:#589478;font-size:11px;font-weight:800;letter-spacing:.13em}.modal h2{margin:0;color:#294a3b;font:700 clamp(22px,3vw,30px)/1.3 'Noto Serif SC','Microsoft YaHei',serif}.modal header span{display:block;margin-top:6px;color:#74867c;font-size:13px}.modal header button{width:34px;height:34px;flex:none;border:0;border-radius:50%;background:#e6f3e9;color:#47745d;font-size:24px;line-height:1;cursor:pointer}.modal main{overflow:auto;padding:24px 26px}.summary{margin:0 0 18px;color:#50685c;line-height:1.8}.days{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.days article{border:1px solid #e2ebe4;border-radius:14px;padding:17px;background:#fcfefc}.days article>span{color:#5a987b;font-size:11px;font-weight:800}.days h3{margin:8px 0;color:#345445;font-size:17px}.days article>p{margin:0 0 11px;color:#76877e;font-size:12px;line-height:1.6}.items{display:grid;gap:7px}.items div{display:grid;grid-template-columns:58px 1fr;gap:3px 8px;border-radius:8px;padding:8px;background:#f2f8f3;color:#50685b;font-size:12px}.items b{color:#318363}.items small{grid-column:2;color:#85928b;line-height:1.45}.empty{padding:28px;border-radius:13px;background:#f6faf7;color:#536a5e}.empty p{margin:7px 0 0;color:#7d8b84;font-size:13px}@media(max-width:620px){.modal-backdrop{padding:12px}.modal{max-height:90vh}.modal header,.modal main{padding:19px}.days{grid-template-columns:1fr}.modal header span{line-height:1.55}}
</style>
