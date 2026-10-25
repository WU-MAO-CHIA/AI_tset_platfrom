import { describe, it, expect } from 'vitest'
import { describeFrequency, formatScheduleTime, triggerLabel } from '../../src/utils/scheduleFormat'

describe('scheduleFormat', () => {
  it('describes each frequency', () => {
    expect(describeFrequency({ frequency: 'daily', time_of_day: '02:00', weekdays: null, interval_minutes: null })).toBe('每天 02:00')
    expect(describeFrequency({ frequency: 'weekly', time_of_day: '09:30', weekdays: [0, 2, 6], interval_minutes: null })).toBe('每週一、三、日 09:30')
    expect(describeFrequency({ frequency: 'interval', time_of_day: null, weekdays: null, interval_minutes: 120 })).toBe('每 2 小時')
    expect(describeFrequency({ frequency: 'interval', time_of_day: null, weekdays: null, interval_minutes: 45 })).toBe('每 45 分鐘')
  })

  it('formats times in the schedule time zone, not the browser one', () => {
    // UTC 18:00 = 台北隔天 02:00
    expect(formatScheduleTime('2026-10-25T18:00:00+00:00', 'Asia/Taipei')).toContain('10/26')
    expect(formatScheduleTime('2026-10-25T18:00:00+00:00', 'Asia/Taipei')).toContain('02:00')
    expect(formatScheduleTime(null, 'Asia/Taipei')).toBe('-')
  })

  it('labels how an execution was triggered', () => {
    expect(triggerLabel({})).toBe('手動')
    expect(triggerLabel({ schedule_id: 's-1', schedule_name: 'nightly' })).toBe('排程：nightly')
    expect(triggerLabel({ schedule_id: 's-1', schedule_name: null })).toBe('排程（已刪除）')
  })
})
