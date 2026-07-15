const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000

export function parseUtcDate(value?: string | null) {
  if (!value) return null
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  const parsed = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function formatTripDate(value?: string | null) {
  const parsed = parseUtcDate(value)
  return parsed
    ? parsed.toLocaleString('zh-CN', {
        timeZone: 'Asia/Shanghai',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '未设置'
}

export function tripInputFromUtc(value?: string | null) {
  const parsed = parseUtcDate(value)
  if (!parsed) return ''
  return new Date(parsed.getTime() + BEIJING_OFFSET_MS).toISOString().slice(0, 16)
}

export function tripInputToUtc(value: string) {
  if (!value) return null
  const normalized = value.length === 16 ? `${value}:00` : value
  const parsed = new Date(`${normalized}+08:00`)
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString()
}
