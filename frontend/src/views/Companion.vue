<script setup lang="ts">
/* global HTMLElement */
import { ref, nextTick, watch } from 'vue'
import { useTravelStore } from '@/stores/travel'

const store = useTravelStore()
const messageInput = ref('')
const chatContainer = ref<HTMLElement | null>(null)

const quickActions = [
  { label: '🍜 附近美食', msg: '附近有什么好吃的？' },
  { label: '🌤️ 天气查询', msg: '今天天气怎么样？' },
  { label: '🚗 交通导航', msg: '怎么去最近的景点？' },
  { label: '🗣️ 实时翻译', msg: '帮我翻译一段话' },
  { label: '📸 拍照指南', msg: '哪里拍照最好看？' },
  { label: '💡 旅行贴士', msg: '有什么要注意的？' },
]

async function send() {
  const msg = messageInput.value.trim()
  if (!msg || store.isChatting) return

  messageInput.value = ''
  await store.sendMessage(msg)
  await scrollToBottom()
}

async function sendQuick(msg: string) {
  await store.sendMessage(msg)
  await scrollToBottom()
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// Auto-scroll on new messages
watch(() => store.chatHistory.length, () => {
  scrollToBottom()
})
</script>

<template>
  <div class="companion-page">
    <div class="companion-layout">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="companion-avatar">
          <span class="avatar-emoji">🤖</span>
          <h3>AI 旅行伴侣</h3>
          <p class="status online">
            ● 在线
          </p>
        </div>

        <div class="companion-intro">
          <p>我是你的AI旅行伴侣，随时为你提供：</p>
          <ul>
            <li>🚗 交通导航建议</li>
            <li>🍜 美食餐厅推荐</li>
            <li>🌤️ 实时天气查询</li>
            <li>🗣️ 语言翻译助手</li>
            <li>📸 拍照打卡指南</li>
            <li>🚨 紧急情况协助</li>
          </ul>
        </div>

        <div
          v-if="store.currentPlan"
          class="current-trip"
        >
          <h4>📋 当前行程</h4>
          <p>{{ store.currentPlan.request.destination }}</p>
          <p class="trip-dates">
            {{ store.currentPlan.request.start_date }} ~ {{ store.currentPlan.request.end_date }}
          </p>
        </div>

        <div class="quick-actions">
          <h4>⚡ 快速操作</h4>
          <button
            v-for="action in quickActions"
            :key="action.label"
            :disabled="store.isChatting"
            @click="sendQuick(action.msg)"
          >
            {{ action.label }}
          </button>
        </div>
      </aside>

      <!-- Chat area -->
      <div class="chat-area">
        <div
          ref="chatContainer"
          class="chat-messages"
        >
          <!-- Empty state -->
          <div
            v-if="store.chatHistory.length === 0"
            class="empty-chat"
          >
            <div class="empty-icon">
              🤖
            </div>
            <h2>你好！我是你的AI旅行伴侣</h2>
            <p>旅行中遇到任何问题都可以问我<br>点击左侧快捷操作或直接输入消息</p>
            <div class="empty-suggestions">
              <button
                v-for="action in quickActions.slice(0, 4)"
                :key="action.label"
                @click="sendQuick(action.msg)"
              >
                {{ action.label }}
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div
            v-for="(msg, i) in store.chatHistory"
            :key="i"
            :class="['message', msg.role]"
          >
            <div class="msg-avatar">
              {{ msg.role === 'user' ? '👤' : (msg.emoji || '🤖') }}
            </div>
            <div class="msg-bubble">
              <div class="msg-content">
                {{ msg.content }}
              </div>
              <!-- Suggestions -->
              <div
                v-if="msg.suggestions && msg.suggestions.length"
                class="msg-suggestions"
              >
                <button
                  v-for="s in msg.suggestions"
                  :key="s"
                  :disabled="store.isChatting"
                  @click="sendQuick(s)"
                >
                  {{ s }}
                </button>
              </div>
            </div>
          </div>

          <!-- Typing indicator -->
          <div
            v-if="store.isChatting"
            class="message assistant"
          >
            <div class="msg-avatar">
              🤖
            </div>
            <div class="msg-bubble">
              <div class="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div class="chat-input">
          <input
            v-model="messageInput"
            type="text"
            placeholder="输入你的问题，例如：附近有什么好吃的？"
            :disabled="store.isChatting"
            @keyup.enter="send"
          >
          <button
            :disabled="store.isChatting || !messageInput.trim()"
            @click="send"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.companion-page {
  height: calc(100vh - 64px);
  overflow: hidden;
}

.companion-layout {
  display: flex;
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ── Sidebar ── */
.sidebar {
  width: 280px;
  flex-shrink: 0;
  padding: 1.5rem;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
}

.companion-avatar {
  text-align: center;
}

.avatar-emoji {
  font-size: 3.5rem;
  display: block;
  margin-bottom: 0.5rem;
}

.companion-avatar h3 {
  font-size: 1.1rem;
  color: #e2e8f0;
}

.status {
  font-size: 0.8rem;
  margin-top: 0.3rem;
}

.status.online { color: #42b883; }

.companion-intro p {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.5rem;
}

.companion-intro ul {
  list-style: none;
  padding: 0;
}

.companion-intro li {
  font-size: 0.8rem;
  color: #64748b;
  padding: 0.2rem 0;
}

.current-trip {
  background: rgba(66, 184, 131, 0.08);
  border: 1px solid rgba(66, 184, 131, 0.15);
  border-radius: 12px;
  padding: 1rem;
}

.current-trip h4 {
  font-size: 0.85rem;
  color: #42b883;
  margin-bottom: 0.4rem;
}

.current-trip p {
  font-size: 0.9rem;
  color: #e2e8f0;
  font-weight: 600;
}

.trip-dates {
  font-size: 0.8rem !important;
  color: #94a3b8 !important;
  font-weight: 400 !important;
  margin-top: 0.2rem;
}

.quick-actions h4 {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.6rem;
}

.quick-actions button {
  display: block;
  width: 100%;
  padding: 0.5rem 0.8rem;
  margin-bottom: 0.4rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
  color: #94a3b8;
  font-size: 0.8rem;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.quick-actions button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.15);
}

/* ── Chat Area ── */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Empty state */
.empty-chat {
  text-align: center;
  margin: auto;
  padding: 3rem;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-chat h2 {
  font-size: 1.5rem;
  color: #e2e8f0;
  margin-bottom: 0.8rem;
}

.empty-chat p {
  color: #94a3b8;
  line-height: 1.8;
  margin-bottom: 2rem;
}

.empty-suggestions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.6rem;
}

.empty-suggestions button {
  padding: 0.6rem 1.2rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.empty-suggestions button:hover {
  background: rgba(66, 184, 131, 0.1);
  border-color: rgba(66, 184, 131, 0.3);
  color: #42b883;
}

/* Messages */
.message {
  display: flex;
  gap: 0.8rem;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.msg-bubble {
  padding: 1rem 1.2rem;
  border-radius: 16px;
  line-height: 1.7;
  font-size: 0.9rem;
}

.message.user .msg-bubble {
  background: linear-gradient(135deg, #42b883, #3b82f6);
  color: white;
  border-bottom-right-radius: 6px;
}

.message.assistant .msg-bubble {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  border-bottom-left-radius: 6px;
}

.msg-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.8rem;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.msg-suggestions button {
  padding: 0.3rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.msg-suggestions button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 0.2rem 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* Chat input */
.chat-input {
  display: flex;
  gap: 0.8rem;
  padding: 1.2rem 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(15, 15, 30, 0.95);
}

.chat-input input {
  flex: 1;
  padding: 0.8rem 1.2rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
  font-size: 0.95rem;
  font-family: inherit;
}

.chat-input input:focus {
  outline: none;
  border-color: #42b883;
}

.chat-input input::placeholder {
  color: #64748b;
}

.chat-input button {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #42b883, #3b82f6);
  color: white;
  font-size: 1.3rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-input button:hover:not(:disabled) {
  transform: scale(1.05);
}

.chat-input button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
  .message {
    max-width: 95%;
  }
}
</style>
