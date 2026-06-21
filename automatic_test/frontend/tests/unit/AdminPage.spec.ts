import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AdminPage from '../../src/pages/AdminPage.vue'
import * as adminApi from '../../src/services/adminApi'

vi.mock('../../src/services/adminApi', () => ({
  listUsers: vi.fn().mockResolvedValue([]),
  listSystemCategories: vi.fn().mockResolvedValue([]),
  getLlmKeyStatus: vi.fn().mockResolvedValue({
    anthropic_key_set: true,
    anthropic_key_masked: 'sk-ant-****…dF3a',
    openai_key_set: false,
    openai_key_masked: '',
  }),
  setLlmKey: vi.fn().mockResolvedValue(undefined),
  getDefaultModel: vi.fn().mockResolvedValue({ model: 'claude-sonnet-4-6' }),
  setDefaultModel: vi.fn().mockResolvedValue(undefined),
  getLlmModels: vi.fn().mockResolvedValue({
    models: [
      { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', provider: 'anthropic' },
      { id: 'claude-opus-4-7', name: 'Claude Opus 4.7', provider: 'anthropic' },
    ],
    default: 'claude-sonnet-4-6',
  }),
}))

describe('AdminPage — LLM 分頁（遮罩 + 全域預設模型）', () => {
  beforeEach(() => vi.clearAllMocks())

  async function mountLlmTab() {
    const wrapper = mount(AdminPage)
    await flushPromises()
    const llmTab = wrapper.findAll('.tab-btn').find((b) => b.text().includes('LLM'))
    await llmTab!.trigger('click')
    await flushPromises()
    return wrapper
  }

  it('已設定的 key 顯示遮罩值', async () => {
    const wrapper = await mountLlmTab()
    expect(wrapper.text()).toContain('sk-ant-****…dF3a')
  })

  it('未設定的 provider 顯示「未設定」', async () => {
    const wrapper = await mountLlmTab()
    expect(wrapper.text()).toContain('未設定')
  })

  it('變更全域預設模型下拉後呼叫 setDefaultModel', async () => {
    const wrapper = await mountLlmTab()
    const select = wrapper.find('[data-testid="default-model-select"]')
    expect(select.exists()).toBe(true)
    await select.setValue('claude-opus-4-7')
    await flushPromises()
    expect(adminApi.setDefaultModel).toHaveBeenCalledWith('claude-opus-4-7')
  })
})
