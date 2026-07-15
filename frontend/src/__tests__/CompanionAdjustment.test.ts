// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Companion from '@/views/Companion.vue'

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    listTrips: vi.fn(),
    listMemos: vi.fn(),
    listItineraries: vi.fn(),
    listAdvice: vi.fn(),
    listNotifications: vi.fn(),
    getTripChat: vi.fn(),
    actOnAdvice: vi.fn(),
    markNotificationRead: vi.fn(),
    deleteTrip: vi.fn(),
  },
}))

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return { ...actual, api: apiMock }
})

const trip = {
  id: 1,
  title: '上海旅行',
  origin_city: '杭州',
  destination_city: '上海',
  start_date: '2026-07-15',
  end_date: '2026-07-17',
  status: 'ongoing',
}

function advice(overrides: Record<string, unknown> = {}) {
  return {
    advice_id: 17,
    trip_id: 1,
    advice_type: 'itinerary_replan',
    reason_text: '景点临时闭馆，将影响下午行程。',
    advice_text: '景点临时闭馆，将影响下午行程。',
    result: 'pending',
    audit_status: 'pass',
    created_at: '2026-07-15T08:00:00',
    ...overrides,
  }
}

async function mountCompanion(
  adviceRows: ReturnType<typeof advice>[] = [],
  memoRows: Record<string, unknown>[] = [],
  itineraryRows: Record<string, unknown>[] = [],
) {
  apiMock.listTrips.mockResolvedValue([trip])
  apiMock.listMemos.mockResolvedValue(memoRows)
  apiMock.listItineraries.mockResolvedValue(itineraryRows)
  apiMock.listAdvice.mockResolvedValue(adviceRows)
  apiMock.listNotifications.mockResolvedValue([])
  apiMock.getTripChat.mockResolvedValue({
    session_id: 1,
    trip_id: 1,
    user_id: 1,
    status: 'active',
    messages: [],
  })
  const wrapper = mount(Companion, { attachTo: document.body })
  await flushPromises()
  await flushPromises()
  return wrapper
}

describe('Companion adjustment dialog', () => {
  beforeEach(() => vi.clearAllMocks())

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('opens an automatic confirmation and then shows system notice plus supplement', async () => {
    const wrapper = await mountCompanion([advice()])

    expect(document.body.textContent).toContain('是否根据这项变化重新生成')
    expect(document.body.textContent).toContain('放弃')
    const agree = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === '同意更改',
    )
    expect(agree).toBeTruthy()
    agree!.click()
    await flushPromises()

    const textareas = document.body.querySelectorAll('.adjustment-dialog textarea')
    expect(textareas).toHaveLength(2)
    expect(document.body.textContent).toContain('系统自动提示')
    expect(document.body.textContent).toContain('用户补充')
    wrapper.unmount()
  })

  it('uses a single requirement field for a manual adjustment', async () => {
    const wrapper = await mountCompanion()
    const open = wrapper.findAll('button').find((button) => button.text() === '调整行程')
    expect(open).toBeTruthy()
    await open!.trigger('click')

    expect(document.body.querySelectorAll('.adjustment-dialog textarea')).toHaveLength(1)
    expect(document.body.textContent).toContain('调整要求')
    expect(document.body.textContent).not.toContain('用户补充')
    wrapper.unmount()
  })

  it('renders a legacy failed audit reason once instead of duplicating the reply', async () => {
    const reason = '候选方案未满足审核要求'
    const wrapper = await mountCompanion([
      advice({ audit_status: 'failed', audit_reason: reason, advice_text: reason }),
    ])

    expect((wrapper.text().match(new RegExp(reason, 'g')) || [])).toHaveLength(1)
    expect(wrapper.findAll('.audit-failure-only')).toHaveLength(1)
    wrapper.unmount()
  })

  it('opens memo and itinerary creation in dedicated dialogs', async () => {
    const wrapper = await mountCompanion()

    const addMemo = wrapper.findAll('button').find((button) => button.text() === '添加备忘')
    expect(addMemo).toBeTruthy()
    await addMemo!.trigger('click')
    expect(document.body.textContent).toContain('新增旅途备忘')
    expect(document.body.querySelector('.memo-dialog')).toBeTruthy()
    document.body.querySelector<HTMLButtonElement>('.memo-dialog .dialog-close')!.click()
    await flushPromises()

    const addItinerary = wrapper.findAll('button').find((button) => button.text() === '添加日程')
    expect(addItinerary).toBeTruthy()
    await addItinerary!.trigger('click')
    expect(document.body.textContent).toContain('新增实时日程')
    expect(document.body.querySelector('.itinerary-dialog')).toBeTruthy()
    wrapper.unmount()
  })

  it('offers an explicit current plan deletion confirmation', async () => {
    const wrapper = await mountCompanion()

    const removePlan = wrapper.findAll('button').find((button) => button.text() === '删除当前计划')
    expect(removePlan).toBeTruthy()
    await removePlan!.trigger('click')
    expect(document.body.textContent).toContain('确认删除计划')
    expect(document.body.textContent).toContain('上海旅行')
    const confirm = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === '确认删除计划',
    )
    confirm!.click()
    await flushPromises()
    expect(apiMock.deleteTrip).toHaveBeenCalledWith(1)
    wrapper.unmount()
  })

  it('shows explicit deletion controls for memo and itinerary rows', async () => {
    const wrapper = await mountCompanion(
      [],
      [{ memo_id: 3, trip_id: 1, memo_text: '带证件', reminder_time: null }],
      [{
        itinerary_id: 8,
        trip_id: 1,
        title: '参观博物馆',
        place_name: '市博物馆',
        start_time: '2026-07-16T01:00:00',
        end_time: '2026-07-16T03:00:00',
        itinerary_type: 'play',
        status: 'pending',
      }],
    )

    const rowDeletes = wrapper.findAll('button').filter((button) => button.text() === '删除')
    expect(rowDeletes).toHaveLength(2)
    await rowDeletes[0]!.trigger('click')
    expect(document.body.textContent).toContain('将删除“带证件”')
    wrapper.unmount()
  })
})
