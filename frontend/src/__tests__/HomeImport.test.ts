// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Home from '@/views/Home.vue'

const { apiMock, pushMock } = vi.hoisted(() => ({
  apiMock: {
    listPlans: vi.fn(),
    generatePlan: vi.fn(),
    syncPlanItineraries: vi.fn(),
  },
  pushMock: vi.fn(),
}))

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return { ...actual, api: { ...actual.api, ...apiMock } }
})

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe('planner import submission', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.listPlans.mockResolvedValue([])
  })

  it('ignores a second plan generation click while the first is pending', async () => {
    apiMock.generatePlan.mockReturnValue(new Promise(() => undefined))
    const wrapper = mount(Home)
    await flushPromises()
    const inputs = wrapper.findAll('input[type="date"]')
    await inputs[0]!.setValue('2026-07-20')
    await inputs[1]!.setValue('2026-07-22')
    const button = wrapper.findAll('button').find((item) => (
      item.text().includes('生成旅行规划')
    ))

    expect(button).toBeTruthy()
    void button!.trigger('click')
    void button!.trigger('click')
    await flushPromises()

    expect(apiMock.generatePlan).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
})
