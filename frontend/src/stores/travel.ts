import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type J = Record<string, any>

export interface TravelPlanRequest {
  destination: string
  departure_city: string
  start_date: string
  end_date: string
  budget: number
  travelers: number
  style: string
  interests: string[]
  special_requirements: string
}

export interface TravelPlan {
  id: string
  created_at: string
  request: TravelPlanRequest
  overview: string
  weather_forecast: J[]
  days: J[]
  budget_breakdown: Record<string, number>
  tips: string[]
  recommended_attractions: J[]
  recommended_hotels: J[]
  agent_log: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  suggestions?: string[]
  emoji?: string
}

const API_BASE = 'http://127.0.0.1:8000'

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  return String(err)
}

export const useTravelStore = defineStore('travel', () => {
  const currentPlan = ref<TravelPlan | null>(null)
  const plans = ref<TravelPlan[]>([])
  const isPlanning = ref(false)
  const planError = ref('')

  const chatHistory = ref<ChatMessage[]>([])
  const isChatting = ref(false)

  const blogContent = ref('')
  const isGenerating = ref(false)

  const destinations = ref<J[]>([])

  const hasPlan = computed(() => currentPlan.value !== null)
  const agentLogs = computed(() => currentPlan.value?.agent_log || [])

  async function fetchDestinations() {
    try {
      const res = await fetch(`${API_BASE}/api/destinations`)
      destinations.value = await res.json()
    } catch (err) {
      console.error('Failed to fetch destinations:', getErrorMessage(err))
    }
  }

  async function createPlan(request: TravelPlanRequest) {
    isPlanning.value = true
    planError.value = ''
    try {
      const res = await fetch(`${API_BASE}/api/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      currentPlan.value = await res.json()
    } catch (err) {
      planError.value = getErrorMessage(err)
    } finally {
      isPlanning.value = false
    }
  }

  async function fetchPlans() {
    try {
      const res = await fetch(`${API_BASE}/api/plan`)
      plans.value = await res.json()
    } catch (err) {
      console.error('Failed to fetch plans:', getErrorMessage(err))
    }
  }

  async function fetchPlan(id: string) {
    try {
      const res = await fetch(`${API_BASE}/api/plan/${id}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      currentPlan.value = await res.json()
    } catch (err) {
      planError.value = getErrorMessage(err)
    }
  }

  async function sendMessage(message: string) {
    chatHistory.value.push({ role: 'user', content: message })
    isChatting.value = true
    try {
      const res = await fetch(`${API_BASE}/api/companion/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: currentPlan.value?.id || null,
          message,
          context: {},
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      chatHistory.value.push({
        role: 'assistant',
        content: data.reply,
        suggestions: data.suggestions,
        emoji: data.agent_emoji,
      })
    } catch {
      chatHistory.value.push({
        role: 'assistant',
        content: '抱歉，我暂时无法回复。请检查后端是否运行。💤',
        emoji: '⚠️',
      })
    } finally {
      isChatting.value = false
    }
  }

  async function generateBlog(tone: string, focus: string) {
    if (!currentPlan.value) return
    isGenerating.value = true
    try {
      const res = await fetch(`${API_BASE}/api/blog/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: currentPlan.value.id,
          tone,
          focus,
          include_photos: true,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      blogContent.value = data.content
      return data
    } catch (err) {
      console.error('Blog generation failed:', getErrorMessage(err))
    } finally {
      isGenerating.value = false
    }
  }

  return {
    currentPlan,
    plans,
    isPlanning,
    planError,
    chatHistory,
    isChatting,
    blogContent,
    isGenerating,
    destinations,
    hasPlan,
    agentLogs,
    fetchDestinations,
    createPlan,
    fetchPlans,
    fetchPlan,
    sendMessage,
    generateBlog,
  }
})
