import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AIChatPanel from '../../src/components/AIChatPanel/index.vue'
import * as caseApiModule from '../../src/services/caseApi'

vi.mock('../../src/services/caseApi', () => ({
  caseApi: {
    chatWithAI: vi.fn(),
    chatPreview: vi.fn(),
    getChatHistory: vi.fn(),
    getRobotScript: vi.fn(),
  },
}))

describe('AIChatPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders chat input textarea', () => {
    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('send button is disabled when input is empty', () => {
    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    const btn = wrapper.find('button[data-testid="send-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('send button is enabled when input has content', async () => {
    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('請生成測試步驟')
    const btn = wrapper.find('button[data-testid="send-btn"]')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('calls chatWithAI and displays assistant bubble on send', async () => {
    vi.mocked(caseApiModule.caseApi.chatWithAI).mockResolvedValue({
      data: { assistant_message: 'AI 回應內容', rf_code: '*** Test Cases ***' },
    } as any)

    const wrapper = mount(AIChatPanel, {
      props: { caseId: 'test-case-id', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('測試訊息')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(caseApiModule.caseApi.chatWithAI).toHaveBeenCalledWith(
      'test-case-id',
      '測試訊息',
      'claude-3-5-sonnet-20241022',
      'full',
      undefined,
    )
  })

  it('emits rf-updated event after AI responds', async () => {
    vi.mocked(caseApiModule.caseApi.chatWithAI).mockResolvedValue({
      data: { assistant_message: 'AI 回應', rf_code: '*** Test Cases ***\nLogin Test' },
    } as any)

    const wrapper = mount(AIChatPanel, {
      props: { caseId: 'test-case-id', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('測試')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    const emitted = wrapper.emitted('rf-updated')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('*** Test Cases ***\nLogin Test')
  })

  it('loads chat history when caseId is provided', async () => {
    vi.mocked(caseApiModule.caseApi.getChatHistory).mockResolvedValue({
      data: {
        messages: [
          { role: 'user', content: '舊訊息', created_at: '2026-01-01T00:00:00Z' },
          { role: 'assistant', content: 'AI 舊回應', created_at: '2026-01-01T00:00:01Z' },
        ],
      },
    } as any)

    mount(AIChatPanel, {
      props: { caseId: 'existing-case-id', selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await new Promise((r) => setTimeout(r, 0))

    expect(caseApiModule.caseApi.getChatHistory).toHaveBeenCalledWith('existing-case-id')
  })

  it('uses chatPreview with local history when no caseId (creation page)', async () => {
    vi.mocked(caseApiModule.caseApi.chatPreview).mockResolvedValue({
      data: { assistant_message: 'AI 回應', rf_code: '*** Test ***' },
    } as any)

    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('第一則')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.find('textarea').setValue('第二則')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(caseApiModule.caseApi.chatWithAI).not.toHaveBeenCalled()
    expect(caseApiModule.caseApi.getChatHistory).not.toHaveBeenCalled()
    const lastCall = vi.mocked(caseApiModule.caseApi.chatPreview).mock.calls.at(-1)![0]
    expect(lastCall.message).toBe('第二則')
    expect(lastCall.history!.length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('AI 回應')
  })

  it('does not duplicate the current message in stateless history', async () => {
    vi.mocked(caseApiModule.caseApi.chatPreview).mockResolvedValue({
      data: { assistant_message: 'AI 回應', rf_code: '' },
    } as any)

    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('唯一訊息')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    const lastCall = vi.mocked(caseApiModule.caseApi.chatPreview).mock.calls.at(-1)![0]
    // History must be empty: the current turn travels in `message`, not `history`
    expect(lastCall.history).toEqual([])
  })

  it('sends rfCodeContext as rf_code in stateless chat', async () => {
    vi.mocked(caseApiModule.caseApi.chatPreview).mockResolvedValue({
      data: { assistant_message: 'AI 回應', rf_code: '' },
    } as any)

    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022', rfCodeContext: '*** Test ***' },
    })
    await wrapper.find('textarea').setValue('解釋這段代碼')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    const lastCall = vi.mocked(caseApiModule.caseApi.chatPreview).mock.calls.at(-1)![0]
    expect(lastCall.rf_code).toBe('*** Test ***')
  })

  it('shows backend error detail on failure', async () => {
    vi.mocked(caseApiModule.caseApi.chatPreview).mockRejectedValue(new Error('案例不存在'))

    const wrapper = mount(AIChatPanel, {
      props: { selectedModel: 'claude-3-5-sonnet-20241022' },
    })
    await wrapper.find('textarea').setValue('測試')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('案例不存在')
  })

  it('passes elementCatalog to chatWithAI when provided', async () => {
    vi.mocked(caseApiModule.caseApi.chatWithAI).mockResolvedValue({
      data: { assistant_message: 'AI 回應', rf_code: '' },
    } as any)
    const catalog = [{ goal: '登入按鈕', recommended: 'role=button[name="登入"]', xpath: '//button[1]', css: 'button', status: 'found' }]

    const wrapper = mount(AIChatPanel, {
      props: { caseId: 'test-case-id', selectedModel: 'claude-3-5-sonnet-20241022', elementCatalog: catalog },
    })
    await wrapper.find('textarea').setValue('用真實定位器生成')
    await wrapper.find('button[data-testid="send-btn"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(caseApiModule.caseApi.chatWithAI).toHaveBeenCalledWith(
      'test-case-id',
      '用真實定位器生成',
      'claude-3-5-sonnet-20241022',
      'full',
      catalog,
    )
  })
})
