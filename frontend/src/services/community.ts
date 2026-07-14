export type CommunityContentType = 'plan' | 'blog'

export interface CommunityPost {
  id: string
  type: CommunityContentType
  title: string
  author: string
  destination: string
  excerpt: string
  tags: string[]
  likes: number
  saves: number
  readMinutes: number
  accent: string
}

// Replace this fixture with GET /api/community/posts once the community API is available.
export const communityPosts: CommunityPost[] = [
  { id: 'hangzhou-slow', type: 'plan', title: '杭州 3 天游：把西湖留给清晨', author: '小满同学', destination: '杭州', excerpt: '避开人潮的晨间西湖、南山路散步和一份慢节奏咖啡地图。', tags: ['慢旅行', '人文', '3 天'], likes: 328, saves: 126, readMinutes: 4, accent: 'lake' },
  { id: 'dali-story', type: 'blog', title: '风从洱海吹来时，我终于慢下来', author: '林间来信', destination: '大理', excerpt: '三天两夜的碎片、一次日落和一场没有目的地的骑行。', tags: ['故事', '治愈', '云南'], likes: 562, saves: 198, readMinutes: 6, accent: 'sunset' },
  { id: 'chengdu-food', type: 'plan', title: '成都周末美食路线，不赶路也尽兴', author: '吃吃旅行家', destination: '成都', excerpt: '以地铁为线索，把茶馆、火锅和街巷小店串成一个周末。', tags: ['美食', '周末', '地铁'], likes: 284, saves: 93, readMinutes: 3, accent: 'pepper' },
  { id: 'xiamen-notes', type: 'blog', title: '厦门的海风，写在旧街的影子里', author: '阿序', destination: '厦门', excerpt: '从八市清晨到沙坡尾黄昏，一次不设清单的城市漫游。', tags: ['城市漫游', '摄影', '海边'], likes: 401, saves: 157, readMinutes: 5, accent: 'ocean' },
]

export function searchCommunityPosts(query: string, type: 'all' | CommunityContentType = 'all') {
  const keyword = query.trim().toLowerCase()
  return communityPosts.filter((post) => {
    const matched = !keyword || [post.title, post.author, post.destination, post.excerpt, ...post.tags].join(' ').toLowerCase().includes(keyword)
    return matched && (type === 'all' || post.type === type)
  })
}
