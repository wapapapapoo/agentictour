// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import { renderMarkdown } from '@/utils/markdown'

describe('renderMarkdown', () => {
  it('renders headings, emphasis, lists, and GFM tables', () => {
    const html = renderMarkdown(`## 建议\n\n**先休息**\n\n1. 入住酒店\n\n| 时间 | 安排 |\n| --- | --- |\n| 19:00 | 到站 |`)

    expect(html).toContain('<h2>建议</h2>')
    expect(html).toContain('<strong>先休息</strong>')
    expect(html).toContain('<ol>')
    expect(html).toContain('<table>')
  })

  it('removes unsafe generated markup', () => {
    const html = renderMarkdown('正常内容<script>alert(1)</script>')

    expect(html).toContain('正常内容')
    expect(html).not.toContain('<script>')
  })
})
