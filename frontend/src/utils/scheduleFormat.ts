import type { Schedule } from '../services/scheduleApi'

export const WEEKDAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']

export function describeFrequency(s: Pick<Schedule, 'frequency' | 'time_of_day' | 'weekdays' | 'interval_minutes'>): string {
  switch (s.frequency) {
    case 'daily':
      return `每天 ${s.time_of_day}`
    case 'weekly': {
      const days = (s.weekdays ?? []).map((d) => WEEKDAY_LABELS[d]).join('、')
      return `每週${days} ${s.time_of_day}`
    }
    case 'interval': {
      const minutes = s.interval_minutes ?? 0
      return minutes % 60 === 0 ? `每 ${minutes / 60} 小時` : `每 ${minutes} 分鐘`
    }
    default:
      return s.frequency
  }
}

// 以排程時區顯示時間，避免瀏覽器與伺服器時區不同時看錯
export function formatScheduleTime(iso: string | null, timeZone: string): string {
  if (!iso) return '-'
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

export function triggerLabel(r: { schedule_id?: string | null; schedule_name?: string | null }): string {
  if (!r.schedule_id) return '手動'
  return r.schedule_name ? `排程：${r.schedule_name}` : '排程（已刪除）'
}
