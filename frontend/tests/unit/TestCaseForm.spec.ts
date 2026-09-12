import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import TestCaseForm from '@/components/TestCaseForm/index.vue'

vi.mock('@/services/caseApi', () => ({
  caseApi: {
    createCase: vi.fn().mockResolvedValue({ data: { id: 'case-1', case_number: 'TC-001', version: 1, created_at: '2026-01-01' } }),
    updateCase: vi.fn().mockResolvedValue({ data: {} }),
    getRobotScript: vi.fn().mockResolvedValue({ data: { rf_code: '*** Test ***\nLog    Hello', case_number: 'TC-001' } }),
    uploadRobotScript: vi.fn().mockResolvedValue({ data: { rf_code: '*** Uploaded ***\nLog    World', case_number: 'TC-001', file_path: '/tmp/TC-001.robot', size_bytes: 100, encoding: 'utf-8' } }),
    aiComplete: vi.fn().mockResolvedValue({ data: { completed_steps: 'AI filled steps', model_used: 'claude' } }),
    aiCompletePreview: vi.fn().mockResolvedValue({ data: { completed_steps: 'AI filled steps', model_used: 'claude' } }),
    trialRun: vi.fn().mockResolvedValue({ data: { execution_id: 'exec-1', stream_url: '/stream' } }),
    listCategories: vi.fn().mockResolvedValue({ data: { items: ['web', 'api'] } }),
  },
}))

import { caseApi } from '@/services/caseApi'

const globalStubs = {
  stubs: {
    MediaUploader: { template: '<div class="media-uploader" />', props: ['caseId'], emits: ['uploaded'] },
    LLMModelSelector: { template: '<div class="llm-selector" />', props: ['modelValue'], emits: ['update:modelValue'] },
    RFCodePreview: { template: '<div class="rf-preview" data-testid="rf-preview"><slot/></div>', props: ['mainSteps', 'selectedModel', 'rfCodeOverride', 'caseId', 'chatMode'], emits: ['trial-started'] },
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

  it('should not show AI complete button (moved to AIChatPanel)', () => {
    // Phase 12: AI completion moved to AIChatPanel in Tab 2; TestCaseForm only has basic fields
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    const btn = wrapper.findAll('button').find(b => b.text().includes('AI 補齊步驟'))
    expect(btn).toBeUndefined()
  })

  it('should have submit and trial-run buttons only', async () => {
    const wrapper = mount(TestCaseForm, {
      props: { caseId: 'case-abc' },
      global: globalStubs,
    })
    const buttons = wrapper.findAll('button')
    const texts = buttons.map(b => b.text())
    expect(texts.some(t => t.includes('儲存'))).toBe(true)
    expect(texts.some(t => t.includes('試跑'))).toBe(true)
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

  it('should not show LLM model selector (moved to AIChatPanel)', () => {
    // Phase 12: LLMModelSelector moved to AIChatPanel in Tab 2
    const wrapper = mount(TestCaseForm, { global: globalStubs })
    expect(wrapper.find('.llm-selector').exists()).toBe(false)
  })
})

describe('TestCaseForm RF code upload integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should show RFCodeUpload component in create mode', () => {
    const wrapper = mount(TestCaseForm, {
      props: { selectedModel: 'claude-sonnet-4-6' },
      global: globalStubs,
    })
    expect(wrapper.find('[data-testid="rf-upload"]').exists()).toBe(true)
  })

  it('should show RFCodePreview with existing RF code when editing', async () => {
    const wrapper = mount(TestCaseForm, {
      props: { caseId: 'case-1', initialData: { main_steps: 'steps' }, selectedModel: 'claude-sonnet-4-6' },
      global: globalStubs,
    })
    await flushPromises()
    expect(wrapper.find('[data-testid="rf-preview"]').exists()).toBe(true)
    expect(caseApi.getRobotScript).toHaveBeenCalledWith('case-1')
  })

  it('should upload pending RF code after case creation', async () => {
    const wrapper = mount(TestCaseForm, {
      props: { selectedModel: 'claude-sonnet-4-6' },
      global: globalStubs,
    })

    // Simulate file loaded event
    const rfUpload = wrapper.findComponent({ name: 'RFCodeUpload' })
    rfUpload.vm.$emit('file-loaded', '*** Test ***\nLog    Uploaded')

    await wrapper.find('button[type="submit"]').trigger('click')
    await flushPromises()

    expect(caseApi.createCase).toHaveBeenCalled()
    expect(caseApi.uploadRobotScript).toHaveBeenCalled()
  })

  it('should upload pending RF code after case update', async () => {
    const wrapper = mount(TestCaseForm, {
      props: { caseId: 'case-1', initialData: { main_steps: 'steps' }, selectedModel: 'claude-sonnet-4-6' },
      global: globalStubs,
    })
    await flushPromises()

    // Simulate file loaded event
    const rfUpload = wrapper.findComponent({ name: 'RFCodeUpload' })
    rfUpload.vm.$emit('file-loaded', '*** Test ***\nLog    Uploaded')

    await wrapper.find('button[type="submit"]').trigger('click')
    await flushPromises()

    expect(caseApi.updateCase).toHaveBeenCalled()
    expect(caseApi.uploadRobotScript).toHaveBeenCalledWith('case-1', expect.any(File))
  })

  it('should clear RF code when file-cleared emitted', async () => {
    const wrapper = mount(TestCaseForm, {
      props: { selectedModel: 'claude-sonnet-4-6' },
      global: globalStubs,
    })

    const rfUpload = wrapper.findComponent({ name: 'RFCodeUpload' })
    rfUpload.vm.$emit('file-loaded', '*** Test ***\nLog    Hello')
    rfUpload.vm.$emit('file-cleared')

    await flushPromises()
    // RFCodePreview should not be shown when cleared
    expect(wrapper.find('[data-testid="rf-preview"]').exists()).toBe(false)
  })
})
