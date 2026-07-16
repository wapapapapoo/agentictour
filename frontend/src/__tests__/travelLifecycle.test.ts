import { describe, expect, it } from 'vitest'

import { itineraryLifecycle, tripLifecycle } from '@/utils/travelLifecycle'

const now = new Date('2026-07-15T12:00:00Z')

describe('travel lifecycle', () => {
  it('derives trip state from local dates while preserving cancellation', () => {
    const base = {
      id: 1,
      title: '测试旅行',
      origin_city: '天津',
      destination_city: '沈阳',
      timezone: 'Asia/Shanghai',
      status: 'planned',
    }

    expect(tripLifecycle({ ...base, start_date: '2026-07-16', end_date: '2026-07-18' }, now)).toBe('upcoming')
    expect(tripLifecycle({ ...base, start_date: '2026-07-15', end_date: '2026-07-16' }, now)).toBe('ongoing')
    expect(tripLifecycle({ ...base, start_date: '2026-07-10', end_date: '2026-07-14' }, now)).toBe('completed')
    expect(tripLifecycle({ ...base, start_date: '2026-07-15', end_date: '2026-07-16', status: 'cancelled' }, now)).toBe('cancelled')
  })

  it('shows itinerary states before, during and after execution', () => {
    const base = {
      itinerary_id: 1,
      trip_id: 1,
      title: '测试日程',
      place_name: '测试地点',
      itinerary_type: 'play' as const,
      status: 'pending' as const,
    }

    expect(itineraryLifecycle({ ...base, start_time: '2026-07-15T13:00:00Z', end_time: '2026-07-15T14:00:00Z' }, now)).toBe('upcoming')
    expect(itineraryLifecycle({ ...base, start_time: '2026-07-15T11:00:00Z', end_time: '2026-07-15T13:00:00Z' }, now)).toBe('ongoing')
    expect(itineraryLifecycle({ ...base, start_time: '2026-07-15T10:00:00Z', end_time: '2026-07-15T11:00:00Z' }, now)).toBe('completed')
    expect(itineraryLifecycle({ ...base, start_time: '2026-07-15T13:00:00Z', end_time: '2026-07-15T14:00:00Z', status: 'cancelled' }, now)).toBe('cancelled')
    expect(itineraryLifecycle({ ...base, start_time: '2026-07-15T13:00:00Z', end_time: '2026-07-15T14:00:00Z', status: 'change_pending' }, now)).toBe('change_pending')
  })
})
