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
    sendChatMessage: vi.fn(),
    actOnAdvice: vi.fn(),
    markNotificationRead: vi.fn(),
    deleteTrip: vi.fn(),
    generateAdvice: vi.fn(),
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
  notificationRows: Record<string, unknown>[] = [],
  chatRows: Record<string, unknown>[] = [],
  tripRows: Record<string, unknown>[] = [trip],
) {
  apiMock.listTrips.mockResolvedValue(tripRows)
  apiMock.listMemos.mockResolvedValue(memoRows)
  apiMock.listItineraries.mockResolvedValue(itineraryRows)
  apiMock.listAdvice.mockResolvedValue(adviceRows)
  apiMock.listNotifications.mockResolvedValue(notificationRows)
  apiMock.getTripChat.mockResolvedValue({
    session_id: 1,
    trip_id: 1,
    user_id: 1,
    status: 'active',
    messages: chatRows,
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

  it('shows web citations from an agent reply as a dedicated source list', async () => {
    const wrapper = await mountCompanion([], [], [], [], [{
      message_id: 9,
      sender_type: 'ai',
      content: '开放信息以景区公告为准。\n\n参考来源：\n- [景区官网](https://example.com/visit)',
      audit_status: 'pass',
      audit_reason: null,
    }])

    const source = wrapper.find('.message-sources a')
    expect(source.text()).toBe('景区官网')
    expect(source.attributes('href')).toBe('https://example.com/visit')
    expect(source.attributes('target')).toBe('_blank')
    expect(source.attributes('rel')).toBe('noopener noreferrer')
    expect(wrapper.find('.message .markdown-body').text()).not.toContain('参考来源')
    wrapper.unmount()
  })

  it('prevents the same message from being submitted twice while pending', async () => {
    apiMock.sendChatMessage.mockReturnValue(new Promise(() => undefined))
    const wrapper = await mountCompanion()
    const input = wrapper.find('.composer input')
    await input.setValue('介绍一下天津工业大学')

    void wrapper.find('.composer').trigger('submit')
    void wrapper.find('.composer').trigger('submit')
    await flushPromises()

    expect(apiMock.sendChatMessage).toHaveBeenCalledTimes(1)
    expect(wrapper.findAll('.message.user')).toHaveLength(1)
    expect(wrapper.find('.composer button').text()).toBe('等待回复…')
    expect(wrapper.find('.messages').attributes('aria-busy')).toBe('true')
    expect(wrapper.text()).toContain('Hikari 正在思考并核对旅途信息')
    wrapper.unmount()
  })

  it('collapses consecutive duplicate user messages restored from history', async () => {
    const wrapper = await mountCompanion([], [], [], [], [
      { message_id: 1, sender_type: 'user', content: '介绍一下天津工业大学' },
      { message_id: 2, sender_type: 'user', content: '介绍一下天津工业大学' },
      { message_id: 3, sender_type: 'ai', content: '这里是介绍。', audit_status: 'pass' },
    ])

    expect(wrapper.findAll('.message.user')).toHaveLength(1)
    expect(wrapper.findAll('.message.agent')).toHaveLength(1)
    wrapper.unmount()
  })

  it('shows an empty state instead of a live trip when no plan exists', async () => {
    const wrapper = await mountCompanion([], [], [], [], [], [])

    expect(wrapper.text()).toContain('目前还没有旅行计划')
    expect(wrapper.text()).not.toContain('LIVE · 正在进行')
    wrapper.unmount()
  })

  it('renders upcoming trip and time-driven itinerary lifecycle labels', async () => {
    const current = Date.now()
    const itinerary = (id: number, start: number, end: number, status = 'pending') => ({
      itinerary_id: id,
      trip_id: 2,
      title: `日程 ${id}`,
      place_name: '测试地点',
      start_time: new Date(start).toISOString(),
      end_time: new Date(end).toISOString(),
      itinerary_type: 'play',
      status,
    })
    const wrapper = await mountCompanion(
      [],
      [],
      [
        itinerary(1, current + 3_600_000, current + 7_200_000),
        itinerary(2, current - 3_600_000, current + 3_600_000),
        itinerary(3, current - 7_200_000, current - 3_600_000),
        itinerary(4, current + 3_600_000, current + 7_200_000, 'cancelled'),
      ],
      [],
      [],
      [{ ...trip, id: 2, start_date: '2099-07-15', end_date: '2099-07-16', status: 'planned' }],
    )

    expect(wrapper.text()).toContain('UPCOMING · 尚未开始')
    expect(wrapper.findAll('.itinerary-status').map((item) => item.text())).toEqual([
      '待开始',
      '进行中',
      '已完成',
      '已取消',
    ])
    wrapper.unmount()
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
    expect(wrapper.find('.audit-failure-summary').exists()).toBe(true)
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

  it('highlights the ongoing trip near the top of the workspace', async () => {
    const wrapper = await mountCompanion()

    const card = wrapper.find('.active-trip-card')
    expect(card.exists()).toBe(true)
    expect(card.text()).toContain(trip.title)
    expect(card.text()).toContain(trip.origin_city)
    expect(card.text()).toContain(trip.destination_city)
    const activeIndex = wrapper.find('.companion-page').element.children[0]?.className
    expect(activeIndex).toContain('active-trip-section')
    expect(wrapper.find('.trip-overview').text()).toContain('计划日期')
    expect(wrapper.find('.trip-overview').text()).toContain('杭州 → 上海')
    wrapper.unmount()
  })

  it('shows the current itinerary itself instead of a redundant ongoing count', async () => {
    const now = Date.now()
    const wrapper = await mountCompanion([], [], [{
      itinerary_id: 88,
      trip_id: 1,
      title: '参观天津工业大学',
      place_name: '天津工业大学校内',
      start_time: new Date(now - 30 * 60_000).toISOString(),
      end_time: new Date(now + 30 * 60_000).toISOString(),
      itinerary_type: 'play',
      status: 'pending',
    }])

    const card = wrapper.find('.active-trip-card')
    expect(card.text()).toContain('参观天津工业大学')
    expect(card.text()).toContain('天津工业大学校内')
    expect(card.text()).not.toContain('项正在进行')
    expect(wrapper.find('.trip-overview').text()).toContain('参观天津工业大学')
    wrapper.unmount()
  })

  it('opens a reminder inbox with unread count and unread filtering', async () => {
    const wrapper = await mountCompanion([], [], [], [
      {
        notification_id: 31,
        trip_id: 1,
        content: '出发前记得携带身份证。',
        category: 'memo_reminder',
        read_at: null,
        created_at: '2026-07-15T08:00:00',
      },
      {
        notification_id: 32,
        trip_id: 1,
        content: '酒店入住时间已经确认。',
        category: 'itinerary_reminder',
        read_at: '2026-07-15T09:00:00',
        created_at: '2026-07-15T08:30:00',
      },
    ])

    expect(wrapper.find('.notification-inbox-trigger .unread-badge').text()).toBe('1')
    await wrapper.find('.notification-inbox-trigger').trigger('click')
    expect(document.body.querySelector('.notification-dialog')).toBeTruthy()
    expect(document.body.querySelectorAll('.mail-row')).toHaveLength(2)

    const unreadFilter = document.body.querySelector<HTMLInputElement>('.notification-dialog input[type="checkbox"]')!
    unreadFilter.click()
    await flushPromises()
    expect(document.body.querySelectorAll('.mail-row')).toHaveLength(1)
    expect(document.body.querySelector('.mail-row.unread')).toBeTruthy()
    wrapper.unmount()
  })

  it('lets users select pending conflict items and excludes completed items', async () => {
    const wrapper = await mountCompanion([], [], [
      {
        itinerary_id: 8,
        trip_id: 1,
        title: '夜游',
        place_name: '河畔',
        start_time: '2026-07-16T12:00:00',
        end_time: '2026-07-16T14:00:00',
        itinerary_type: 'play',
        status: 'pending',
      },
      {
        itinerary_id: 9,
        trip_id: 1,
        title: '已经完成的午餐',
        place_name: '餐厅',
        start_time: '2026-07-15T04:00:00',
        end_time: '2026-07-15T05:00:00',
        itinerary_type: 'play',
        status: 'done',
      },
    ])

    await wrapper.findAll('button').find((button) => button.text() === '调整行程')!.trigger('click')
    const choices = document.body.querySelectorAll('.conflict-choice')
    expect(choices).toHaveLength(1)
    expect(choices[0]!.textContent).toContain('夜游')
    expect(document.body.querySelector('.conflict-picker')!.textContent).not.toContain('已经完成的午餐')
    wrapper.unmount()
  })

  it('locks automatically detected conflicts but allows extra selections', async () => {
    const wrapper = await mountCompanion([
      advice({ proposed_itinerary: { conflicting_itinerary_ids: [8] } }),
    ], [], [
      {
        itinerary_id: 8,
        trip_id: 1,
        title: '自动识别的冲突行程',
        place_name: '景点 A',
        start_time: '2026-07-16T12:00:00',
        end_time: '2026-07-16T14:00:00',
        itinerary_type: 'play',
        status: 'pending',
      },
      {
        itinerary_id: 9,
        trip_id: 1,
        title: '用户可追加的行程',
        place_name: '景点 B',
        start_time: '2026-07-16T15:00:00',
        end_time: '2026-07-16T17:00:00',
        itinerary_type: 'play',
        status: 'pending',
      },
    ])

    const agree = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === '同意更改',
    )!
    agree.click()
    await flushPromises()
    const checkboxes = document.body.querySelectorAll<HTMLInputElement>('.conflict-choice input')
    expect(checkboxes).toHaveLength(2)
    expect(checkboxes[0]!.checked).toBe(true)
    expect(checkboxes[0]!.disabled).toBe(true)
    expect(checkboxes[1]!.disabled).toBe(false)
    wrapper.unmount()
  })

  it('shows a visible progress state while a candidate request is pending', async () => {
    apiMock.generateAdvice.mockReturnValue(new Promise(() => undefined))
    const wrapper = await mountCompanion()
    await wrapper.findAll('button').find((button) => button.text() === '调整行程')!.trigger('click')
    const textarea = document.body.querySelector<HTMLTextAreaElement>('.adjustment-dialog textarea')!
    textarea.value = '把夜游改成游行'
    textarea.dispatchEvent(new Event('input'))
    await flushPromises()
    const submit = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === '生成候选方案',
    )!
    submit.click()
    await flushPromises()
    expect(document.body.querySelector('.adjustment-progress')).toBeTruthy()
    expect(document.body.textContent).toContain('正在生成候选方案')
    wrapper.unmount()
  })

  it('shows progress after accepting an existing candidate', async () => {
    apiMock.actOnAdvice.mockReturnValue(new Promise(() => undefined))
    const wrapper = await mountCompanion([
      advice({ advice_type: 'replan', result: 'pending' }),
    ])
    await wrapper.findAll('button').find((button) => button.text() === '继续处理候选方案')!.trigger('click')
    const accept = Array.from(document.body.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === '采纳并更新日程',
    )!
    accept.click()
    await flushPromises()

    expect(document.body.querySelector('.adjustment-progress')).toBeTruthy()
    expect(document.body.textContent).toContain('正在采纳方案并更新实时日程')
    wrapper.unmount()
  })
})
