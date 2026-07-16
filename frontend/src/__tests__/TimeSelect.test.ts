// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TimeSelect from '@/components/TimeSelect.vue'

describe('TimeSelect', () => {
  it('accepts direct keyboard input and normalizes it to HH:mm', async () => {
    const wrapper = mount(TimeSelect, {
      props: { modelValue: '', label: '提醒时间' },
    })

    const input = wrapper.get<HTMLInputElement>('.time-picker-input')
    await input.setValue('9:30')
    await input.trigger('blur')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['09:30'])
  })

  it('offers touch-friendly hour and minute wheels with every minute available', async () => {
    const wrapper = mount(TimeSelect, {
      props: { modelValue: '09:30', label: '提醒时间' },
      attachTo: document.body,
    })

    await wrapper.get('.time-picker-toggle').trigger('click')
    expect(wrapper.findAll('.time-wheel-hours button')).toHaveLength(24)
    expect(wrapper.findAll('.time-wheel-minutes button')).toHaveLength(60)
    await wrapper.get('.time-wheel-hours button[data-value="10"]').trigger('click')
    await wrapper.get('.time-wheel-minutes button[data-value="45"]').trigger('click')
    await wrapper.get('.time-picker-confirm').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['10:45'])
    wrapper.unmount()
  })
})
