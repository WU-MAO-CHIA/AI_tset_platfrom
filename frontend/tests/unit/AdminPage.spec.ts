import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AdminPage from '../../src/pages/AdminPage.vue'

const setActiveModel = vi.fn().mockResolvedValue(undefined)

vi.mock('../../src/services/adminApi', () => ({
  listUsers: vi.fn().mockResolvedValue([]),
  listSystemCategories: vi.fn().mockResolvedValue([]),
  getLlmKeyStatus: vi.fn().mockResolvedValue({
    anthropic_key_set: true,
    anthropic_key_masked: 'sk-ant-****…dF3a',
    openai_key_set: false,
    openai_key_masked: '',
    ollama_base_url: 'http://localhost:11434',
    ollama_configured: true,
  }),
  getActiveModel: vi.fn().mockResolvedValue({ model: 'claude-sonnet-4-6' }),
  setActiveModel: (...args: any[]) => setActiveModel(...args),
  getLlmModels: vi.fn().mockResolvedValue({
    models: [
      { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', provider: 'anthropic', requires_setup: false },
      { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', requires_setup: true },
      { id: 'ollama:gemma4:e4b', name: 'gemma4:e4b', provider: 'ollama', requires_setup: false },
    ],
    default: 'claude-sonnet-4-6',
  }),
}))

describe('AdminPage — LLM 設定（金鑰唯讀 + 啟用模型可切換）', () => {
  beforeEach(() => vi.clearAllMocks())

  async function mountLlmTab() {
    const wrapper = mount(AdminPage)
    await flushPromises()
    const llmTab = wrapper.findAll('.tab-btn').find((b) => b.text().includes('LLM'))
    await llmTab!.trigger('click')
    await flushPromises()
    return wrapper
  }

  it('已設定的 key 顯示遮罩值（唯讀）', async () => {
    const wrapper = await mountLlmTab()
    expect(wrapper.text()).toContain('sk-ant-****…dF3a')
  })

  it('未設定的 provider 顯示「未設定」', async () => {
    const wrapper = await mountLlmTab()
    expect(wrapper.text()).toContain('未設定')
  })

  it('顯示「目前使用模型」下拉，僅含可用模型（requires_setup=false）', async () => {
    const wrapper = await mountLlmTab()
    const select = wrapper.find('[data-testid="active-model-select"]')
    expect(select.exists()).toBe(true)
    const optionValues = select.findAll('option').map((o) => o.element.value)
    expect(optionValues).toContain('claude-sonnet-4-6')
    expect(optionValues).toContain('ollama:gemma4:e4b')
    // requires_setup=true 的模型不應出現
    expect(optionValues).not.toContain('gpt-4o')
  })

  it('變更下拉即呼叫 setActiveModel', async () => {
    const wrapper = await mountLlmTab()
    const select = wrapper.find('[data-testid="active-model-select"]')
    await select.setValue('ollama:gemma4:e4b')
    await flushPromises()
    expect(setActiveModel).toHaveBeenCalledWith('ollama:gemma4:e4b')
  })
})
