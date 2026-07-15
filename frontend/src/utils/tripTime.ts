export const TRIP_DISPLAY_TIMEZONE = 'Asia/Shanghai'
const SHANGHAI_OFFSET_MS = 8 * 60 * 60 * 1000
const LOCAL_INPUT_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/

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
        timeZone: TRIP_DISPLAY_TIMEZONE,
        hourCycle: 'h23',
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
  return new Date(parsed.getTime() + SHANGHAI_OFFSET_MS).toISOString().slice(0, 16)
}

export function tripInputToUtc(value: string) {
  if (!value) return null
  const matched = LOCAL_INPUT_RE.exec(value)
  if (!matched) return null
  const [, yearText, monthText, dayText, hourText, minuteText, secondText = '00'] = matched
  const parts = [yearText, monthText, dayText, hourText, minuteText, secondText].map(Number)
  const [year, month, day, hour, minute, second] = parts
  const wallClock = new Date(Date.UTC(year, month - 1, day, hour, minute, second))
  const valid = wallClock.getUTCFullYear() === year
    && wallClock.getUTCMonth() === month - 1
    && wallClock.getUTCDate() === day
    && wallClock.getUTCHours() === hour
    && wallClock.getUTCMinutes() === minute
    && wallClock.getUTCSeconds() === second
  return valid ? new Date(wallClock.getTime() - SHANGHAI_OFFSET_MS).toISOString() : null
}
