import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../../src/stores/authStore'
import ScheduleList from '../../src/components/ScheduleList/index.vue'
import ScheduleForm from '../../src/components/ScheduleForm/index.vue'
import * as scheduleApi from '../../src/services/scheduleApi'
import { confirmAction } from '../../src/composables/useConfirm'

vi.mock('../../src/services/runnerEnvironmentApi', async (importOriginal) => ({
  ...(await importOriginal<object>()),
  listEnvironments: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../src/services/scheduleApi', () => ({
  listSchedules: vi.fn(),
  listChecklistSchedules: vi.fn(),
  createSchedule: vi.fn(),
  updateSchedule: vi.fn(),
  deleteSchedule: vi.fn(),
}))

vi.mock('../../src/composables/useConfirm', () => ({ confirmAction: vi.fn() }))

const router = createRouter({
  history: createWebHashHistory(),
  routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }],
})

function schedule(overrides: Partial<scheduleApi.Schedule> = {}): scheduleApi.Schedule {
  return {
    id: 's-1', checklist_id: 'cl-1', checklist_name: '每日回歸', name: 'nightly', enabled: true,
    frequency: 'daily', time_of_day: '02:00', weekdays: null, interval_minutes: null,
    parallel_mode: false, max_workers: 1, timezone: 'Asia/Taipei',
    next_run_at: '2026-10-25T18:00:00+00:00', last_triggered_at: null,
    last_execution_id: 'exec-1', last_execution_status: 'completed', last_skip_reason: null,
    created_by: 'admin', ...overrides,
  }
}

async function mountAs(role: string, props: Record<string, unknown> = {}) {
  useAuthStore().role = role
  const wrapper = mount(ScheduleList, { props, global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('ScheduleList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(scheduleApi.listSchedules).mockResolvedValue({ items: [schedule()], total: 1 })
    vi.mocked(scheduleApi.listChecklistSchedules).mockResolvedValue({ items: [schedule()], total: 1 })
  })

  it('lists all schedules with checklist column and no add button', async () => {
    const wrapper = await mountAs('editor')
    expect(scheduleApi.listSchedules).toHaveBeenCalled()
    expect(wrapper.text()).toContain('每日回歸')
    expect(wrapper.text()).toContain('每天 02:00')
    expect(wrapper.text()).toContain('完成')
    expect(wrapper.find('[data-testid="btn-add-schedule"]').exists()).toBe(false)
  })

  it('shows skip reason instead of last result', async () => {
    vi.mocked(scheduleApi.listSchedules).mockResolvedValue({
      items: [schedule({ last_skip_reason: '前一次執行仍在排隊或執行中' })], total: 1,
    })
    const wrapper = await mountAs('viewer')
    expect(wrapper.text()).toContain('略過：前一次執行仍在排隊或執行中')
  })

  it('is read-only for viewers', async () => {
    const wrapper = await mountAs('viewer', { checklistId: 'cl-1' })
    expect(scheduleApi.listChecklistSchedules).toHaveBeenCalledWith('cl-1')
    expect(wrapper.find('[data-testid="btn-add-schedule"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="btn-toggle-schedule"]').exists()).toBe(false)
  })

  it('toggles enabled with a partial update', async () => {
    vi.mocked(scheduleApi.updateSchedule).mockResolvedValue(schedule({ enabled: false, next_run_at: null }))
    const wrapper = await mountAs('editor', { checklistId: 'cl-1' })

    await wrapper.find('[data-testid="btn-toggle-schedule"]').trigger('click')
    await flushPromises()

    expect(scheduleApi.updateSchedule).toHaveBeenCalledWith('s-1', { enabled: false })
    expect(wrapper.text()).toContain('停用')
  })

  it('creates a schedule for the checklist from the form', async () => {
    vi.mocked(scheduleApi.listChecklistSchedules).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(scheduleApi.createSchedule).mockResolvedValue(schedule({ id: 's-2', name: 'new' }))
    const wrapper = await mountAs('editor', { checklistId: 'cl-1' })
    expect(wrapper.find('[data-testid="schedule-empty"]').exists()).toBe(true)

    await wrapper.find('[data-testid="btn-add-schedule"]').trigger('click')
    const payload = { name: 'new', enabled: true, frequency: 'daily', time_of_day: '03:00', weekdays: null, interval_minutes: null, parallel_mode: false, max_workers: 1 }
    wrapper.findComponent(ScheduleForm).vm.$emit('submit', payload)
    await flushPromises()

    expect(scheduleApi.createSchedule).toHaveBeenCalledWith('cl-1', payload)
    expect(wrapper.find('[data-testid="schedule-row-s-2"]').exists()).toBe(true)
    expect(wrapper.findComponent(ScheduleForm).exists()).toBe(false)
  })

  it('shows the API validation message when saving fails', async () => {
    vi.mocked(scheduleApi.updateSchedule).mockRejectedValue({ response: { data: { message: 'max_workers must be between 1 and 5' } } })
    const wrapper = await mountAs('editor', { checklistId: 'cl-1' })

    await wrapper.find('[data-testid="btn-edit-schedule"]').trigger('click')
    wrapper.findComponent(ScheduleForm).vm.$emit('submit', {} as any)
    await flushPromises()

    expect(wrapper.text()).toContain('max_workers must be between 1 and 5')
    expect(wrapper.findComponent(ScheduleForm).exists()).toBe(true)
  })

  it('deletes after confirmation', async () => {
    vi.mocked(confirmAction).mockResolvedValue(true)
    vi.mocked(scheduleApi.deleteSchedule).mockResolvedValue()
    const wrapper = await mountAs('editor', { checklistId: 'cl-1' })

    await wrapper.find('[data-testid="btn-delete-schedule"]').trigger('click')
    await flushPromises()

    expect(scheduleApi.deleteSchedule).toHaveBeenCalledWith('s-1')
    expect(wrapper.find('[data-testid="schedule-empty"]').exists()).toBe(true)
  })

  it('does not delete when the confirmation is cancelled', async () => {
    vi.mocked(confirmAction).mockResolvedValue(false)
    const wrapper = await mountAs('editor', { checklistId: 'cl-1' })

    await wrapper.find('[data-testid="btn-delete-schedule"]').trigger('click')
    await flushPromises()

    expect(scheduleApi.deleteSchedule).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="schedule-row-s-1"]').exists()).toBe(true)
  })
})
