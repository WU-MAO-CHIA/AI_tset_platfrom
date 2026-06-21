import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AdminPage from '../../src/pages/AdminPage.vue'

vi.mock('../../src/services/adminApi', () => ({
  listUsers: vi.fn().mockResolvedValue([]),
  listSystemCategories: vi.fn().mockResolvedValue([]),
  getLlmKeyStatus: vi.fn().mockResolvedValue({
    anthropic_key_set: true,
    anthropic_key_masked: 'sk-ant-****…dF3a',
    openai_key_set: false,
    openai_key_masked: '',
  }),
  getDefaultModel: vi.fn().mockResolvedValue({ model: 'claude-sonnet-4-6' }),
}))

describe('AdminPage — LLM 設定（唯讀，來源 .env）', () => {
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

  it('唯讀顯示全域預設模型，且無編輯下拉', async () => {
    const wrapper = await mountLlmTab()
    const model = wrapper.find('[data-testid="default-model"]')
    expect(model.exists()).toBe(true)
    expect(model.text()).toContain('claude-sonnet-4-6')
    // env-only：不應有可編輯的模型下拉
    expect(wrapper.find('[data-testid="default-model-select"]').exists()).toBe(false)
  })
})
