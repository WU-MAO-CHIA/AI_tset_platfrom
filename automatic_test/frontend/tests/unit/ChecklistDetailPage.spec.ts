import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import ChecklistDetailPage from '../../src/pages/ChecklistDetailPage.vue'
import * as checklistApiModule from '../../src/services/checklistApi'

vi.mock('../../src/services/checklistApi', () => ({
  getChecklist: vi.fn(),
  updateChecklistItems: vi.fn(),
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
    vi.mocked(checklistApiModule.getChecklist).mockResolvedValue({
      id: 'cl-1',
      name: 'Sprint 1',
      created_by: 'tester',
      created_at: '2026-01-01T00:00:00Z',
      items: [
        { id: 'item-1', test_case_id: 'tc-1', order: 1, test_case: { case_number: 'TC-001', name: '登入測試', system_category: 'auth' } },
      ],
    } as any)
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
})
