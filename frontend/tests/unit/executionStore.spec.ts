import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useExecutionStore } from '../../src/stores/executionStore'

describe('executionStore queue states', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows pending with the queue position, then running once a case starts', () => {
    const store = useExecutionStore()
    store.startExecution('exec-1')

    store.handleSSEEvent({ event: 'execution_started', status: 'pending', total_cases: 2 })
    expect(store.executionStatus).toBe('pending')

    store.handleSSEEvent({ event: 'execution_queued', status: 'pending', ahead: 2 })
    expect(store.queueAhead).toBe(2)
    store.handleSSEEvent({ event: 'execution_queued', status: 'pending', ahead: 0 })
    expect(store.queueAhead).toBe(0)

    store.handleSSEEvent({ event: 'case_started', case_number: 'TC-1' })
    expect(store.executionStatus).toBe('running')
    expect(store.queueAhead).toBeNull()
  })

  it('treats pabot_started as running', () => {
    const store = useExecutionStore()
    store.startExecution('exec-1')
    store.handleSSEEvent({ event: 'execution_queued', ahead: 1 })

    store.handleSSEEvent({ event: 'pabot_started' })
    expect(store.executionStatus).toBe('running')
    expect(store.queueAhead).toBeNull()
  })

  it('handles execution_cancelled', () => {
    const store = useExecutionStore()
    store.startExecution('exec-1')
    store.handleSSEEvent({ event: 'execution_queued', ahead: 1 })

    store.handleSSEEvent({ event: 'execution_cancelled', status: 'cancelled', message: '已取消排隊' })
    expect(store.executionStatus).toBe('cancelled')
    expect(store.errorMessage).toBe('已取消排隊')
    expect(store.queueAhead).toBeNull()
  })

  it('keeps cancelled status from a synthetic completion', () => {
    const store = useExecutionStore()
    store.startExecution('exec-1')

    store.handleSSEEvent({ event: 'execution_completed', status: 'cancelled', passed: 0, failed: 0, total: 1 })
    expect(store.executionStatus).toBe('cancelled')
  })
})
