import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScheduleForm from '../../src/components/ScheduleForm/index.vue'

async function submit(wrapper: ReturnType<typeof mount>) {
  await wrapper.find('form').trigger('submit')
}

describe('ScheduleForm', () => {
  it('submits a daily schedule with defaults', async () => {
    const wrapper = mount(ScheduleForm)
    await wrapper.find('[data-testid="schedule-name"]').setValue('nightly')
    await submit(wrapper)

    expect(wrapper.emitted('submit')![0][0]).toEqual({
      name: 'nightly',
      enabled: true,
      frequency: 'daily',
      time_of_day: '02:00',
      weekdays: null,
      interval_minutes: null,
      parallel_mode: false,
      max_workers: 1,
    })
  })

  it('submits weekly days sorted and drops unused fields for interval', async () => {
    const wrapper = mount(ScheduleForm)
    await wrapper.find('[data-testid="schedule-name"]').setValue('weekly')
    await wrapper.find('[data-testid="schedule-frequency"]').setValue('weekly')
    const boxes = wrapper.findAll('[data-testid="schedule-weekdays"] input')
    await boxes[4].setValue(true)
    await submit(wrapper)
    expect((wrapper.emitted('submit')![0][0] as any).weekdays).toEqual([0, 4])

    await wrapper.find('[data-testid="schedule-frequency"]').setValue('interval')
    await wrapper.find('[data-testid="schedule-interval"]').setValue(30)
    await submit(wrapper)
    const payload = wrapper.emitted('submit')![1][0] as any
    expect(payload).toMatchObject({ frequency: 'interval', interval_minutes: 30, time_of_day: null, weekdays: null })
  })

  it('validates before emitting', async () => {
    const wrapper = mount(ScheduleForm)
    await submit(wrapper)
    expect(wrapper.find('[data-testid="schedule-form-error"]').text()).toBe('請輸入名稱')

    await wrapper.find('[data-testid="schedule-name"]').setValue('x')
    await wrapper.find('[data-testid="schedule-frequency"]').setValue('interval')
    await wrapper.find('[data-testid="schedule-interval"]').setValue(10)
    await submit(wrapper)
    expect(wrapper.find('[data-testid="schedule-form-error"]').text()).toBe('間隔至少 15 分鐘')

    await wrapper.find('[data-testid="schedule-frequency"]').setValue('weekly')
    await wrapper.findAll('[data-testid="schedule-weekdays"] input')[0].setValue(false)
    await submit(wrapper)
    expect(wrapper.find('[data-testid="schedule-form-error"]').text()).toBe('請至少選擇一天')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('prefills when editing', () => {
    const wrapper = mount(ScheduleForm, {
      props: {
        schedule: {
          id: 's-1', checklist_id: 'cl-1', checklist_name: 'cl', name: 'old', enabled: false,
          frequency: 'interval', time_of_day: null, weekdays: null, interval_minutes: 90,
          parallel_mode: false, max_workers: 1, timezone: 'Asia/Taipei', next_run_at: null,
          last_triggered_at: null, last_execution_id: null, last_execution_status: null,
          last_skip_reason: null, created_by: 'admin',
        },
      },
    })
    expect(wrapper.text()).toContain('編輯排程')
    expect((wrapper.find('[data-testid="schedule-name"]').element as HTMLInputElement).value).toBe('old')
    expect((wrapper.find('[data-testid="schedule-interval"]').element as HTMLInputElement).value).toBe('90')
  })
})
