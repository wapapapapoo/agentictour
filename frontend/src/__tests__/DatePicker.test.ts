// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import DatePicker from '@/components/DatePicker.vue'

describe('DatePicker', () => {
  it('selects year, month and day without a manually editable date input', async () => {
    const wrapper = mount(DatePicker, {
      props: {
        modelValue: '',
        min: '2025-01-01',
        max: '2027-12-31',
        label: '开始日期',
      },
      attachTo: document.body,
    })

    await wrapper.get('.date-picker-trigger').trigger('click')
    expect(wrapper.find('input').exists()).toBe(false)
    await wrapper.get('[aria-label="选择年份"]').setValue('2026')
    await wrapper.get('[aria-label="选择月份"]').setValue('7')
    await wrapper.get('button[data-date="2026-07-16"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['2026-07-16'])
    wrapper.unmount()
  })
})
