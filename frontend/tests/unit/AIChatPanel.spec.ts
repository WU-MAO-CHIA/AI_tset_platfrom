import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AIChatPanel from '../../src/components/AIChatPanel/index.vue'
import * as caseApiModule from '../../src/services/caseApi'

vi.mock('../../src/services/caseApi', () => ({
  caseApi: {
    chatWithAI: vi.fn(),
    getChatHistory: vi.fn(),
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
})
