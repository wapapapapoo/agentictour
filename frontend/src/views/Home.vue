<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTravelStore } from '@/stores/travel'

const router = useRouter()
const store = useTravelStore()

const featuredDestinations = ref([
  { id: 'tokyo', name: '东京', country: '日本', emoji: '🗼', desc: '传统与现代的完美融合', color: '#ef4444' },
  { id: 'paris', name: '巴黎', country: '法国', emoji: '🗼', desc: '光之城的浪漫之旅', color: '#3b82f6' },
  { id: 'kyoto', name: '京都', country: '日本', emoji: '⛩️', desc: '千年古都的和风雅韵', color: '#f59e0b' },
  { id: 'chengdu', name: '成都', country: '中国', emoji: '🐼', desc: '巴适得板的天府之国', color: '#10b981' },
  { id: 'bali', name: '巴厘岛', country: '印尼', emoji: '🏝️', desc: '众神之岛的热带天堂', color: '#06b6d4' },
  { id: 'bangkok', name: '曼谷', country: '泰国', emoji: '🛕', desc: '天使之城的热情活力', color: '#8b5cf6' },
])

function goPlan(dest?: string) {
  if (dest) {
    router.push({ path: '/plan', query: { destination: dest } })
  } else {
    router.push('/plan')
  }
}

onMounted(() => {
  store.fetchDestinations()
})
</script>

<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <h1>
          <span class="gradient-text">AI 智能旅行规划</span>
        </h1>
        <p class="hero-subtitle">
          多智能体协作 · 个性化行程定制 · 全程AI陪伴 · 一键生成游记
        </p>
        <div class="hero-actions">
          <button
            class="btn-primary"
            @click="goPlan()"
          >
            ✨ 开始规划你的旅程
          </button>
          <button
            class="btn-secondary"
            @click="router.push('/companion')"
          >
            🤖 体验AI旅行伴侣
          </button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="floating-icons">
          <span
            class="float-icon"
            style="top: 10%; left: 10%; animation-delay: 0s"
          >🗺️</span>
          <span
            class="float-icon"
            style="top: 20%; right: 15%; animation-delay: 0.5s"
          >✈️</span>
          <span
            class="float-icon"
            style="top: 50%; left: 5%; animation-delay: 1s"
          >🏨</span>
          <span
            class="float-icon"
            style="top: 60%; right: 10%; animation-delay: 1.5s"
          >🍜</span>
          <span
            class="float-icon"
            style="top: 80%; left: 20%; animation-delay: 2s"
          >📸</span>
          <span
            class="float-icon"
            style="top: 40%; right: 25%; animation-delay: 0.8s"
          >🌤️</span>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            🧠 Multi-Agent 工作流
          </div>
          <div class="agent-list">
            <div class="agent-item">
              🕵️ ScoutAgent — 目的地调研
            </div>
            <div class="agent-item">
              🌤️ WeatherAgent — 天气分析
            </div>
            <div class="agent-item">
              📋 PlannerAgent — 行程规划
            </div>
            <div class="agent-item">
              💰 BudgetAgent — 预算优化
            </div>
            <div class="agent-item">
              🍜 FoodieAgent — 美食推荐
            </div>
            <div class="agent-item">
              🎯 Synthesizer — 方案整合
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="features">
      <h2>三大核心功能</h2>
      <div class="feature-grid">
        <div
          class="feature-card"
          @click="router.push('/plan')"
        >
          <div class="feature-icon">
            📋
          </div>
          <h3>智能旅行规划</h3>
          <p>6个AI Agent协同工作，从目的地调研到预算优化，10秒生成专属旅行计划</p>
          <ul>
            <li>多目的地知识库</li>
            <li>实时天气集成</li>
            <li>个性化行程定制</li>
            <li>预算智能分配</li>
          </ul>
        </div>
        <div
          class="feature-card"
          @click="router.push('/companion')"
        >
          <div class="feature-icon">
            🤖
          </div>
          <h3>AI旅行伴侣</h3>
          <p>旅途中的智能助手，随时解答交通、美食、天气、翻译等问题</p>
          <ul>
            <li>实时翻译助手</li>
            <li>美食探店推荐</li>
            <li>交通导航建议</li>
            <li>拍照打卡指南</li>
          </ul>
        </div>
        <div
          class="feature-card"
          @click="router.push('/blog')"
        >
          <div class="feature-icon">
            ✍️
          </div>
          <h3>游记智能创作</h3>
          <p>旅行结束后一键生成精美游记，多种风格可选，支持社交平台发布</p>
          <ul>
            <li>Markdown格式输出</li>
            <li>多种写作风格</li>
            <li>自动生成标签</li>
            <li>社交媒体优化</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Quick destinations -->
    <section class="destinations">
      <h2>热门目的地</h2>
      <div class="dest-grid">
        <div
          v-for="dest in featuredDestinations"
          :key="dest.id"
          class="dest-card"
          :style="{ '--accent': dest.color }"
          @click="goPlan(dest.id)"
        >
          <div class="dest-emoji">
            {{ dest.emoji }}
          </div>
          <div class="dest-info">
            <h3>{{ dest.name }}</h3>
            <p class="dest-country">
              {{ dest.country }}
            </p>
            <p class="dest-desc">
              {{ dest.desc }}
            </p>
          </div>
          <div class="dest-action">
            开始规划 →
          </div>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="how-it-works">
      <h2>AgenticTour 工作流</h2>
      <div class="steps">
        <div class="step">
          <div class="step-number">
            1
          </div>
          <h4>选择目的地</h4>
          <p>从全球热门目的地中选择或搜索你想去的地方</p>
        </div>
        <div class="step-arrow">
          →
        </div>
        <div class="step">
          <div class="step-number">
            2
          </div>
          <h4>设定偏好</h4>
          <p>旅行风格、预算、日期、人数，告诉AI你的需求</p>
        </div>
        <div class="step-arrow">
          →
        </div>
        <div class="step">
          <div class="step-number">
            3
          </div>
          <h4>Agent协作</h4>
          <p>6个专业Agent并行工作，调研、规划、优化一气呵成</p>
        </div>
        <div class="step-arrow">
          →
        </div>
        <div class="step">
          <div class="step-number">
            4
          </div>
          <h4>出发！</h4>
          <p>带上你的专属旅行计划出发，AI伴侣全程陪伴</p>
        </div>
      </div>
    </section>

    <footer>
      <p>🧳 AgenticTour — AI-Powered Travel Planning | Built with FastAPI + Vue 3</p>
    </footer>
  </div>
