import { describe, expect, it } from 'vitest'

import {
  acceptAutomaticAdjustment,
  openAutomaticAdjustment,
  openManualAdjustment,
} from '@/utils/adjustmentFlow'

describe('adjustment modal flow', () => {
  it('uses one requirement field for a manual adjustment', () => {
    const state = openManualAdjustment()

    expect(state).toMatchObject({
      open: true,
      mode: 'manual',
      stage: 'request',
      systemNotice: '',
      sourceAdviceId: null,
    })
  })

  it('asks for confirmation before an automatic adjustment', () => {
    const confirmation = openAutomaticAdjustment(17, '景点临时闭馆')
    expect(confirmation).toMatchObject({
      open: true,
      mode: 'automatic',
      stage: 'auto-confirm',
      systemNotice: '景点临时闭馆',
      sourceAdviceId: 17,
      selectedItineraryIds: [],
      lockedItineraryIds: [],
    })

    const request = acceptAutomaticAdjustment(confirmation)
    expect(request.stage).toBe('request')
    expect(request.systemNotice).toBe('景点临时闭馆')
    expect(request.sourceAdviceId).toBe(17)
  })

  it('preselects and locks conflicts detected by automatic checks', () => {
    const state = openAutomaticAdjustment(17, '景点临时闭馆', [8, 9])

    expect(state.selectedItineraryIds).toEqual([8, 9])
    expect(state.lockedItineraryIds).toEqual([8, 9])
  })
})
