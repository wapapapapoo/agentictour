import { describe, expect, it } from 'vitest'
import { publishContent } from '@/services/publishing'

describe('publishing API reservation', () => {
  it('keeps the publish request available without a backend endpoint', async () => {
    await expect(publishContent({ contentType: 'plan', title: '杭州周末游', visibility: 'public' }))
      .resolves.toMatchObject({ status: 'pending_api' })
  })
})
