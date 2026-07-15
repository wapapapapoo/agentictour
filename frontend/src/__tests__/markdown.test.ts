import { describe, expect, it } from 'vitest'

import { extractReferenceSources } from '@/utils/markdown'

describe('extractReferenceSources', () => {
  it('extracts and deduplicates safe markdown and bare web sources', () => {
    const sources = extractReferenceSources([
      '开放时间以[故宫博物院官网](https://www.dpm.org.cn/visit.html)为准。',
      '补充报道：https://example.com/travel/news。',
      '重复链接：[官网](https://www.dpm.org.cn/visit.html)',
    ].join('\n'))

    expect(sources).toEqual([
      { title: '故宫博物院官网', url: 'https://www.dpm.org.cn/visit.html' },
      { title: 'example.com', url: 'https://example.com/travel/news' },
    ])
  })

  it('ignores non-http links and limits the number of displayed sources', () => {
    const text = [
      '[危险链接](javascript:alert(1))',
      ...Array.from({ length: 10 }, (_, index) => `https://source${index}.example.com/page`),
    ].join('\n')

    const sources = extractReferenceSources(text)

    expect(sources).toHaveLength(6)
    expect(sources.every((source) => source.url.startsWith('https://'))).toBe(true)
  })
})
