import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import HelloWorld from '@/components/HelloWorld.vue'

describe('HelloWorld', () => {
  it('renders msg prop', () => {
    const wrapper = mount(HelloWorld, {
      props: { msg: 'Hello Vitest' },
    })
    expect(wrapper.find('h2').text()).toBe('Hello Vitest')
  })

  it('increments count on button click', async () => {
    const wrapper = mount(HelloWorld, {
      props: { msg: 'Test' },
    })

    const button = wrapper.find('button')
    expect(button.text()).toContain('Count is 0')

    await button.trigger('click')
    expect(button.text()).toContain('Count is 1')
  })
})
