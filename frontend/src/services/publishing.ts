import type { CommunityContentType } from './community'

export type PublishVisibility = 'public' | 'unlisted'

export interface PublishRequest {
  sourceId?: number
  contentType: CommunityContentType
  title: string
  visibility: PublishVisibility
}

export interface PublishResult {
  status: 'pending_api'
  message: string
}

/**
 * API reservation for POST /api/community/posts.
 * Keep UI components dependent on this function only; replace the body with
 * an HTTP call when the backend community service is implemented.
 */
export async function publishContent(_request: PublishRequest): Promise<PublishResult> {
  void _request;
  return {
    status: 'pending_api',
    message: '社区发布接口尚未接入。',
  }
}
