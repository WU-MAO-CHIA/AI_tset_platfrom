import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import ChecklistDetailPage from '../../src/pages/ChecklistDetailPage.vue'
import * as checklistApiModule from '../../src/services/checklistApi'

vi.mock('../../src/services/checklistApi', () => ({
  getChecklist: vi.fn(),
  getChecklistCases: vi.fn(),
  getChecklistExecutions: vi.fn(),
  updateChecklist: vi.fn(),
  deleteChecklist: vi.fn(),
  patchChecklistCaseItem: vi.fn(),
}))

vi.mock('../../src/services/scheduleApi', () => ({
  listChecklistSchedules: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}))

vi.mock('../../src/components/ChecklistView/index.vue', () => ({
  default: { template: '<div class="checklist-view-stub" />' },
}))

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/checklists', component: { template: '<div />' } },
    { path: '/checklists/:id', component: ChecklistDetailPage },
  ],
})

describe('ChecklistDetailPage', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.mocked(checklistApiModule.getChecklist).mockResolvedValue({
      id: 'cl-1',
      name: 'Sprint 1',
      created_by: 'tester',
      created_at: '2026-01-01T00:00:00Z',
      items: [
        { id: 'item-1', test_case_id: 'tc-1', order: 1, test_case: { case_number: 'TC-001', name: '登入測試', system_category: 'auth' } },
      ],
    } as any)
    vi.mocked(checklistApiModule.getChecklistExecutions).mockResolvedValue({ items: [] } as any)
    vi.mocked(checklistApiModule.getChecklistCases).mockResolvedValue({ items: [] } as any)
    await router.push('/checklists/cl-1')
    await router.isReady()
  })

  it('renders checklist name in header', async () => {
    const wrapper = mount(ChecklistDetailPage, { global: { plugins: [router] } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Sprint 1')
  })

  it('renders basic info section', async () => {
    const wrapper = mount(ChecklistDetailPage, { global: { plugins: [router] } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="basic-info"]').exists()).toBe(true)
  })

  it('renders case list section', async () => {
    const wrapper = mount(ChecklistDetailPage, { global: { plugins: [router] } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="case-list"]').exists()).toBe(true)
  })

  it('renders execution history section', async () => {
    const wrapper = mount(ChecklistDetailPage, { global: { plugins: [router] } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="execution-history"]').exists()).toBe(true)
  })

  it('renders action buttons (execute and edit)', async () => {
    const wrapper = mount(ChecklistDetailPage, { global: { plugins: [router] } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="btn-execute"]').exists()).toBe(true)
  })

  it('renders schedules section and how each execution was triggered', async () => {
    vi.mocked(checklistApiModule.getChecklistExecutions).mockResolvedValue({
      items: [
        { id: 'exec-sched-1', status: 'completed', passed_count: 1, failed_count: 0, total_count: 1, started_at: null, finished_at: null, schedule_id: 's-1', schedule_name: 'nightly' },
        { id: 'exec-manual', status: 'completed', passed_count: 1, failed_count: 0, total_count: 1, started_at: null, finished_at: null },
      ],
    } as any)
    const wrapper = mount(ChecklistDetailPage, { global: { plugins: [router] } })
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="schedules"]').exists()).toBe(true)
    const history = wrapper.find('[data-testid="execution-history"]').text()
    expect(history).toContain('排程：nightly')
    expect(history).toContain('手動')
  })
})