</template>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

/* ── Hero ── */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 70vh;
  padding: 4rem 0;
  gap: 4rem;
}

.hero-content {
  flex: 1;
}

h1 {
  font-size: 3.2rem;
  line-height: 1.2;
  margin-bottom: 1.2rem;
}

.gradient-text {
  background: linear-gradient(135deg, #42b883 0%, #3b82f6 50%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.15rem;
  color: #94a3b8;
  margin-bottom: 2rem;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 1rem;
}

.btn-primary {
  padding: 0.9rem 2rem;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #42b883, #3b82f6);
  color: white;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(66, 184, 131, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(66, 184, 131, 0.4);
}

.btn-secondary {
  padding: 0.9rem 2rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
  font-size: 1.05rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.25);
}

/* ── Hero Visual ── */
.hero-visual {
  flex: 1;
  position: relative;
  height: 400px;
}

.floating-icons {
  position: relative;
  width: 100%;
  height: 100%;
}

.float-icon {
  position: absolute;
  font-size: 2.5rem;
  animation: float 3s ease-in-out infinite;
  opacity: 0.7;
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-15px) rotate(5deg); }
}

.agent-card {
  position: absolute;
  bottom: 0;
  right: 0;
  background: rgba(30, 30, 50, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 1.5rem;
  width: 300px;
  backdrop-filter: blur(16px);
}

.agent-header {
  font-weight: 700;
  font-size: 0.95rem;
  margin-bottom: 0.8rem;
  color: #42b883;
}

.agent-item {
  font-size: 0.8rem;
  color: #94a3b8;
  padding: 0.3rem 0;
  font-family: var(--mono, monospace);
}

/* ── Features ── */
.features {
  padding: 4rem 0;
}

h2 {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 2.5rem;
  color: #e2e8f0;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.feature-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 2rem;
  cursor: pointer;
  transition: all 0.3s;
}

.feature-card:hover {
  background: rgba(66, 184, 131, 0.05);
  border-color: rgba(66, 184, 131, 0.2);
  transform: translateY(-4px);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.2rem;
  margin-bottom: 0.8rem;
  color: #e2e8f0;
}

.feature-card p {
  color: #94a3b8;
  font-size: 0.9rem;
  line-height: 1.7;
  margin-bottom: 1rem;
}

.feature-card ul {
  list-style: none;
  padding: 0;
}

.feature-card li {
  color: #64748b;
  font-size: 0.85rem;
  padding: 0.25rem 0;
}

.feature-card li::before {
  content: '✓ ';
  color: #42b883;
}

/* ── Destinations ── */
.destinations {
  padding: 4rem 0;
}

.dest-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}

.dest-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 1rem;
  position: relative;
  overflow: hidden;
}

.dest-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--accent);
  border-radius: 0 4px 4px 0;
}

.dest-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateX(4px);
}

.dest-emoji {
  font-size: 2.5rem;
  flex-shrink: 0;
}

.dest-info h3 {
  font-size: 1rem;
  color: #e2e8f0;
  margin-bottom: 0.2rem;
}

.dest-country {
  font-size: 0.8rem;
  color: #64748b;
}

.dest-desc {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 0.2rem;
}

.dest-action {
  margin-left: auto;
  color: var(--accent);
  font-size: 0.85rem;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.3s;
}

.dest-card:hover .dest-action {
  opacity: 1;
}

/* ── How it works ── */
.how-it-works {
  padding: 4rem 0;
}

.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
}

.step {
  text-align: center;
  flex: 1;
  max-width: 200px;
}

.step-number {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #42b883, #3b82f6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.2rem;
  margin: 0 auto 1rem;
}

.step h4 {
  color: #e2e8f0;
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}

.step p {
  color: #94a3b8;
  font-size: 0.8rem;
  line-height: 1.5;
}

.step-arrow {
  color: #42b883;
  font-size: 1.5rem;
  font-weight: 700;
}

/* ── Footer ── */
footer {
  text-align: center;
  padding: 3rem 0;
  color: #64748b;
  font-size: 0.85rem;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .hero {
    flex-direction: column;
    text-align: center;
    min-height: auto;
  }
  .hero-actions {
    justify-content: center;
    flex-wrap: wrap;
  }
  .hero-visual {
    display: none;
  }
  .feature-grid {
    grid-template-columns: 1fr;
  }
  .dest-grid {
    grid-template-columns: 1fr 1fr;
  }
  .steps {
    flex-direction: column;
  }
  .step-arrow {
    transform: rotate(90deg);
  }
}
</style>
