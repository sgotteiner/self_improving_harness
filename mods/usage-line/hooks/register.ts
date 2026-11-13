import type { Register, SessionRateLimit } from 'claude-code'

const LABELS: Record<string, string> = { five_hour: 'Session', seven_day: 'Week' }

function timeLeft(resetsAt: string | undefined, now: number): string {
  if (!resetsAt) return ''
  const minutes = Math.max(0, Math.round((Date.parse(resetsAt) - now) / 60000))
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const left = days > 0 ? `${days}d ${hours}h` : hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes}m`
  return ` (resets in ${left})`
}

export function formatLine(limits: SessionRateLimit[], now: number): string | undefined {
  const parts = limits
    .filter(l => LABELS[l.kind])
    .map(l => `${LABELS[l.kind]} ${Math.round(l.percentUsed)}%${timeLeft(l.resetsAt, now)}`)
  return parts.length ? parts.join(' · ') : undefined
}

export const register: Register = on => {
  let limits: SessionRateLimit[] = []
  let ticking = false

  on('session.start', async ($, e, next) => {
    limits = (await $.session.usage()).rateLimits
    $.ui.status(formatLine(limits, await $.clock.now()))
    if (!ticking) {
      ticking = true
      $.clock.every(60000, async () => $.ui.status(formatLine(limits, await $.clock.now())))
    }
    return next(e)
  })

  on('session.measure', async ($, e, next) => {
    limits = e.rateLimits
    $.ui.status(formatLine(limits, await $.clock.now()))
    return next(e)
  })
}
