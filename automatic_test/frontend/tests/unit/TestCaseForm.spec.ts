import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import TestCaseForm from '@/components/TestCaseForm/index.vue'

vi.mock('@/services/caseApi', () => ({
  caseApi: {
    createCase: vi.fn().mockResolvedValue({ data: { id: 'case-1', case_number: 'TC-001', version: 1, created_at: '2026-01-01' } }),
    updateCase: vi.fn().mockResolvedValue({ data: {} }),
    aiComplete: vi.fn().mockResolvedValue({ data: { completed_steps: 'AI filled steps', model_used: 'claude' } }),
    aiCompletePreview: vi.fn().mockResolvedValue({ data: { completed_steps: 'AI filled steps', model_used: 'claude' } }),
    trialRun: vi.fn().mockResolvedValue({ data: { execution_id: 'exec-1', stream_url: '/stream' } }),
  },
}))

import { caseApi } from '@/services/caseApi'

const globalStubs = {
  stubs: {
    MediaUploader: { template: '<div class="media-uploader" />', props: ['caseId'], emits: ['uploaded'] },
    LLMModelSelector: { template: '<div class="llm-selector" />', props: ['modelValue'], emits: ['update:modelValue'] },
  },
}

describe('TestCaseForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should require case_number field', () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    const input = wrapper.find('input[placeholder="TC-001"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('required')).toBeDefined()
  })

  it('should require main_steps field', () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    const textarea = wrapper.find('textarea[required]')
    expect(textarea.exists()).toBe(true)
  })

  it('should show AI complete button', () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    const btn = wrapper.findAll('button').find(b => b.text().includes('AI 補齊步驟'))
    expect(btn).toBeDefined()
  })

  it('should trigger AI completion when AI button clicked', async () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })

    await wrapper.find('textarea[required]').setValue('1. Open login page')
    const btn = wrapper.findAll('button').find(b => b.text().includes('AI 補齊步驟'))!
    expect(btn.attributes('disabled')).toBeUndefined()

    await btn.trigger('click')
    await flushPromises()

    // No caseId prop → should call aiCompletePreview
    expect(caseApi.aiCompletePreview).toHaveBeenCalledWith(
      expect.objectContaining({ partial_steps: '1. Open login page' }),
    )
  })

  it('should show media upload section', () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    expect(wrapper.find('.media-uploader').exists()).toBe(true)
  })

  it('should show trial run button after case is saved', () => {
    const wrapper = mount(TestCaseForm, {
      props: { caseId: 'case-abc' },
      global: globalStubs,
    })
    const btn = wrapper.findAll('button').find(b => b.text().includes('立即試跑'))
    expect(btn).toBeDefined()
    expect(btn!.exists()).toBe(true)
  })
})

describe('TestCaseForm validation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should validate required fields before submit', () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    // Both required fields must carry the required attribute for HTML5 validation
    expect(wrapper.find('input[placeholder="TC-001"]').attributes('required')).toBeDefined()
    expect(wrapper.find('textarea[required]').exists()).toBe(true)
    // Submit button present and not disabled by default
    const submitBtn = wrapper.find('button[type="submit"]')
    expect(submitBtn.exists()).toBe(true)
  })

  it('should show LLM model selector', () => {
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    expect(wrapper.find('.llm-selector').exists()).toBe(true)
  })
})
