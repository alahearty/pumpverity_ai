import { describe, expect, it } from 'vitest'

import { formatDateTime, parseApiDate } from '@/lib/utils'

describe('parseApiDate', () => {
  it('treats offset-less API timestamps as UTC', () => {
    expect(parseApiDate('2026-11-17T19:55:19.091852').toISOString()).toBe(
      '2026-11-17T19:55:19.091Z',
    )
  })

  it('keeps explicit offsets', () => {
    expect(parseApiDate('2026-11-17T19:55:00+01:00').toISOString()).toBe(
      '2026-11-17T18:55:00.000Z',
    )
    expect(parseApiDate('2026-11-17T19:55:00Z').toISOString()).toBe('2026-11-17T19:55:00.000Z')
  })

  it('formats naive and aware forms of the same instant identically', () => {
    expect(formatDateTime('2026-11-17T19:55:19')).toBe(formatDateTime('2026-11-17T19:55:19Z'))
    expect(formatDateTime('2026-11-17T19:55:19Z')).toBe('17 Nov 2026, 19:55 UTC')
  })
})
