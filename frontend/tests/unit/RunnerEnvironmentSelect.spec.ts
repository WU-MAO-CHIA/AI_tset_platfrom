import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RunnerEnvironmentSelect from '../../src/components/RunnerEnvironmentSelect/index.vue'
import type { RunnerEnvironment } from '../../src/services/runnerEnvironmentApi'

function env(id: string, kind: 'linux' | 'windows', enabled = true): RunnerEnvironment {
  return { id, name: id, kind, enabled, is_builtin: false, url: null, status: 'online', checked_at: null }
}

const ENVS = [env('builtin-linux', 'linux'), env('linux-2', 'linux'), env('win-1', 'windows'), env('win-off', 'windows', false)]

describe('RunnerEnvironmentSelect', () => {
  it('lists only enabled environments of the requested kind', () => {
    const wrapper = mount(RunnerEnvironmentSelect, { props: { modelValue: null, environments: ENVS, kind: 'windows' } })
    const values = wrapper.findAllComponents({ name: 'ElOption' }).map((o) => o.props('value'))
    expect(values).toEqual(['win-1'])
  })

  it('maps the default option to null', async () => {
    const wrapper = mount(RunnerEnvironmentSelect, {
      props: { modelValue: 'linux-2', environments: ENVS, kind: 'linux', defaultLabel: '依各案例設定' },
    })
    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', '')
    select.vm.$emit('update:modelValue', 'builtin-linux')
    expect(wrapper.emitted('update:modelValue')).toEqual([[null], ['builtin-linux']])
  })
})
