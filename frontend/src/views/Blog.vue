<script setup lang="ts">
/* global navigator */
import { ref } from 'vue'
import { useTravelStore } from '@/stores/travel'
import { useRouter } from 'vue-router'

const store = useTravelStore()
const router = useRouter()

const tone = ref('casual')
const focus = ref('highlights')

const tones = [
  { id: 'casual', name: '轻松随性', emoji: '😎', desc: '朋友聊天般的口吻' },
  { id: 'formal', name: '优雅正式', emoji: '🎩', desc: '精致的旅行散文' },
  { id: 'poetic', name: '诗意盎然', emoji: '🌸', desc: '如诗如画的文字' },
  { id: 'humorous', name: '幽默风趣', emoji: '🤪', desc: '段子手风格' },
]

const focuses = [
  { id: 'highlights', name: '行程高光', emoji: '✨' },
  { id: 'food', name: '美食探店', emoji: '🍜' },
  { id: 'culture', name: '文化探索', emoji: '🏛️' },
  { id: 'photography', name: '摄影记录', emoji: '📸' },
  { id: 'tips', name: '实用攻略', emoji: '💡' },
]

async function generate() {
  await store.generateBlog(tone.value, focus.value)
}

function copyContent() {
  if (store.blogContent) {
    navigator.clipboard.writeText(store.blogContent)
  }
}

function goToPlan() {
  router.push('/plan')
}

// Simple markdown render placeholder (VLM integration point for future)
</script>

