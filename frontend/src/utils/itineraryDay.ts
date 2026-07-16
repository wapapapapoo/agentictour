import { TRIP_DISPLAY_TIMEZONE, tripInputFromUtc } from './tripTime'

function shanghaiDate(value: Date) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TRIP_DISPLAY_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(value)
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${map.year}-${map.month}-${map.day}`
}

export function tripDateRange(startDate?: string, endDate?: string) {
  if (!startDate || !endDate || endDate < startDate) return []
  const dates: string[] = []
  const cursor = new Date(`${startDate}T00:00:00Z`)
  const last = new Date(`${endDate}T00:00:00Z`)
  while (cursor <= last) {
    dates.push(cursor.toISOString().slice(0, 10))
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  return dates
}

export function preferredItineraryDate(dates: string[], now = new Date()) {
  const today = shanghaiDate(now)
  return dates.includes(today) ? today : dates[0] || ''
}

export function itineraryDate(value?: string | null) {
  return tripInputFromUtc(value).slice(0, 10)
}
