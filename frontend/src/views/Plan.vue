<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTravelStore } from '@/stores/travel'

const route = useRoute()
const store = useTravelStore()

// ── Form state ──
const destinations = [
  { id: 'tokyo', name: '东京 🇯🇵' },
  { id: 'paris', name: '巴黎 🇫🇷' },
  { id: 'kyoto', name: '京都 🇯🇵' },
  { id: 'chengdu', name: '成都 🇨🇳' },
  { id: 'bali', name: '巴厘岛 🇮🇩' },
  { id: 'bangkok', name: '曼谷 🇹🇭' },
]

const styles = [
  { id: 'balanced', name: '综合均衡', emoji: '⚖️', desc: '经典景点+local体验' },
  { id: 'foodie', name: '美食之旅', emoji: '🍜', desc: '以吃为核心' },
  { id: 'culture', name: '文化巡礼', emoji: '🏛️', desc: '博物馆+历史古迹' },
  { id: 'leisure', name: '悠闲度假', emoji: '🏖️', desc: '放松+SPA+慢节奏' },
  { id: 'adventure', name: '冒险探索', emoji: '🧗', desc: '户外+极限体验' },
  { id: 'shopping', name: '购物狂欢', emoji: '🛍️', desc: '商场+市场+买手店' },
  { id: 'luxury', name: '奢华享受', emoji: '🥂', desc: '高级酒店+米其林' },
]

const form = ref({
  destination: 'tokyo',
  departure_city: '北京',
  start_date: '',
  end_date: '',
  budget: 10000,
  travelers: 1,
  style: 'balanced',
  interests: [] as string[],
  special_requirements: '',
})

// Init dates
const today = new Date()
const nextMonth = new Date(today)
nextMonth.setMonth(nextMonth.getMonth() + 1)
form.value.start_date = today.toISOString().slice(0, 10)
form.value.end_date = new Date(today.getTime() + 5 * 86400000).toISOString().slice(0, 10)

// Watch for destination in query
watch(() => route.query.destination, (dest) => {
  if (dest && typeof dest === 'string') {
    form.value.destination = dest
  }
}, { immediate: true })

const interestOptions = ['美食', '摄影', '历史', '自然', '购物', '艺术', '运动', '音乐', '动漫', '咖啡']

function toggleInterest(interest: string) {
  const idx = form.value.interests.indexOf(interest)
  if (idx >= 0) {
    form.value.interests.splice(idx, 1)
  } else {
    form.value.interests.push(interest)
  }
}

const activeTab = ref<'form' | 'result' | 'logs'>('form')

async function submitPlan() {
  if (!form.value.start_date || !form.value.end_date) return

  await store.createPlan({
    destination: form.value.destination,
    departure_city: form.value.departure_city,
    start_date: form.value.start_date,
    end_date: form.value.end_date,
    budget: form.value.budget,
    travelers: form.value.travelers,
    style: form.value.style,
    interests: form.value.interests,
    special_requirements: form.value.special_requirements,
  })

  if (store.currentPlan) {
    activeTab.value = 'result'
  }
}

const budgetPercent = computed(() => {
  if (!store.currentPlan) return 0
  const breakdown = store.currentPlan.budget_breakdown
  const total = breakdown['总计'] || 1
  return Math.min(100, Math.round((total / form.value.budget) * 100))
})

// Format currency
function fmt(n: number) {
  return n.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })
}
</script>

