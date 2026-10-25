import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RunnerEnvironmentsPage from '../../src/pages/RunnerEnvironmentsPage.vue'
import * as api from '../../src/services/runnerEnvironmentApi'
import { confirmAction } from '../../src/composables/useConfirm'

vi.mock('../../src/services/runnerEnvironmentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof api>()
  return {
    ...actual,
    listEnvironments: vi.fn(),
    createEnvironment: vi.fn(),
    updateEnvironment: vi.fn(),
    deleteEnvironment: vi.fn(),
    checkEnvironment: vi.fn(),
  }
})
vi.mock('../../src/composables/useConfirm', () => ({ confirmAction: vi.fn() }))

function env(overrides: Partial<api.RunnerEnvironment> = {}): api.RunnerEnvironment {
  return {
    id: 'env-1', name: 'Windows 測試機 A', kind: 'windows', enabled: true, is_builtin: false,
    url: 'http://10.0.0.5:9000', status: 'online', checked_at: null, ...overrides,
  }
}

const BUILTIN = env({ id: 'builtin-linux', name: '預設容器', kind: 'linux', is_builtin: true, url: null, status: 'local' })

async function mountPage() {
  const wrapper = mount(RunnerEnvironmentsPage, { attachTo: document.body })
  await flushPromises()
  return wrapper
}

describe('RunnerEnvironmentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listEnvironments).mockResolvedValue([BUILTIN, env(), env({ id: 'env-2', name: '離線機', status: 'offline' })])
  })

  it('lists environments with their status and hides actions for the builtin one', async () => {
    const wrapper = await mountPage()
    const text = wrapper.text()
    expect(text).toContain('預設容器')
    expect(text).toContain('Windows 測試機 A')
    expect(wrapper.find('[data-testid="status-env-1"]').text()).toBe('已連線')
    expect(wrapper.find('[data-testid="status-env-2"]').text()).toBe('未連線')
    expect(wrapper.find('[data-testid="btn-edit-builtin-linux"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="btn-delete-builtin-linux"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="btn-edit-env-1"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('creates an environment', async () => {
    vi.mocked(api.createEnvironment).mockResolvedValue(env({ id: 'env-3', name: '新機器', kind: 'linux' }))
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="btn-add"]').trigger('click')
    await flushPromises()
    const dialog = document.body
    const setValue = async (testid: string, value: string) => {
      const input = dialog.querySelector(`[data-testid="${testid}"] input, input[data-testid="${testid}"]`) as HTMLInputElement
      input.value = value
      input.dispatchEvent(new Event('input'))
      await flushPromises()
    }
    await setValue('input-name', '新機器')
    await setValue('input-url', 'http://10.0.0.6:9000')
    await setValue('input-token', 'x'.repeat(40))
    ;(dialog.querySelector('[data-testid="btn-save"]') as HTMLButtonElement).click()
    await flushPromises()

    expect(api.createEnvironment).toHaveBeenCalledWith({
      name: '新機器', kind: 'linux', url: 'http://10.0.0.6:9000', token: 'x'.repeat(40), enabled: true,
    })
    expect(wrapper.text()).toContain('新機器')
    wrapper.unmount()
  })

  it('requires a token when creating', async () => {
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="btn-add"]').trigger('click')
    await flushPromises()
    ;(document.body.querySelector('[data-testid="btn-save"]') as HTMLButtonElement).click()
    await flushPromises()
    expect(api.createEnvironment).not.toHaveBeenCalled()
    expect(document.body.querySelector('[data-testid="form-error"]')?.textContent).toContain('token')
    wrapper.unmount()
  })

  it('deletes after confirmation', async () => {
    vi.mocked(confirmAction).mockResolvedValue(true)
    vi.mocked(api.deleteEnvironment).mockResolvedValue()
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="btn-delete-env-1"]').trigger('click')
    await flushPromises()
    expect(confirmAction).toHaveBeenCalledWith(expect.objectContaining({ message: expect.stringContaining('重新選擇') }))
    expect(api.deleteEnvironment).toHaveBeenCalledWith('env-1')
    expect(wrapper.text()).not.toContain('Windows 測試機 A')
    wrapper.unmount()
  })

  it('re-checks an environment', async () => {
    vi.mocked(api.checkEnvironment).mockResolvedValue(env({ id: 'env-2', name: '離線機', status: 'online' }))
    const wrapper = await mountPage()
    await wrapper.find('[data-testid="btn-check-env-2"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="status-env-2"]').text()).toBe('已連線')
    wrapper.unmount()
  })
})
