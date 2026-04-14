// Typed API client
const BASE = '/api'

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

// ---- types ------------------------------------------------------------------

export interface Device {
  id: string
  name: string
  serial: string
  model: string
  status: 'online' | 'offline'
  last_seen: string | null
}

export interface Task {
  id: string
  goal: string
  device_id: string | null
  status: 'pending' | 'running' | 'done' | 'error'
  success: boolean | null
  reason: string
  steps: number
  provider: string
  model: string
  created_at: string
  finished_at: string | null
}

export interface TaskLog {
  id: number
  message: string
  created_at: string
}

export interface Settings {
  default_provider: string
  gemini_model: string
  openai_model: string
  anthropic_model: string
  deepseek_model: string
  zhipu_model: string
  ollama_model: string
  ollama_base_url: string
  max_steps: number
  google_api_key: string
  openai_api_key: string
  anthropic_api_key: string
  deepseek_api_key: string
  zhipu_api_key: string
}

export interface TokenOut {
  id: string
  name: string
  token: string
}

// ---- devices ----------------------------------------------------------------

export const getDevices = () => req<Device[]>('/devices')
export const deleteDevice = (id: string) =>
  req<void>(`/devices/${id}`, { method: 'DELETE' })
export const createToken = (name: string) =>
  req<TokenOut>('/tokens', { method: 'POST', body: JSON.stringify({ name }) })

// ---- tasks ------------------------------------------------------------------

export const getTasks = (limit = 50) => req<Task[]>(`/tasks?limit=${limit}`)
export const getTask = (id: string) => req<Task>(`/tasks/${id}`)
export const getTaskLogs = (id: string) => req<TaskLog[]>(`/tasks/${id}/logs`)
export const createTask = (body: {
  goal: string
  device_id: string
  provider?: string
  model?: string
  enable_vision?: boolean
  enable_reasoning?: boolean
}) => req<Task>('/tasks', { method: 'POST', body: JSON.stringify(body) })

// ---- settings ---------------------------------------------------------------

export const getSettings = () => req<Settings>('/settings')
export const updateSettings = (data: Partial<Settings>) =>
  req<Settings>('/settings', { method: 'PUT', body: JSON.stringify(data) })
