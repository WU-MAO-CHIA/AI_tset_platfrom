import { describe, it, expect } from 'vitest'
import { isTerminalEvent } from '../../src/services/executionApi'

describe('isTerminalEvent', () => {
  it.each(['execution_completed', 'execution_error', 'execution_interrupted', 'execution_cancelled'])('%s ends the stream', (event) => {
    expect(isTerminalEvent({ event })).toBe(true)
  })

  it.each(['execution_started', 'execution_queued', 'case_started', 'case_completed', 'pabot_started'])('%s does not', (event) => {
    expect(isTerminalEvent({ event })).toBe(false)
  })

  it('handles malformed data', () => {
    expect(isTerminalEvent(null)).toBe(false)
    expect(isTerminalEvent({})).toBe(false)
  })
})
