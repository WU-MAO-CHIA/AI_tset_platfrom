import apiClient from './apiClient'
import type { Schedule } from './scheduleApi'

export interface DashboardExecution {
  id: string
  execution_type: string
  status: string
  // 清單執行為清單名稱，試跑為案例名稱
  target_name: string | null
  checklist_id: string | null
  source_case_id: string | null
  schedule_id: string | null
  schedule_name: string | null
  priority: number
  queued_at: string | null
  started_at: string | null
  heartbeat_at: string | null
  passed_count: number
  failed_count: number
  total_count: number
}

export interface Dashboard {
  generated_at: string
  timezone: string
  max_concurrent: number
  counts: { running: number; pending: number; schedules_enabled: number; schedules_total: number }
  running: DashboardExecution[]
  // 依 worker 領取順序
  pending: DashboardExecution[]
  // 已啟用排程，依下次執行時間
  schedules: Schedule[]
}

export const getDashboard = (): Promise<Dashboard> =>
  apiClient.get('/admin/dashboard').then((r) => r.data)