<template>
  <div class="blog-page">
    <div class="blog-layout">
      <!-- Controls -->
      <aside class="blog-sidebar">
        <h2>✍️ 游记创作</h2>
        <p class="sidebar-desc">
          基于你的旅行计划，AI自动生成精美游记
        </p>

        <!-- Plan selector -->
        <div class="control-group">
          <label>📋 旅行计划</label>
          <div
            v-if="store.currentPlan"
            class="selected-plan"
          >
            <span class="plan-dest">{{ store.currentPlan.request.destination }}</span>
            <span class="plan-date">{{ store.currentPlan.request.start_date }} ~ {{ store.currentPlan.request.end_date }}</span>
          </div>
          <div
            v-else
            class="no-plan"
          >
            <p>还没有旅行计划</p>
            <button
              class="link-btn"
              @click="goToPlan"
            >
              → 先去创建一个
            </button>
          </div>
        </div>

        <!-- Tone -->
        <div class="control-group">
          <label>🎭 写作风格</label>
          <div class="tone-grid">
            <button
              v-for="t in tones"
              :key="t.id"
              :class="{ active: tone === t.id }"
              @click="tone = t.id"
            >
              <span class="tone-emoji">{{ t.emoji }}</span>
              <span class="tone-name">{{ t.name }}</span>
              <span class="tone-desc">{{ t.desc }}</span>
            </button>
          </div>
        </div>

        <!-- Focus -->
        <div class="control-group">
          <label>🎯 内容重点</label>
          <div class="focus-grid">
            <button
              v-for="f in focuses"
              :key="f.id"
              :class="{ active: focus === f.id }"
              @click="focus = f.id"
            >
              {{ f.emoji }} {{ f.name }}
            </button>
          </div>
        </div>

        <!-- Generate button -->
        <button
          class="generate-btn"
          :disabled="!store.currentPlan || store.isGenerating"
          @click="generate"
        >
          <template v-if="store.isGenerating">
            <span class="spinner" />
            AI正在创作中...
          </template>
          <template v-else>
            ✨ 生成游记
          </template>
        </button>
      </aside>

      <!-- Preview -->
      <div class="blog-preview">
        <div
          v-if="!store.blogContent"
          class="empty-preview"
        >
          <div class="empty-icon">
            ✍️
          </div>
          <h3>你的游记将在这里呈现</h3>
          <p>
            1. 先在「旅行计划」页面创建行程<br>
            2. 选择写作风格和内容重点<br>
            3. 点击「生成游记」按钮
          </p>
          <div class="preview-features">
            <div class="preview-feature">
              <span class="pf-icon">📝</span>
              <span>Markdown格式</span>
            </div>
            <div class="preview-feature">
              <span class="pf-icon">🏷️</span>
              <span>自动生成标签</span>
            </div>
            <div class="preview-feature">
              <span class="pf-icon">📱</span>
              <span>社交媒体优化</span>
            </div>
            <div class="preview-feature">
              <span class="pf-icon">🎨</span>
              <span>多风格可选</span>
            </div>
          </div>
        </div>

        <div
          v-else
          class="blog-content"
        >
          <div class="blog-toolbar">
            <button
              class="toolbar-btn"
              @click="copyContent"
            >
              📋 复制全文
            </button>
          </div>
          <div class="markdown-body">
            <pre>{{ store.blogContent }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.blog-page {
  height: calc(100vh - 64px);
  overflow: hidden;
}

.blog-layout {
  display: flex;
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ── Sidebar ── */
.blog-sidebar {
  width: 300px;
  flex-shrink: 0;
  padding: 2rem 1.5rem;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
}

.blog-sidebar h2 {
  font-size: 1.4rem;
  margin: 0;
  text-align: left;
}

.sidebar-desc {
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.6;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.control-group label {
  font-weight: 600;
  font-size: 0.85rem;
  color: #cbd5e1;
}

.selected-plan {
  padding: 0.8rem;
  background: rgba(66, 184, 131, 0.08);
  border: 1px solid rgba(66, 184, 131, 0.15);
  border-radius: 10px;
}

.plan-dest {
  display: block;
  font-weight: 600;
  color: #e2e8f0;
  font-size: 0.95rem;
}

.plan-date {
  display: block;
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 0.3rem;
}

.no-plan {
  padding: 1rem;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  text-align: center;
}

.no-plan p {
  color: #94a3b8;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.link-btn {
  background: none;
  border: none;
  color: #42b883;
  cursor: pointer;
  font-size: 0.85rem;
}

/* Tone */
.tone-grid {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.tone-grid button {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  color: #94a3b8;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.tone-grid button:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.tone-grid button.active {
  background: rgba(66, 184, 131, 0.1);
  border-color: #42b883;
  color: #e2e8f0;
}

.tone-emoji { font-size: 1.2rem; }
.tone-name { font-weight: 600; font-size: 0.85rem; }
.tone-desc { font-size: 0.75rem; opacity: 0.6; margin-left: auto; }

/* Focus */
.focus-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.focus-grid button {
  padding: 0.4rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.02);
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.focus-grid button:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.focus-grid button.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: #3b82f6;
  color: #3b82f6;
}

/* Generate button */
.generate-btn {
  width: 100%;
  padding: 0.9rem;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #8b5cf6, #3b82f6);
  color: white;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: auto;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.3);
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Preview ── */
.blog-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.empty-preview {
  text-align: center;
  margin: auto;
  padding: 3rem;
  max-width: 500px;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-preview h3 {
  color: #e2e8f0;
  font-size: 1.3rem;
  margin-bottom: 1rem;
}

.empty-preview p {
  color: #94a3b8;
  line-height: 2;
  margin-bottom: 2rem;
}

.preview-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
}

.preview-feature {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  font-size: 0.85rem;
  color: #94a3b8;
}

.pf-icon {
  font-size: 1.2rem;
}

/* Blog content */
.blog-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.blog-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.toolbar-btn {
  padding: 0.4rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.toolbar-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
}

.markdown-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.markdown-body pre {
  font-family: var(--mono, monospace);
  font-size: 0.9rem;
  line-height: 1.8;
  color: #cbd5e1;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .blog-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    max-height: 40vh;
  }
  .blog-layout {
    flex-direction: column;
  }
}
</style>
