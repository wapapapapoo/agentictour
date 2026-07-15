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
  }
}

export function openManualAdjustment(): AdjustmentFlowState {
  return { ...closedAdjustment(), open: true, stage: 'request' }
}

export function openAutomaticAdjustment(
  sourceAdviceId: number,
  systemNotice: string,
): AdjustmentFlowState {
  return {
    ...closedAdjustment(),
    open: true,
    mode: 'automatic',
    stage: 'auto-confirm',
    sourceAdviceId,
    systemNotice,
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
