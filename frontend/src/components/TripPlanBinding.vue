<script setup lang="ts">
import type { Plan, Trip } from '@/services/api'

defineProps<{ trip?: Trip; plan?: Plan }>()

function titleOf(plan: Plan | undefined, trip: Trip | undefined) {
  if (typeof plan?.title === 'string' && plan.title.trim()) return plan.title
  return trip ? `${trip.destination_city}旅行规划` : '请选择旅行规划'
}
</script>

<template>
  <section class="plan-binding" aria-label="当前旅行规划关联">
    <span>PLAN ↔ SCHEDULE</span>
    <div><b>{{ titleOf(plan, trip) }}</b><small v-if="trip">日程、提醒和陪伴对话均关联至此规划</small><small v-else>先在旅行规划中生成一份计划，再管理实时日程。</small></div>
    <em v-if="trip">{{ trip.start_date }} 至 {{ trip.end_date }}</em>
  </section>
</template>

<style scoped>
.plan-binding{display:flex;align-items:center;gap:13px;margin-bottom:18px;border:1px solid #d7e9db;border-radius:14px;padding:12px 16px;background:linear-gradient(110deg,#f7fcf8,#edf8f0)}.plan-binding>span{flex:none;border-radius:999px;padding:5px 8px;background:#dff1e4;color:#39745a;font-size:10px;font-weight:800;letter-spacing:.07em}.plan-binding div{display:grid;min-width:0;gap:3px}.plan-binding b{overflow:hidden;color:#355446;font-size:14px;text-overflow:ellipsis;white-space:nowrap}.plan-binding small{color:#75867c;font-size:11px}.plan-binding em{margin-left:auto;color:#57806b;font-size:12px;font-style:normal;font-weight:700;white-space:nowrap}@media(max-width:620px){.plan-binding{align-items:start;flex-wrap:wrap}.plan-binding em{width:100%;margin-left:0}}
</style>
