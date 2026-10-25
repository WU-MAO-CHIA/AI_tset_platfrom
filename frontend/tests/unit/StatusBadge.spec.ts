import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBadge from '../../src/components/StatusBadge/index.vue'

describe('StatusBadge', () => {
  it('maps execution statuses to tone and label', () => {
    expect(mount(StatusBadge, { props: { status: 'passed' } }).classes()).toContain('badge-pass')
    const failed = mount(StatusBadge, { props: { status: 'failed' } })
    expect(failed.classes()).toContain('badge-fail')
    expect(failed.text()).toBe('失敗')
    expect(mount(StatusBadge, { props: { status: 'pending' } }).text()).toBe('排隊中')
  })

  it('shows 未執行 when there is no status and falls back to the raw value', () => {
    expect(mount(StatusBadge, { props: { status: null } }).text()).toBe('未執行')
    expect(mount(StatusBadge, { props: { status: 'weird' } }).text()).toBe('weird')
  })

  it('prefers an explicit label', () => {
    expect(mount(StatusBadge, { props: { status: 'failed', label: '3 個失敗' } }).text()).toBe('3 個失敗')
  })
})
