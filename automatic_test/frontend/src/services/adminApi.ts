import apiClient from './apiClient'

// ──────────────── 帳號管理 ────────────────

export interface UserRecord {
  id: string
  username: string
  role: string
  is_active: boolean
  created_at: string
}

export interface CreateUserPayload {
  username: string
  password: string
  role: string
}

export interface UpdateUserPayload {
  role?: string
  is_active?: boolean
  new_password?: string
}

export const listUsers = (): Promise<UserRecord[]> =>
  apiClient.get('/admin/users').then((r) => r.data)

export const createUser = (payload: CreateUserPayload): Promise<UserRecord> =>
  apiClient.post('/admin/users', payload).then((r) => r.data)

export const updateUser = (id: string, payload: UpdateUserPayload): Promise<void> =>
  apiClient.put(`/admin/users/${id}`, payload).then((r) => r.data)

export const deleteUser = (id: string): Promise<void> =>
  apiClient.delete(`/admin/users/${id}`).then((r) => r.data)

// ──────────────── 系統別管理 ────────────────

export interface SystemCategory {
  id: string
  name: string
  created_at: string
}

export const listSystemCategories = (): Promise<SystemCategory[]> =>
  apiClient.get('/admin/system-categories').then((r) => r.data)

export const createSystemCategory = (name: string): Promise<SystemCategory> =>
  apiClient.post('/admin/system-categories', { name }).then((r) => r.data)

export const renameSystemCategory = (id: string, name: string): Promise<SystemCategory> =>
  apiClient.put(`/admin/system-categories/${id}`, { name }).then((r) => r.data)

export const deleteSystemCategory = (id: string): Promise<{ deleted: boolean; affected_case_count: number }> =>
  apiClient.delete(`/admin/system-categories/${id}`).then((r) => r.data)

// ──────────────── LLM API Key 管理 ────────────────

// LLM 金鑰與預設模型由 .env 配置，後台僅唯讀顯示（FR-027）

export interface LlmKeyStatus {
  anthropic_key_set: boolean
  anthropic_key_masked?: string
  openai_key_set: boolean
  openai_key_masked?: string
}

export const getLlmKeyStatus = (): Promise<LlmKeyStatus> =>
  apiClient.get('/admin/llm-keys').then((r) => r.data)

export const getDefaultModel = (): Promise<{ model: string }> =>
  apiClient.get('/admin/llm-default-model').then((r) => r.data)
