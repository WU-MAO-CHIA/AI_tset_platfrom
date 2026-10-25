import apiClient from './apiClient'

export type ScheduleFrequency = 'daily' | 'weekly' | 'interval'

export interface Schedule {
  id: string
  checklist_id: string
  checklist_name: string | null
  name: string
  enabled: boolean
  frequency: ScheduleFrequency
  time_of_day: string | null
  // 0 = 週一 … 6 = 週日
  weekdays: number[] | null
  interval_minutes: number | null
  parallel_mode: boolean
  max_workers: number
  // 排程時間的解讀時區（後端 SCHEDULE_TIMEZONE）
  timezone: string
  next_run_at: string | null
  last_triggered_at: string | null
  last_execution_id: string | null
  last_execution_status: string | null
  last_skip_reason: string | null
  created_by: string
}

export interface ScheduleInput {
  name: string
  enabled: boolean
  frequency: ScheduleFrequency
  time_of_day: string | null
  weekdays: number[] | null
  interval_minutes: number | null
  parallel_mode: boolean
  max_workers: number
}

export async function listSchedules(): Promise<{ items: Schedule[]; total: number }> {
  const res = await apiClient.get('/schedules')
  return res.data
}

export async function listChecklistSchedules(checklistId: string): Promise<{ items: Schedule[]; total: number }> {
  const res = await apiClient.get(`/checklists/${checklistId}/schedules`)
  return res.data
}

export async function createSchedule(checklistId: string, payload: ScheduleInput): Promise<Schedule> {
  const res = await apiClient.post<Schedule>(`/checklists/${checklistId}/schedules`, payload)
  return res.data
}

// 只更新有帶的欄位，例如只送 { enabled } 來啟用 / 停用
export async function updateSchedule(id: string, payload: Partial<ScheduleInput>): Promise<Schedule> {
  const res = await apiClient.put<Schedule>(`/schedules/${id}`, payload)
  return res.data
}

export async function deleteSchedule(id: string): Promise<void> {
  await apiClient.delete(`/schedules/${id}`)
}
