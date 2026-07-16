import { describe, expect, it } from 'vitest'
import { itineraryDate, preferredItineraryDate, tripDateRange } from '@/utils/itineraryDay'

describe('itinerary day selection', () => {
  const dates = tripDateRange('2026-07-23', '2026-07-24')

  it('uses the current travel day when it matches the trip range', () => {
    expect(preferredItineraryDate(dates, new Date('2026-07-24T04:00:00Z'))).toBe('2026-07-24')
  })

  it('falls back to the first travel day outside the trip range', () => {
    expect(preferredItineraryDate(dates, new Date('2026-07-22T04:00:00Z'))).toBe('2026-07-23')
  })

  it('groups stored UTC itinerary times by their Shanghai calendar day', () => {
    expect(itineraryDate('2026-07-23T16:30:00Z')).toBe('2026-07-24')
  })
})
