import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.use({
  breaks: true,
  gfm: true,
})

export function renderMarkdown(markdown: string) {
  const html = marked.parse(markdown, { async: false })
  return DOMPurify.sanitize(html)
}

export type ReferenceSource = {
  title: string
  url: string
}

const TRAILING_URL_PUNCTUATION = /[)\]}>.,;:!?，。；：！？]+$/

function safeWebUrl(value: string) {
  const cleaned = value.trim().replace(TRAILING_URL_PUNCTUATION, '')
  try {
    const parsed = new URL(cleaned)
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.toString() : null
  } catch {
    return null
  }
}

export function extractReferenceSources(markdown: string, limit = 6): ReferenceSource[] {
  const sources: ReferenceSource[] = []
  const seen = new Set<string>()

  const append = (rawUrl: string, rawTitle?: string) => {
    if (sources.length >= limit) return
    const url = safeWebUrl(rawUrl)
    if (!url || seen.has(url)) return
    const hostname = new URL(url).hostname.replace(/^www\./, '')
    const title = rawTitle?.replace(/[*_`]/g, '').trim() || hostname
    seen.add(url)
    sources.push({ title, url })
  }

  const markdownLink = /\[([^\]]+)]\((https?:\/\/[^\s)]+)(?:\s+["'][^"']*["'])?\)/gi
  for (const match of markdown.matchAll(markdownLink)) append(match[2], match[1])

  const bareLink = /https?:\/\/[^\s<>"')\]]+/gi
  for (const match of markdown.matchAll(bareLink)) append(match[0])

  return sources
}

export function stripReferenceSection(markdown: string) {
  if (!extractReferenceSources(markdown).length) return markdown
  const heading = /^[ \t]*(?:#{1,6}[ \t]+)?(?:\*\*|__)?参考来源[ \t]*[:：]?[ \t]*(?:\*\*|__)?[ \t]*$/gim
  const matches = [...markdown.matchAll(heading)]
  const lastHeading = matches.at(-1)
  return lastHeading?.index === undefined
    ? markdown
    : markdown.slice(0, lastHeading.index).trim()
}
