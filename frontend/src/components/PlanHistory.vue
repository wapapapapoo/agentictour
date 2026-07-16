<script setup lang="ts">
import type { Plan } from '@/services/api'

defineProps<{
  plans: Plan[]
  loading: boolean
  activePlanId?: number
}>()

const emit = defineEmits<{ select: [plan: Plan] }>()

function titleOf(plan: Plan) {
  return typeof plan.title === 'string' && plan.title.trim()
    ? plan.title
    : `${plan.destination_city}旅行规划`
}
</script>

<template>
  <section class="plan-history" aria-label="历史旅行规划">
    <div class="history-heading">
      <div>
        <p>TRAVEL PLAN ARCHIVE</p>
        <h2>历史旅行规划</h2>
        <span>所有生成成功的规划都会自动保存在这里。</span>
      </div>
      <b>{{ plans.length }} 份规划</b>
    </div>
    <p v-if="loading" class="muted">正在读取历史旅行规划…</p>
    <div v-else-if="plans.length" class="plan-grid">
      <button
        v-for="plan in plans"
        :key="plan.id"
        type="button"
        :class="{ active: activePlanId === plan.id }"
        @click="emit('select', plan)"
      >
        <i>#{{ plan.id }}</i>
        <strong>{{ titleOf(plan) }}</strong>
        <span>{{ plan.origin_city }} → {{ plan.destination_city }}</span>
        <small>{{ plan.start_date }} 至 {{ plan.end_date }}</small>
        <em>查看并继续调整 →</em>
      </button>
    </div>
    <div v-else class="empty"><b>✦</b><span>还没有历史规划。生成第一份旅行规划后，它会自动出现在这里。</span></div>
  </section>
</template>

<style scoped>
.plan-history{margin-bottom:28px;border:1px solid #dfeae2;border-radius:20px;padding:24px 27px;background:linear-gradient(145deg,#fff,#f6fbf7);box-shadow:0 10px 28px rgba(39,91,66,.05)}.history-heading{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:18px}.history-heading p{margin:0 0 6px;color:#579379;font-size:11px;font-weight:800;letter-spacing:.13em}.history-heading h2{margin:0;color:#294a3b;font-size:21px}.history-heading span{display:block;margin-top:6px;color:#7d8d84;font-size:13px}.history-heading>b{flex:none;border-radius:999px;padding:6px 10px;background:#eaf7ed;color:#498166;font-size:12px}.plan-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.plan-grid button{display:grid;min-height:145px;gap:7px;border:1px solid #dfebe2;border-radius:13px;padding:15px;background:#fff;text-align:left;cursor:pointer;transition:transform .2s,border-color .2s,box-shadow .2s}.plan-grid button:hover,.plan-grid button.active{border-color:#86bd9d;box-shadow:0 9px 20px rgba(40,105,73,.11);transform:translateY(-2px)}.plan-grid i{color:#91a59a;font:700 11px monospace}.plan-grid strong{overflow:hidden;color:#385447;font-size:14px;text-overflow:ellipsis;white-space:nowrap}.plan-grid span,.plan-grid small{color:#788a80;font-size:12px}.plan-grid em{margin-top:auto;color:#438063;font-size:12px;font-style:normal;font-weight:700}.muted{margin:0;color:#7c8b83;font-size:13px}.empty{display:flex;align-items:center;gap:10px;border:1px dashed #d2e4d7;border-radius:12px;padding:17px;color:#7b8c82;font-size:13px}.empty b{color:#6da283;font-size:20px}@media(max-width:760px){.plan-history{padding:21px}.history-heading{align-items:start;flex-direction:column;gap:8px}.plan-grid{grid-template-columns:1fr}}
</style>
