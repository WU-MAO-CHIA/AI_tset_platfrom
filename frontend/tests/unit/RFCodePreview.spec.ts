import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import RFCodePreview from '../../src/components/RFCodePreview/index.vue'
import * as caseApiModule from '../../src/services/caseApi'

vi.mock('../../src/services/caseApi', () => ({
  caseApi: {
    previewRfCode: vi.fn(),
    saveRobotScript: vi.fn(),
    getRobotScript: vi.fn(),
  },
}))

describe('RFCodePreview', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders translate button', () => {
    const wrapper = mount(RFCodePreview, {
      props: { mainSteps: '1. 步驟', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    expect(wrapper.find('button[data-testid="rf-translate-btn"]').exists()).toBe(true)
  })

  it('calls previewRfCode with correct payload on button click', async () => {
    vi.mocked(caseApiModule.caseApi.previewRfCode).mockResolvedValue({
      data: { rf_code: '*** Test Cases ***\nExample\n    Log  hello' },
    } as any)

    const wrapper = mount(RFCodePreview, {
      props: { mainSteps: '1. 開啟登入頁面', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('button[data-testid="rf-translate-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(caseApiModule.caseApi.previewRfCode).toHaveBeenCalledWith({
      main_steps: '1. 開啟登入頁面',
      llm_model: 'claude-3-5-sonnet-20241022',
    })
  })

  it('displays rf code in pre element after successful translation', async () => {
    vi.mocked(caseApiModule.caseApi.previewRfCode).mockResolvedValue({
      data: { rf_code: '*** Test Cases ***\nExample\n    Log  hello' },
    } as any)

    const wrapper = mount(RFCodePreview, {
      props: { mainSteps: '1. 步驟', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('button[data-testid="rf-translate-btn"]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('pre').text()).toContain('*** Test Cases ***')
  })

  it('shows error message on translation failure without clearing mainSteps', async () => {
    vi.mocked(caseApiModule.caseApi.previewRfCode).mockRejectedValue(new Error('LLM error'))

    const wrapper = mount(RFCodePreview, {
      props: { mainSteps: '1. 步驟', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('button[data-testid="rf-translate-btn"]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="rf-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="rf-error"]').text()).toContain('翻譯失敗')
  })

  it('shows loading state during translation', async () => {
    let resolve: (v: any) => void
    vi.mocked(caseApiModule.caseApi.previewRfCode).mockReturnValue(
      new Promise(r => { resolve = r })
    )

    const wrapper = mount(RFCodePreview, {
      props: { mainSteps: '1. 步驟', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('button[data-testid="rf-translate-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button[data-testid="rf-translate-btn"]').attributes('disabled')).toBeDefined()
    resolve!({ data: { rf_code: '' } })
  })

  it('renders save button when caseId and rfCode provided', () => {
    const wrapper = mount(RFCodePreview, {
      props: {
        mainSteps: '1. 步驟',
        selectedModel: 'claude-3-5-sonnet-20241022',
        caseId: 'case-1',
        rfCodeOverride: '*** Test ***\nLog    Hello',
        chatMode: false,
      },
    })
    expect(wrapper.find('button[data-testid="rf-save-btn"]').exists()).toBe(true)
  })

  it('calls saveRobotScript when save button clicked', async () => {
    vi.mocked(caseApiModule.caseApi.saveRobotScript).mockResolvedValue({
      data: { case_number: 'TC-001', file_path: '/tmp/TC-001.robot' },
    } as any)

    const wrapper = mount(RFCodePreview, {
      props: {
        mainSteps: '1. 步驟',
        selectedModel: 'claude-3-5-sonnet-20241022',
        caseId: 'case-1',
        rfCodeOverride: '*** Test ***\nLog    Hello',
        chatMode: false,
      },
    })
    await wrapper.find('button[data-testid="rf-save-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(caseApiModule.caseApi.saveRobotScript).toHaveBeenCalledWith('case-1', '*** Test ***\nLog    Hello')
  })

  it('shows saved state after successful save', async () => {
    vi.mocked(caseApiModule.caseApi.saveRobotScript).mockResolvedValue({
      data: { case_number: 'TC-001', file_path: '/tmp/TC-001.robot' },
    } as any)

    const wrapper = mount(RFCodePreview, {
      props: {
        mainSteps: '1. 步驟',
        selectedModel: 'claude-3-5-sonnet-20241022',
        caseId: 'case-1',
        rfCodeOverride: '*** Test ***\nLog    Hello',
        chatMode: false,
      },
    })
    await wrapper.find('button[data-testid="rf-save-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button[data-testid="rf-save-btn"]').text()).toContain('已儲存')
  })

  it('shows trial run button in chat mode when rfCode available', () => {
    const wrapper = mount(RFCodePreview, {
      props: {
        mainSteps: '1. 步驟',
        selectedModel: 'claude-3-5-sonnet-20241022',
        caseId: 'case-1',
        rfCodeOverride: '*** Test ***\nLog    Hello',
        chatMode: true,
      },
    })
    expect(wrapper.find('button[data-testid="rf-trial-run-btn"]').exists()).toBe(true)
  })
})
