const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const USER_ID = import.meta.env.VITE_USER_ID || 'demo-traveler'

export interface Plan { id: number; destination_city: string; origin_city: string; start_date: string; end_date: string; latest_version?: { version_no: number; plan_json: Record<string, unknown> }; [key: string]: unknown }
export interface BlogMaterial { id: number; title: string; destination: string }
export interface BlogGeneration { id: number; generated_title?: string; generated_content: string; tags?: string; risk_note?: string }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `请求失败（${response.status}）`) }
  return response.json() as Promise<T>
}

export const api = {
  userId: USER_ID,
  generatePlan: (payload: Record<string, string>) => request<Plan>('/trip-plans/generate', { method: 'POST', body: JSON.stringify({ ...payload, user_id: USER_ID, action: 'create' }) }),
  revisePlan: (id: number, revision_request: string) => request<Plan>(`/trip-plans/${id}/revise`, { method: 'POST', body: JSON.stringify({ user_id: USER_ID, revision_request }) }),
  listPlans: () => request<Plan[]>(`/trip-plans?user_id=${encodeURIComponent(USER_ID)}`),
  getPlan: (id: number) => request<Plan>(`/trip-plans/${id}`),
  humanizePlan: (id: number) => request<{ natural_language: string }>(`/trip-plans/${id}/humanize`, { method: 'POST', body: JSON.stringify({ user_id: USER_ID }) }),
  createMaterial: (payload: Record<string, unknown>) => request<BlogMaterial>('/blog/materials', { method: 'POST', body: JSON.stringify({ ...payload, user_id: USER_ID }) }),
  generateBlog: (material_id: number, content_type: string, writing_style: string) => request<BlogGeneration>('/blog/generate', { method: 'POST', body: JSON.stringify({ material_id, content_type, writing_style, user_id: USER_ID }) }),
  listGenerations: () => request<Array<Record<string, unknown>>>(`/blog/generations?user_id=${encodeURIComponent(USER_ID)}`),
}
