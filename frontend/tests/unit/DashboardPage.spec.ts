import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardPage from '../../src/pages/DashboardPage.vue'
import * as dashboardApi from '../../src/services/dashboardApi'

vi.mock('../../src/services/dashboardApi', () => ({ getDashboard: vi.fn() }))

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }],
})

function execution(overrides: Partial<dashboardApi.DashboardExecution> = {}): dashboardApi.DashboardExecution {
  return {
    id: 'e-1', execution_type: 'checklist', status: 'running', target_name: '每日回歸',
    checklist_id: 'cl-1', source_case_id: null, schedule_id: null, schedule_name: null, priority: 0,
    queued_at: '2026-10-25T01:00:00+00:00', started_at: '2026-10-25T01:00:00+00:00', heartbeat_at: null,
    passed_count: 2, failed_count: 1, total_count: 6,
    ...overrides,
  }
}

function dashboard(): dashboardApi.Dashboard {
  return {
    generated_at: '2026-10-25T01:05:00+00:00',
    timezone: 'Asia/Taipei',
    max_concurrent: 2,
    counts: { running: 1, pending: 2, schedules_enabled: 1, schedules_total: 3 },
    running: [execution({ schedule_id: 's-1', schedule_name: 'nightly' })],
    pending: [
      execution({ id: 'e-2', status: 'pending', execution_type: 'trial_run', target_name: '登入測試', priority: 10 }),
      execution({ id: 'e-3', status: 'pending' }),
    ],
    schedules: [{
      id: 's-1', checklist_id: 'cl-1', checklist_name: '每日回歸', name: 'nightly', enabled: true,
      frequency: 'daily', time_of_day: '02:00', weekdays: null, interval_minutes: null,
      parallel_mode: false, max_workers: 1, timezone: 'Asia/Taipei',
      next_run_at: '2026-10-25T18:00:00+00:00', last_triggered_at: null, last_execution_id: null,
      last_execution_status: null, last_skip_reason: null, created_by: 'admin',
    }],
  }
}

async function mountPage() {
  const wrapper = mount(DashboardPage, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(dashboardApi.getDashboard).mockReset().mockResolvedValue(dashboard())
  })
  afterEach(() => vi.useRealTimers())

  it('shows counts, running, queued and scheduled items', async () => {
    const wrapper = await mountPage()
    const text = wrapper.text()

    expect(wrapper.find('[data-testid="stat-running"]').text()).toContain('/ 2')
    expect(wrapper.find('[data-testid="stat-schedules"]').text()).toContain('/ 3')
    expect(wrapper.find('[data-testid="table-running"]').text()).toContain('排程：nightly')
    expect(wrapper.find('[data-testid="table-pending"]').text()).toContain('試跑：登入測試')
    expect(wrapper.find('[data-testid="table-schedules"]').text()).toContain('每天 02:00')
    expect(text).toContain('執行中')
  })

  it('refreshes periodically', async () => {
    await mountPage()
    expect(dashboardApi.getDashboard).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(5000)
    expect(dashboardApi.getDashboard).toHaveBeenCalledTimes(2)
  })

  it('shows an error when loading fails', async () => {
    vi.mocked(dashboardApi.getDashboard).mockRejectedValue(new Error('boom'))
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="dashboard-error"]').exists()).toBe(true)
  })
})
