import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ExecutionProgress from '../../src/components/ExecutionProgress/index.vue'
import * as executionApiModule from '../../src/services/executionApi'
import { useAuthStore } from '../../src/stores/authStore'

vi.mock('../../src/services/executionApi', () => ({
  streamExecution: vi.fn(),
  cancelExecution: vi.fn(),
  isTerminalEvent: (data: any) =>
    ['execution_completed', 'execution_error', 'execution_interrupted', 'execution_cancelled'].includes(data?.event),
}))

describe('ExecutionProgress', () => {
  let push: (data: unknown) => void

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    vi.mocked(executionApiModule.streamExecution).mockImplementation((_id, onEvent) => {
      push = onEvent
      return { close: vi.fn() } as any
    })
  })

  function mountAs(role: string) {
    useAuthStore().role = role
    return mount(ExecutionProgress, { props: { executionId: 'exec-1' } })
  }

  it('shows the queue position and a cancel button while pending', async () => {
    const wrapper = mountAs('editor')
    push({ event: 'execution_started', status: 'pending', total_cases: 1 })
    push({ event: 'execution_queued', status: 'pending', ahead: 2 })
    await flushPromises()

    expect(wrapper.find('[data-testid="queue-notice"]').text()).toContain('前面還有 2 筆')
    expect(wrapper.find('.status-badge').text()).toBe('排隊中')
    expect(wrapper.find('[data-testid="cancel-execution"]').exists()).toBe(true)
  })

  it('hides the cancel button from viewers', async () => {
    const wrapper = mountAs('viewer')
    push({ event: 'execution_queued', status: 'pending', ahead: 0 })
    await flushPromises()

    expect(wrapper.find('[data-testid="queue-notice"]').text()).toContain('下一個就輪到')
    expect(wrapper.find('[data-testid="cancel-execution"]').exists()).toBe(false)
  })

  it('cancels, then emits completed when the cancelled event arrives', async () => {
    vi.mocked(executionApiModule.cancelExecution).mockResolvedValue({} as any)
    const wrapper = mountAs('editor')
    push({ event: 'execution_queued', status: 'pending', ahead: 1 })
    await flushPromises()

    await wrapper.find('[data-testid="cancel-execution"]').trigger('click')
    expect(executionApiModule.cancelExecution).toHaveBeenCalledWith('exec-1')

    push({ event: 'execution_cancelled', status: 'cancelled', message: '已取消排隊' })
    await flushPromises()
    expect(wrapper.find('[data-testid="queue-notice"]').exists()).toBe(false)
    expect(wrapper.emitted('completed')).toHaveLength(1)
  })

  it('ignores a 409 when the run already started', async () => {
    vi.mocked(executionApiModule.cancelExecution).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mountAs('editor')
    push({ event: 'execution_queued', status: 'pending', ahead: 0 })
    await flushPromises()

    await wrapper.find('[data-testid="cancel-execution"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('.error-message').exists()).toBe(false)
  })

  it('stays on the page when the stream connection fails', async () => {
    const wrapper = mountAs('editor')
    push({ event: 'execution_error', message: 'SSE connection failed' })
    await flushPromises()

    expect(wrapper.emitted('completed')).toBeUndefined()
    expect(wrapper.find('.error-message').text()).toContain('SSE connection failed')
  })
})
