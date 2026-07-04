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

// ──────────────── LLM 設定 ────────────────

// 金鑰／連線由 .env 配置，後台唯讀顯示；「目前啟用模型」存 DB、後台可切換（FR-027）

export interface LlmKeyStatus {
  anthropic_key_set: boolean
  anthropic_key_masked?: string
  openai_key_set: boolean
  openai_key_masked?: string
  ollama_base_url?: string
  ollama_configured?: boolean
}

export interface LlmModel {
  id: string
  name: string
  provider: string
  requires_setup: boolean
}

export const getLlmKeyStatus = (): Promise<LlmKeyStatus> =>
  apiClient.get('/admin/llm-keys').then((r) => r.data)

export const getDefaultModel = (): Promise<{ model: string }> =>
  apiClient.get('/admin/llm-default-model').then((r) => r.data)

export const getLlmModels = (): Promise<{ models: LlmModel[]; default: string }> =>
  apiClient.get('/llm-models').then((r) => r.data)

export const getActiveModel = (): Promise<{ model: string }> =>
  apiClient.get('/admin/active-model').then((r) => r.data)

export const setActiveModel = (model: string): Promise<{ model: string }> =>
  apiClient.put('/admin/active-model', { model }).then((r) => r.data)
