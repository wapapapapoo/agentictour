import { describe, expect, it } from 'vitest'
import { searchCommunityPosts } from '@/services/community'

describe('community search', () => {
  it('matches destination and content text without case sensitivity', () => {
    expect(searchCommunityPosts('杭州')).toHaveLength(1)
    expect(searchCommunityPosts('慢旅行')).toHaveLength(1)
  })

  it('combines keyword and content-type filtering', () => {
    expect(searchCommunityPosts('美食', 'plan')).toHaveLength(1)
    expect(searchCommunityPosts('美食', 'blog')).toHaveLength(0)
  })

  it('returns all fixture posts for an empty query', () => {
    expect(searchCommunityPosts('')).toHaveLength(4)
  })
})
