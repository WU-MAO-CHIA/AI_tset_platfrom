import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CaseCreatePage from '../../src/pages/CaseCreatePage.vue'
import * as caseApiModule from '../../src/services/caseApi'

vi.mock('../../src/services/caseApi', () => ({
  caseApi: {
    saveRobotScript: vi.fn(),
  },
}))

vi.mock('../../src/services/apiClient', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { default: 'claude-sonnet-4-6' } }),
  },
}))

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: {} }),
  useRouter: () => ({ push: pushMock }),
}))

let pendingRf: string | null = null

const FormStub = {
  name: 'TestCaseFormStub',
  template: '<div class="form-stub" />',
  emits: ['saved'],
  setup() {
    const takePendingRfCode = () => pendingRf
    return { takePendingRfCode }
  },
}

function mountPage() {
  return mount(CaseCreatePage, {
    global: {
      stubs: {
        TestCaseForm: FormStub,
        AIChatPanel: { name: 'AIChatPanelStub', template: '<div />' },
        RFCodePreview: { name: 'RFCodePreviewStub', template: '<div />' },
      },
    },
  })
}

describe('CaseCreatePage RF persistence on save', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    pendingRf = null
    pushMock.mockClear()
  })

  it('saves AI-generated RF code after case creation, then navigates', async () => {
    vi.mocked(caseApiModule.caseApi.saveRobotScript).mockResolvedValue({
      data: { case_number: 'TC-001', file_path: '/tmp/TC-001.robot' },
    } as any)

    const wrapper = mountPage()
    await flushPromises()

    // Simulate AI chat producing code on Tab 2
    const chat = wrapper.findComponent({ name: 'AIChatPanelStub' })
    chat.vm.$emit('rf-updated', '*** AI CODE ***')
    await flushPromises()

    // Simulate Tab 1 form finishing creation
    wrapper.findComponent(FormStub).vm.$emit('saved', 'new-case-id')
    await flushPromises()

    expect(caseApiModule.caseApi.saveRobotScript).toHaveBeenCalledWith('new-case-id', '*** AI CODE ***')
    expect(pushMock).toHaveBeenCalledWith('/cases/new-case-id')
  })

  it('uploaded file content takes precedence over AI code', async () => {
    pendingRf = '*** UPLOADED ***'
    vi.mocked(caseApiModule.caseApi.saveRobotScript).mockResolvedValue({
      data: { case_number: 'TC-001', file_path: '/tmp/TC-001.robot' },
    } as any)

    const wrapper = mountPage()
    await flushPromises()
    const chat = wrapper.findComponent({ name: 'AIChatPanelStub' })
    chat.vm.$emit('rf-updated', '*** AI CODE ***')
    await flushPromises()

    wrapper.findComponent(FormStub).vm.$emit('saved', 'new-case-id')
    await flushPromises()

    expect(caseApiModule.caseApi.saveRobotScript).toHaveBeenCalledWith('new-case-id', '*** UPLOADED ***')
  })

  it('navigates directly when there is no RF code', async () => {
    const wrapper = mountPage()
    await flushPromises()

    wrapper.findComponent(FormStub).vm.$emit('saved', 'new-case-id')
    await flushPromises()

    expect(caseApiModule.caseApi.saveRobotScript).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith('/cases/new-case-id')
  })

  it('stays on page with error when RF save fails', async () => {
    vi.mocked(caseApiModule.caseApi.saveRobotScript).mockRejectedValue(new Error('boom'))

    const wrapper = mountPage()
    await flushPromises()
    const chat = wrapper.findComponent({ name: 'AIChatPanelStub' })
    chat.vm.$emit('rf-updated', '*** AI CODE ***')
    await flushPromises()

    wrapper.findComponent(FormStub).vm.$emit('saved', 'new-case-id')
    await flushPromises()

    expect(pushMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('RF 程式碼儲存失敗')
  })
})
