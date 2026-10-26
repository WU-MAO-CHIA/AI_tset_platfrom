import apiClient from './apiClient'

// spec 005：執行環境。linux = 網頁測試、windows = Windows 桌面應用程式測試
export type EnvironmentKind = 'linux' | 'windows'
export type EnvironmentStatus = 'online' | 'busy' | 'offline' | 'unauthorized' | 'local' | 'unknown' | 'desktop_locked'

export const BUILTIN_ENVIRONMENT_ID = 'builtin-linux'

export interface RunnerEnvironment {
  id: string
  name: string
  kind: EnvironmentKind
  enabled: boolean
  is_builtin: boolean
  // 只有 admin 會拿到位址；token 永遠不會回傳
  url: string | null
  status: EnvironmentStatus
  checked_at: string | null
}

export interface EnvironmentInput {
  name: string
  kind: EnvironmentKind
  url: string
  token: string
  enabled: boolean
}

export const KIND_LABEL: Record<EnvironmentKind, string> = {
  linux: 'Linux 容器（網頁）',
  windows: 'Windows（桌面程式）',
}

export const STATUS_LABEL: Record<EnvironmentStatus, string> = {
  online: '已連線',
  busy: '執行中',
  offline: '未連線',
  unauthorized: 'token 錯誤',
  local: '後端本機執行',
  unknown: '尚未檢查',
  desktop_locked: '桌面已鎖定',
}

export async function listEnvironments(): Promise<RunnerEnvironment[]> {
  const res = await apiClient.get<{ items: RunnerEnvironment[] }>('/runner-environments')
  return res.data.items
}

export async function createEnvironment(payload: EnvironmentInput): Promise<RunnerEnvironment> {
  const res = await apiClient.post<RunnerEnvironment>('/runner-environments', payload)
  return res.data
}

// token 留空表示不變
export async function updateEnvironment(id: string, payload: Partial<EnvironmentInput>): Promise<RunnerEnvironment> {
  const res = await apiClient.put<RunnerEnvironment>(`/runner-environments/${id}`, payload)
  return res.data
}

export async function deleteEnvironment(id: string): Promise<void> {
  await apiClient.delete(`/runner-environments/${id}`)
}

export async function checkEnvironment(id: string): Promise<RunnerEnvironment> {
  const res = await apiClient.post<RunnerEnvironment>(`/runner-environments/${id}/check`)
  return res.data
}

export function kindOf(environments: RunnerEnvironment[], id: string | null | undefined): EnvironmentKind | null {
  return environments.find((e) => e.id === id)?.kind ?? null
}