<template>
  <div class="plan-page">
    <h1>📋 AI 智能旅行规划</h1>
    <p class="subtitle">
      填写你的需求，让6个AI Agent协作生成专属旅行计划
    </p>

    <!-- Tabs when we have a plan -->
    <div
      v-if="store.currentPlan"
      class="tabs"
    >
      <button
        :class="{ active: activeTab === 'form' }"
        @click="activeTab = 'form'"
      >
        📝 新建计划
      </button>
      <button
        :class="{ active: activeTab === 'result' }"
        @click="activeTab = 'result'"
      >
        📊 查看结果
      </button>
      <button
        :class="{ active: activeTab === 'logs' }"
        @click="activeTab = 'logs'"
      >
        🧠 Agent日志
      </button>
    </div>

    <!-- Form -->
    <div
      v-if="activeTab === 'form'"
      class="form-container"
    >
      <div class="form-grid">
        <!-- Destination -->
        <div class="form-group">
          <label>🌍 目的地</label>
          <select v-model="form.destination">
            <option
              v-for="d in destinations"
              :key="d.id"
              :value="d.id"
            >
              {{ d.name }}
            </option>
          </select>
        </div>

        <!-- Departure -->
        <div class="form-group">
          <label>🏠 出发城市</label>
          <input
            v-model="form.departure_city"
            type="text"
            placeholder="例如：北京"
          >
        </div>

        <!-- Dates -->
        <div class="form-group">
          <label>📅 出发日期</label>
          <input
            v-model="form.start_date"
            type="date"
          >
        </div>
        <div class="form-group">
          <label>📅 返回日期</label>
          <input
            v-model="form.end_date"
            type="date"
          >
        </div>

        <!-- Budget -->
        <div class="form-group">
          <label>💰 预算（元）</label>
          <input
            v-model.number="form.budget"
            type="number"
            min="1000"
            step="1000"
          >
        </div>

        <!-- Travelers -->
        <div class="form-group">
          <label>👥 出行人数</label>
          <input
            v-model.number="form.travelers"
            type="number"
            min="1"
            max="20"
          >
        </div>

        <!-- Style -->
        <div class="form-group full-width">
          <label>🎨 旅行风格</label>
          <div class="style-grid">
            <button
              v-for="s in styles"
              :key="s.id"
              :class="{ active: form.style === s.id }"
              class="style-btn"
              @click="form.style = s.id"
            >
              <span class="style-emoji">{{ s.emoji }}</span>
              <span class="style-name">{{ s.name }}</span>
              <span class="style-desc">{{ s.desc }}</span>
            </button>
          </div>
        </div>

        <!-- Interests -->
        <div class="form-group full-width">
          <label>🏷️ 兴趣标签（可多选）</label>
          <div class="interest-tags">
            <button
              v-for="tag in interestOptions"
              :key="tag"
              :class="{ active: form.interests.includes(tag) }"
              class="tag-btn"
              @click="toggleInterest(tag)"
            >
              {{ tag }}
            </button>
          </div>
        </div>

        <!-- Special requirements -->
        <div class="form-group full-width">
          <label>💬 特殊需求</label>
          <textarea
            v-model="form.special_requirements"
            placeholder="例如：需要无障碍设施、素食餐食、儿童友好..."
            rows="2"
          />
        </div>
      </div>

      <!-- Error -->
      <div
        v-if="store.planError"
        class="error-msg"
      >
        ❌ {{ store.planError }}
      </div>

      <!-- Submit -->
      <button
        class="submit-btn"
        :disabled="store.isPlanning"
        @click="submitPlan"
      >
        <template v-if="store.isPlanning">
          <span class="spinner" />
          Agent正在工作中...
        </template>
        <template v-else>
          🚀 让AI Agent开始规划
        </template>
      </button>
    </div>

    <!-- Result -->
    <div
      v-if="activeTab === 'result' && store.currentPlan"
      class="result-container"
    >
      <!-- Overview -->
      <div class="overview-card">
        <h2>{{ store.currentPlan.overview }}</h2>
      </div>

      <!-- Weather -->
      <div class="section">
        <h3>🌤️ 天气预报</h3>
        <div class="weather-grid">
          <div
            v-for="w in store.currentPlan.weather_forecast"
            :key="w.date"
            class="weather-card"
          >
            <div class="weather-date">
              {{ w.date }}
            </div>
            <div class="weather-icon">
              {{ w.condition }}
            </div>
            <div class="weather-temp">
              {{ Math.round(w.temperature_low) }}° ~ {{ Math.round(w.temperature_high) }}°
            </div>
            <div class="weather-tip">
              {{ w.tips }}
            </div>
          </div>
        </div>
      </div>

      <!-- Itinerary -->
      <div class="section">
        <h3>🗓️ 每日行程</h3>
        <div class="days-grid">
          <div
            v-for="day in store.currentPlan.days"
            :key="day.day"
            class="day-card"
          >
            <div class="day-header">
              <span class="day-num">Day {{ day.day }}</span>
              <span class="day-theme">{{ day.theme }}</span>
            </div>
            <div class="day-date">
              {{ day.date }}
            </div>
            <div class="day-activities">
              <div
                v-for="act in day.activities"
                :key="act.time"
                class="activity-item"
              >
                <div class="act-time">
                  {{ act.time }}
                </div>
                <div class="act-detail">
                  <div class="act-name">
                    {{ act.name }}
                  </div>
                  <div class="act-meta">
                    ⏱️ {{ act.duration }} | 🎫 {{ act.ticket }}
                  </div>
                  <div class="act-note">
                    💡 {{ act.note }}
                  </div>
                </div>
              </div>
            </div>
            <div class="day-meals">
              <div
                v-for="meal in day.meals"
                :key="meal.type"
                class="meal-item"
              >
                {{ meal.type }}: {{ meal.suggestion }}
              </div>
            </div>
            <div class="day-transport">
              🚗 {{ day.transportation }}
            </div>
          </div>
        </div>
      </div>

      <!-- Budget -->
      <div class="section">
        <h3>💰 预算分析</h3>
        <div class="budget-container">
          <div class="budget-chart">
            <div class="budget-total">
              <span class="label">总预算</span>
              <span class="value">{{ fmt(form.budget) }}</span>
            </div>
            <div class="budget-bar">
              <div
                class="budget-fill"
                :style="{ width: budgetPercent + '%' }"
                :class="{ over: budgetPercent > 100 }"
              />
            </div>
            <div
              v-if="store.currentPlan.budget_breakdown['总计']"
              class="budget-total"
            >
              <span class="label">预估花费</span>
              <span
                class="value"
                :class="{ over: budgetPercent > 100 }"
              >
                {{ fmt(store.currentPlan.budget_breakdown['总计']) }}
              </span>
            </div>
          </div>
          <div class="budget-details">
            <div
              v-for="(val, key) in store.currentPlan.budget_breakdown"
              :key="key"
              class="budget-row"
              :class="{ total: key === '总计' }"
            >
              <span>{{ key }}</span>
              <span>{{ fmt(val) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tips -->
      <div class="section">
        <h3>💡 旅行贴士</h3>
        <div class="tips-list">
          <div
            v-for="tip in store.currentPlan.tips"
            :key="tip"
            class="tip-item"
          >
            {{ tip }}
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Logs -->
    <div
      v-if="activeTab === 'logs' && store.currentPlan"
      class="logs-container"
    >
      <h3>🧠 Multi-Agent 工作日志</h3>
      <p class="logs-subtitle">
        以下是6个AI Agent的协作过程记录
      </p>
      <div class="log-list">
        <div
          v-for="(log, i) in store.agentLogs"
          :key="i"
          class="log-entry"
        >
          <span class="log-num">{{ i + 1 }}</span>
          <span class="log-text">{{ log }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plan-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #94a3b8;
  margin-bottom: 2rem;
}

/* ── Tabs ── */
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
}

.tabs button {
  padding: 0.6rem 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.tabs button.active {
  background: rgba(66, 184, 131, 0.15);
  border-color: rgba(66, 184, 131, 0.3);
  color: #42b883;
}

/* ── Form ── */
.form-container {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 2rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

label {
  font-weight: 600;
  font-size: 0.9rem;
  color: #cbd5e1;
}

input, select, textarea {
  padding: 0.7rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
  font-size: 0.95rem;
  font-family: inherit;
  transition: border-color 0.2s;
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: #42b883;
}

textarea {
  resize: vertical;
}

/* Style grid */
.style-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 0.6rem;
}

.style-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.8rem 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
}

.style-btn:hover {
  border-color: rgba(255, 255, 255, 0.2);
}

.style-btn.active {
  background: rgba(66, 184, 131, 0.1);
  border-color: #42b883;
  color: #42b883;
}

.style-emoji { font-size: 1.5rem; }
.style-name { font-size: 0.85rem; font-weight: 600; }
.style-desc { font-size: 0.7rem; opacity: 0.6; }

/* Interest tags */
.interest-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag-btn {
  padding: 0.4rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.tag-btn:hover {
  border-color: rgba(255, 255, 255, 0.2);
}

.tag-btn.active {
  background: rgba(59, 130, 246, 0.15);
  border-color: #3b82f6;
  color: #3b82f6;
}

/* Submit */
.submit-btn {
  width: 100%;
  margin-top: 2rem;
  padding: 1rem;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #42b883, #3b82f6);
  color: white;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(66, 184, 131, 0.3);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-msg {
  margin-top: 1rem;
  padding: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  color: #ef4444;
}

/* ── Result ── */
.result-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.overview-card {
  background: linear-gradient(135deg, rgba(66, 184, 131, 0.15), rgba(59, 130, 246, 0.15));
  border: 1px solid rgba(66, 184, 131, 0.2);
  border-radius: 16px;
  padding: 2rem;
}

.overview-card h2 {
  font-size: 1.15rem;
  line-height: 1.8;
  color: #e2e8f0;
  margin: 0;
  text-align: left;
}

.section {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 1.5rem;
}

.section h3 {
  margin-bottom: 1.2rem;
  font-size: 1.15rem;
}

/* Weather */
.weather-grid {
  display: flex;
  gap: 0.8rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}

.weather-card {
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 1rem;
  min-width: 140px;
  text-align: center;
}

.weather-date { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.3rem; }
.weather-icon { font-size: 1.2rem; margin-bottom: 0.3rem; }
.weather-temp { font-size: 0.95rem; font-weight: 600; color: #e2e8f0; }
.weather-tip { font-size: 0.75rem; color: #64748b; margin-top: 0.3rem; }

/* Days */
.days-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.day-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 1.5rem;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 0.3rem;
}

.day-num {
  background: #42b883;
  color: white;
  padding: 0.2rem 0.8rem;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.85rem;
}

.day-theme {
  font-weight: 600;
  color: #e2e8f0;
}

.day-date {
  color: #64748b;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.activity-item {
  display: flex;
  gap: 1rem;
  padding: 0.8rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.activity-item:last-child { border-bottom: none; }

.act-time {
  color: #42b883;
  font-weight: 700;
  font-size: 0.9rem;
  min-width: 45px;
}

.act-name { font-weight: 600; color: #e2e8f0; }
.act-meta { font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem; }
.act-note { font-size: 0.8rem; color: #64748b; margin-top: 0.1rem; }

.day-meals {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.meal-item {
  font-size: 0.85rem;
  color: #94a3b8;
  padding: 0.2rem 0;
}

.day-transport {
  margin-top: 0.8rem;
  font-size: 0.85rem;
  color: #64748b;
}

/* Budget */
.budget-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: start;
}

.budget-total {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.8rem;
}

.budget-total .label { color: #94a3b8; font-size: 0.9rem; }
.budget-total .value { font-weight: 700; font-size: 1.1rem; color: #42b883; }
.budget-total .value.over { color: #ef4444; }

.budget-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.budget-fill {
  height: 100%;
  background: linear-gradient(90deg, #42b883, #3b82f6);
  border-radius: 4px;
  transition: width 0.6s;
}

.budget-fill.over {
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.budget-details {
  display: flex;
  flex-direction: column;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 0.9rem;
  color: #94a3b8;
}

.budget-row.total {
  font-weight: 700;
  color: #e2e8f0;
  font-size: 1rem;
  border-bottom: none;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* Tips */
.tips-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
}

.tip-item {
  padding: 0.8rem 1rem;
  background: rgba(66, 184, 131, 0.05);
  border: 1px solid rgba(66, 184, 131, 0.1);
  border-radius: 10px;
  font-size: 0.9rem;
  color: #cbd5e1;
  line-height: 1.5;
}

/* ── Agent Logs ── */
.logs-container h3 {
  margin-bottom: 0.5rem;
}

.logs-subtitle {
  color: #64748b;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.log-entry {
  display: flex;
  gap: 0.8rem;
  padding: 0.6rem 1rem;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  font-size: 0.85rem;
  font-family: var(--mono, monospace);
  align-items: baseline;
}

.log-num {
  color: #64748b;
  min-width: 24px;
  text-align: right;
}

.log-text {
  color: #94a3b8;
}

@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr; }
  .budget-container { grid-template-columns: 1fr; }
  .tips-list { grid-template-columns: 1fr; }
}
</style>
