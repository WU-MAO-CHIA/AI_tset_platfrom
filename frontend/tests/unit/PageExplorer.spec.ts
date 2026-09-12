import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PageExplorer from '../../src/components/PageExplorer/index.vue'
import * as caseApiModule from '../../src/services/caseApi'

vi.mock('../../src/services/caseApi', () => ({
  caseApi: {
    explorePage: vi.fn(),
    getExploreSession: vi.fn(),
  },
}))

const CATALOG = [
  {
    goal: '登入按鈕', status: 'found', note: '', ref: 'e1',
    role: 'button', name: '登入',
    recommended: 'role=button[name="登入"]',
    xpath: '//button[1]', css: 'button', xpath_unique: true,
  },
  {
    goal: '不存在的東西', status: 'not_found', note: '沒看到', ref: '',
    role: '', name: '', recommended: '', xpath: '', css: '', xpath_unique: false,
  },
]

function mountExplorer() {
  return mount(PageExplorer, { props: { caseId: 'case-1' } })
}

describe('PageExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('launch button is disabled without url and goals', () => {
    const wrapper = mountExplorer()
    const btn = wrapper.find('[data-testid="explore-launch-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('launches exploration and renders catalog after polling', async () => {
    vi.mocked(caseApiModule.caseApi.explorePage).mockResolvedValue({
      data: { session_id: 's-1', status_url: '/api/v1/cases/case-1/explore-sessions/s-1' },
    } as any)
    vi.mocked(caseApiModule.caseApi.getExploreSession).mockResolvedValue({
      data: {
        session_id: 's-1', case_id: 'case-1', url: 'https://example.com/',
        status: 'done', steps: 3, log: [{ step: 1, action: 'snapshot' }],
        catalog: CATALOG, note: '找到 1/2 個目標',
      },
    } as any)

    const wrapper = mountExplorer()
    await wrapper.find('[data-testid="explore-url"]').setValue('https://example.com/')
    await wrapper.find('[data-testid="explore-goals"]').setValue('登入按鈕\n不存在的東西')
    await wrapper.find('[data-testid="explore-launch-btn"]').trigger('click')
    await flushPromises()

    expect(caseApiModule.caseApi.explorePage).toHaveBeenCalledWith('case-1', {
      url: 'https://example.com/',
      goals: ['登入按鈕', '不存在的東西'],
      variables: [],
    })

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(caseApiModule.caseApi.getExploreSession).toHaveBeenCalledWith('case-1', 's-1')
    const table = wrapper.find('[data-testid="explore-catalog"]')
    expect(table.exists()).toBe(true)
    expect(table.text()).toContain('//button[1]')
    expect(table.text()).toContain('role=button[name="登入"]')
  })

  it('apply button emits only found elements', async () => {
    vi.mocked(caseApiModule.caseApi.explorePage).mockResolvedValue({
      data: { session_id: 's-1', status_url: '/x' },
    } as any)
    vi.mocked(caseApiModule.caseApi.getExploreSession).mockResolvedValue({
      data: {
        session_id: 's-1', case_id: 'case-1', url: 'https://example.com/',
        status: 'done', steps: 2, log: [], catalog: CATALOG, note: '',
      },
    } as any)

    const wrapper = mountExplorer()
    await wrapper.find('[data-testid="explore-url"]').setValue('https://example.com/')
    await wrapper.find('[data-testid="explore-goals"]').setValue('登入按鈕')
    await wrapper.find('[data-testid="explore-launch-btn"]').trigger('click')
    await flushPromises()
    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    await wrapper.find('[data-testid="explore-apply-btn"]').trigger('click')
    const emitted = wrapper.emitted('catalog-ready')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toHaveLength(1)
    expect(emitted![0][0][0].xpath).toBe('//button[1]')
  })

  it('shows error when launch fails', async () => {
    vi.mocked(caseApiModule.caseApi.explorePage).mockRejectedValue(new Error('案例不存在'))

    const wrapper = mountExplorer()
    await wrapper.find('[data-testid="explore-url"]').setValue('https://example.com/')
    await wrapper.find('[data-testid="explore-goals"]').setValue('登入按鈕')
    await wrapper.find('[data-testid="explore-launch-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="explore-error"]').text()).toContain('案例不存在')
  })
})
