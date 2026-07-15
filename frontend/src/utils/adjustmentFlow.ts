export type AdjustmentMode = 'manual' | 'automatic'
export type AdjustmentStage = 'closed' | 'auto-confirm' | 'request' | 'candidate' | 'revision'

export type AdjustmentFlowState = {
  open: boolean
  mode: AdjustmentMode
  stage: AdjustmentStage
  sourceAdviceId: number | null
  candidateAdviceId: number | null
  systemNotice: string
  requirement: string
  supplement: string
  revision: string
  selectedItineraryIds: number[]
  lockedItineraryIds: number[]
}

export function closedAdjustment(): AdjustmentFlowState {
  return {
    open: false,
    mode: 'manual',
    stage: 'closed',
    sourceAdviceId: null,
    candidateAdviceId: null,
    systemNotice: '',
    requirement: '',
    supplement: '',
    revision: '',
    selectedItineraryIds: [],
    lockedItineraryIds: [],
  }
}

export function openManualAdjustment(): AdjustmentFlowState {
  return { ...closedAdjustment(), open: true, stage: 'request' }
}

export function openAutomaticAdjustment(
  sourceAdviceId: number,
  systemNotice: string,
  lockedItineraryIds: number[] = [],
): AdjustmentFlowState {
  return {
    ...closedAdjustment(),
    open: true,
    mode: 'automatic',
    stage: 'auto-confirm',
    sourceAdviceId,
    systemNotice,
    selectedItineraryIds: [...lockedItineraryIds],
    lockedItineraryIds: [...lockedItineraryIds],
  }
}

export function acceptAutomaticAdjustment(
  state: AdjustmentFlowState,
): AdjustmentFlowState {
  return { ...state, stage: 'request' }
}

export function showAdjustmentCandidate(
  state: AdjustmentFlowState,
  candidateAdviceId: number,
): AdjustmentFlowState {
  return {
    ...state,
    open: true,
    stage: 'candidate',
    candidateAdviceId,
    revision: '',
  }
}
