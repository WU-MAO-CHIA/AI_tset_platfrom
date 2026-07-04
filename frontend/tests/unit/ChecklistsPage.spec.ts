import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import ChecklistsPage from '../../src/pages/ChecklistsPage.vue'
import * as checklistApiModule from '../../src/services/checklistApi'

vi.mock('../../src/services/checklistApi', () => ({
  listChecklists: vi.fn(),
  createChecklist: vi.fn(),
}))

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/checklists', component: ChecklistsPage },
    { path: '/checklists/:id', component: { template: '<div />' } },
  ],
})

describe('ChecklistsPage', () => {
  beforeEach(() => {
    vi.mocked(checklistApiModule.listChecklists).mockResolvedValue({
      items: [
        { id: 'cl-1', name: 'Sprint 1', created_by: 'tester', case_count: 3, last_run_at: null, status: null },
        { id: 'cl-2', name: 'Sprint 2', created_by: 'tester', case_count: 5, last_run_at: '2026-01-01', status: 'passed' },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    } as any)
  })

  it('renders page title', async () => {
    const wrapper = mount(ChecklistsPage, { global: { plugins: [router] } })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('測試清單')
  })

  it('renders search bar', async () => {
    const wrapper = mount(ChecklistsPage, { global: { plugins: [router] } })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('input[data-testid="search-input"]').exists()).toBe(true)
  })

  it('renders checklist table with rows', async () => {
    const wrapper = mount(ChecklistsPage, { global: { plugins: [router] } })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 0))
    const rows = wrapper.findAll('tr[data-testid="checklist-row"]')
    expect(rows.length).toBeGreaterThan(0)
  })

  it('checklist rows are clickable', async () => {
    const wrapper = mount(ChecklistsPage, { global: { plugins: [router] } })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 0))
    const row = wrapper.find('tr[data-testid="checklist-row"]')
    expect(row.exists()).toBe(true)
    expect(row.classes()).toContain('clickable')
  })

  it('renders create button', async () => {
    const wrapper = mount(ChecklistsPage, { global: { plugins: [router] } })
    expect(wrapper.find('button').text()).toContain('建立')
  })
})
