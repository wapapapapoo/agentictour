import { reactive } from 'vue'

const STORAGE_KEY = 'agentictour.session'

export interface AuthSession {
  accessToken: string
  userId: number
  username: string
}

function readStoredSession(): Partial<AuthSession> {
  try {
    return JSON.parse(globalThis.localStorage?.getItem(STORAGE_KEY) || '{}') as Partial<AuthSession>
  } catch {
    return {}
  }
}

const stored = readStoredSession()

export const session = reactive<{ accessToken: string; userId: number | null; username: string }>({
  accessToken: stored.accessToken || '',
  userId: typeof stored.userId === 'number' && Number.isInteger(stored.userId) ? stored.userId : null,
  username: stored.username || '',
})

export function saveSession(value: AuthSession) {
  session.accessToken = value.accessToken
  session.userId = value.userId
  session.username = value.username
  globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(value))
}

export function clearSession() {
  session.accessToken = ''
  session.userId = null
  session.username = ''
  globalThis.localStorage?.removeItem(STORAGE_KEY)
}

export function isAuthenticated() {
  return Boolean(session.accessToken && session.userId)
}
