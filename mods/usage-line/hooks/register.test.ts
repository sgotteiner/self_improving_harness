import { expect, test } from 'claude-code/testing'

import { formatLine } from './register'

const NOW = Date.parse('2026-10-24T12:00:00Z')

test('shows session and week with time to reset', () => {
  const line = formatLine(
    [
      { kind: 'five_hour', percentUsed: 23.5, resetsAt: '2026-10-24T14:10:00Z' },
      { kind: 'seven_day', percentUsed: 41, resetsAt: '2026-10-27T15:00:00Z' },
    ],
    NOW,
  )
  expect(line).toBe('Session 24% (resets in 2h 10m) · Week 41% (resets in 3d 3h)')
})

test('shows nothing until a limit is known', () => {
  expect(formatLine([], NOW)).toBe(undefined)
})

test('a usage update sets the status line', async ($, on) => {
  const shown: (string | undefined)[] = []
  on('ui.status', (_, e) => (shown.push(e.text), { value: undefined }))
  on('clock.now', () => ({ value: NOW }))
  on('session.measure', (_, e) => ({ changed: e.changed }))

  await $.session.measure({
    context: { tokens: 0, window: 200000, percentUsed: 0, apiUsage: null } as never,
    rateLimits: [{ kind: 'seven_day', percentUsed: 41, resetsAt: '2026-10-27T15:00:00Z' }],
    changed: ['rateLimits'],
  } as never)

  expect(shown.at(-1)).toBe('Week 41% (resets in 3d 3h)')
})
