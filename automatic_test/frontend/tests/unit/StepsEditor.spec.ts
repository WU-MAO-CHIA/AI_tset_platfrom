import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import StepsEditor from '../../src/components/StepsEditor/index.vue'
import * as caseApiModule from '../../src/services/caseApi'

vi.mock('../../src/services/caseApi', () => ({
  caseApi: {
    aiCompletePreview: vi.fn(),
  },
}))

vi.mock('../../src/components/LLMModelSelector/index.vue', () => ({
  default: { template: '<div class="llm-stub" />' },
}))

describe('StepsEditor', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders main steps textarea', () => {
    const wrapper = mount(StepsEditor, {
      props: { mainSteps: '', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('AI complete button is disabled when mainSteps is empty', () => {
    const wrapper = mount(StepsEditor, {
      props: { mainSteps: '', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    const btn = wrapper.find('button[data-testid="ai-complete-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('AI complete button is enabled when mainSteps has content', () => {
    const wrapper = mount(StepsEditor, {
      props: { mainSteps: '1. 開啟頁面', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    const btn = wrapper.find('button[data-testid="ai-complete-btn"]')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('calls aiCompletePreview and emits update:mainSteps on AI complete', async () => {
    vi.mocked(caseApiModule.caseApi.aiCompletePreview).mockResolvedValue({
      data: { completed_steps: '1. 步驟一\n2. 步驟二', model_used: 'claude' },
    } as any)

    const wrapper = mount(StepsEditor, {
      props: { mainSteps: '1. 開啟頁面', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('button[data-testid="ai-complete-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(caseApiModule.caseApi.aiCompletePreview).toHaveBeenCalledWith({
      partial_steps: '1. 開啟頁面',
      llm_model: 'claude-3-5-sonnet-20241022',
      description: '',
    })
    const emitted = wrapper.emitted('update:mainSteps')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('1. 步驟一\n2. 步驟二')
  })

  it('emits update:mainSteps when textarea value changes', async () => {
    const wrapper = mount(StepsEditor, {
      props: { mainSteps: '', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('新步驟')
    const emitted = wrapper.emitted('update:mainSteps')
    expect(emitted).toBeTruthy()
  })
})
