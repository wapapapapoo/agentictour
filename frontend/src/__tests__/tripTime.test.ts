import { describe, expect, it } from 'vitest'

import { formatTripDate, tripInputFromUtc, tripInputToUtc } from '@/utils/tripTime'

describe('trip time conversion', () => {
  it('displays backend UTC values as Asia/Shanghai time', () => {
    expect(formatTripDate('2026-07-15T09:49:00')).toContain('17:49')
    expect(tripInputFromUtc('2026-07-15T09:49:00')).toBe('2026-07-15T17:49')
  })

  it('stores Beijing datetime-local values as UTC', () => {
    expect(tripInputToUtc('2026-07-15T17:49')).toBe('2026-07-15T09:49:00.000Z')
  })
})
