import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ResultPage from '../../src/pages/ResultPage.vue'
import * as executionApiModule from '../../src/services/executionApi'

vi.mock('../../src/services/executionApi', () => ({
  getExecution: vi.fn(),
  getExecutionResults: vi.fn(),
  exportReport: vi.fn(),
  getRfReportStatus: vi.fn(),
  streamExecution: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'exec-1' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const EXECUTION = {
  id: 'exec-1', status: 'failed', checklist_id: null, source_case_id: 'case-1',
  parallel_mode: false, max_workers: 1, passed_count: 0, failed_count: 1, total_count: 1,
}

const ITEMS = [
  {
    id: 'cr-1', test_case_id: 'case-1', case_number: 'MMA-001', case_name: 'MMA登入',
    status: 'skipped', elapsed_ms: 0,
    failure_message: '尚無 RF 程式碼（請先透過 AI 對話生成或上傳）', media: [],
  },
]

describe('ResultPage', () => {
  beforeEach(() => vi.clearAllMocks())

  function mockTerminal(status = 'failed') {
    vi.mocked(executionApiModule.getExecution).mockResolvedValue({ ...EXECUTION, status } as any)
    vi.mocked(executionApiModule.getExecutionResults).mockResolvedValue({ items: ITEMS, total: 1 } as any)
  }

  it('renders case results with failure message', async () => {
    mockTerminal()
    vi.mocked(executionApiModule.getRfReportStatus).mockResolvedValue({ available: false } as any)

    const wrapper = mount(ResultPage)
    await flushPromises()

    const table = wrapper.find('[data-testid="case-results"]')
    expect(table.exists()).toBe(true)
    expect(table.text()).toContain('MMA-001')
    expect(table.text()).toContain('尚無 RF 程式碼')
    expect(executionApiModule.streamExecution).not.toHaveBeenCalled()
  })

  it('shows friendly placeholder instead of iframing a missing report', async () => {
    mockTerminal()
    vi.mocked(executionApiModule.getRfReportStatus).mockResolvedValue({ available: false } as any)

    const wrapper = mount(ResultPage)
    await flushPromises()

    expect(wrapper.find('iframe.rf-iframe').exists()).toBe(false)
    const placeholder = wrapper.find('[data-testid="rf-report-missing"]')
    expect(placeholder.exists()).toBe(true)
    expect(placeholder.text()).toContain('尚無 RF 測試報告')
    expect(placeholder.text()).toContain('尚無 RF 程式碼')
  })

  it('renders iframe when report is available', async () => {
    mockTerminal()
    vi.mocked(executionApiModule.getRfReportStatus).mockResolvedValue({ available: true } as any)

    const wrapper = mount(ResultPage)
    await flushPromises()

    const iframe = wrapper.find('iframe.rf-iframe')
    expect(iframe.exists()).toBe(true)
    expect(iframe.attributes('src')).toBe('/api/v1/executions/exec-1/rf-report/report.html')
    expect(wrapper.find('[data-testid="rf-report-missing"]').exists()).toBe(false)
  })
})
