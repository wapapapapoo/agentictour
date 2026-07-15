import type { Itinerary, Trip } from '@/services/api'
import { parseUtcDate } from '@/utils/tripTime'

export type TripLifecycle = 'upcoming' | 'ongoing' | 'completed' | 'cancelled'
export type ItineraryLifecycle = 'upcoming' | 'ongoing' | 'completed' | 'cancelled'

function localDateKey(now: Date, timeZone: string) {
  try {
    const parts = new Intl.DateTimeFormat('en', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(now)
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
    return `${values.year}-${values.month}-${values.day}`
  } catch {
    return localDateKey(now, 'Asia/Shanghai')
  }
}

export function tripLifecycle(trip: Trip, now = new Date()): TripLifecycle {
  if (trip.status === 'cancelled') return 'cancelled'
  const today = localDateKey(now, trip.timezone || 'Asia/Shanghai')
  if (today < trip.start_date) return 'upcoming'
  if (today > trip.end_date) return 'completed'
  return 'ongoing'
}

export function itineraryLifecycle(
  itinerary: Itinerary,
  now = new Date(),
): ItineraryLifecycle {
  if (itinerary.status === 'cancelled') return 'cancelled'
  if (itinerary.status === 'done') return 'completed'
  const start = parseUtcDate(itinerary.start_time)
  const end = parseUtcDate(itinerary.end_time)
  if (!start || !end) return 'upcoming'
  if (now < start) return 'upcoming'
  if (now >= end) return 'completed'
  return 'ongoing'
}

export const tripLifecycleLabel: Record<TripLifecycle, string> = {
  upcoming: '待出发',
  ongoing: '进行中',
  completed: '已结束',
  cancelled: '已取消',
}

export const itineraryLifecycleLabel: Record<ItineraryLifecycle, string> = {
  upcoming: '待开始',
  ongoing: '进行中',
  completed: '已完成',
  cancelled: '已取消',
}
