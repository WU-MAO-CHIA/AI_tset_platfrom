import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RunStrip from '../../src/components/RunStrip/index.vue'
import type { RecentRun } from '../../src/services/checklistApi'

function run(id: string, status: string, failed = 0): RecentRun {
  return { id, status, passed_count: 3 - failed, failed_count: failed, total_count: 3, started_at: '2026-10-25T01:00:00' }
}

describe('RunStrip', () => {
  it('draws oldest to newest and pads missing slots on the left', () => {
    // API 回傳新到舊
    const wrapper = mount(RunStrip, { props: { runs: [run('c', 'completed'), run('b', 'completed', 1), run('a', 'failed')] } })
    const tones = wrapper.findAll('.cells i').map((i) => i.classes()[0])
    expect(tones).toHaveLength(10)
    expect(tones.slice(0, 7).every((t) => t === 'empty')).toBe(true)
    expect(tones.slice(7)).toEqual(['fail', 'fail', 'pass'])
    expect(wrapper.find('.rate').text()).toBe('1/3')
  })

  it('shows the running state and leaves active runs out of the pass rate', () => {
    const wrapper = mount(RunStrip, { props: { runs: [run('b', 'running'), run('a', 'completed')] } })
    expect(wrapper.findAll('.cells i').at(-1)!.classes()).toContain('running')
    expect(wrapper.find('.rate').text()).toBe('執行中')
    expect(wrapper.attributes('aria-label')).toBe('最近完成的 1 次執行中，1 次全部通過')
  })

  it('says when a checklist has never run', () => {
    const wrapper = mount(RunStrip, { props: { runs: [] } })
    expect(wrapper.text()).toContain('還沒執行過')
    expect(wrapper.findAll('.cells i.empty')).toHaveLength(10)
  })
})
