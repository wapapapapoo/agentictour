import { session } from './session'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface AuthToken { access_token: string; token_type: string; user_id: number; username: string }
export interface Trip { id: number; title: string; origin_city: string; destination_city: string; start_date: string; end_date: string; timezone?: string; status: string }
export interface Plan { id: number; trip_id: number; destination_city: string; origin_city: string; start_date: string; end_date: string; latest_version?: { version_no: number; plan_json: Record<string, unknown> }; [key: string]: unknown }
export interface BlogMaterial { id: number; title: string; destination: string }
export interface BlogGeneration { id: number; generated_title?: string; generated_content: string; tags?: string; risk_note?: string }
export interface ChatReply { id?: number; reply: string; content?: string; created_at?: string }

function detailMessage(detail: unknown, fallback: string) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => (typeof item === 'object' && item ? String((item as { msg?: string }).msg || '') : '')).filter(Boolean).join('；') || fallback
  return fallback
}

function requireUserId() {
  if (!session.userId) throw new ApiError('请先登录后再使用该功能。', 401)
  return session.userId
}

function optionalDate(value: unknown) {
  return typeof value === 'string' && !value.trim() ? null : value
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (session.accessToken) headers.set('Authorization', `Bearer ${session.accessToken}`)
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown }
    throw new ApiError(detailMessage(body.detail, `请求失败（${response.status}）`), response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  register: (payload: { username: string; password: string; nickname?: string; phone?: string; email?: string }) => request<AuthToken>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload: { username: string; password: string }) => request<AuthToken>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  createTrip: (payload: Omit<Trip, 'id'>) => request<Trip>('/trips', { method: 'POST', body: JSON.stringify({ ...payload, user_id: requireUserId() }) }),
  listTrips: () => request<Trip[]>(`/trips?user_id=${requireUserId()}`),
  generatePlan: (payload: Record<string, unknown>) => request<Plan>('/trip-plans/generate', { method: 'POST', body: JSON.stringify({ ...payload, user_id: requireUserId(), action: 'create' }) }),
  revisePlan: (id: number, revision_request: string) => request<Plan>(`/trip-plans/${id}/revise`, { method: 'POST', body: JSON.stringify({ user_id: requireUserId(), revision_request }) }),
  listPlans: () => request<Plan[]>(`/trip-plans?user_id=${requireUserId()}`),
  getPlan: (id: number) => request<Plan>(`/trip-plans/${id}`),
  humanizePlan: (id: number) => request<{ natural_language: string }>(`/trip-plans/${id}/humanize`, { method: 'POST', body: JSON.stringify({ user_id: requireUserId() }) }),
  createMaterial: (payload: Record<string, unknown>) => request<BlogMaterial>('/blog/materials', { method: 'POST', body: JSON.stringify({ ...payload, start_date: optionalDate(payload.start_date), end_date: optionalDate(payload.end_date), user_id: requireUserId() }) }),
  uploadMaterialPhoto: (materialId: number, file: File) => { const form = new FormData(); form.append('user_id', String(requireUserId())); form.append('file', file); return request(`/blog/materials/${materialId}/photos`, { method: 'POST', body: form }) },
  generateBlog: (material_id: number, content_type: string, writing_style: string) => request<BlogGeneration>('/blog/generate', { method: 'POST', body: JSON.stringify({ material_id, content_type, writing_style, user_id: requireUserId() }) }),
  listGenerations: () => request<BlogGeneration[]>(`/blog/generations?user_id=${requireUserId()}`),
  sendChatMessage: (payload: { trip_id: number; message: string; city?: string; nearby_context?: string; latitude?: number; longitude?: number; location_name?: string }) => request<ChatReply>('/chat/messages', { method: 'POST', body: JSON.stringify({ ...payload, user_id: requireUserId() }) }),
  updateLocation: (payload: { latitude: number; longitude: number; city?: string; place_name?: string; location_context?: string }) => request('/locations', { method: 'PUT', body: JSON.stringify({ ...payload, user_id: requireUserId() }) }),
}
