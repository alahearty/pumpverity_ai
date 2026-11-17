import { describe, expect, it } from 'vitest'

import { canAccess, routeMeta } from './navigation'

describe('navigation access rules', () => {
  it('allows administrators to access every declared role area', () => {
    expect(canAccess('ADMINISTRATOR', ['ENGINEER'])).toBe(true)
    expect(canAccess('ADMINISTRATOR', ['REVIEWER'])).toBe(true)
    expect(canAccess('ADMINISTRATOR', undefined)).toBe(true)
  })

  it('enforces role-specific areas', () => {
    expect(canAccess('ENGINEER', ['ENGINEER', 'RESEARCHER'])).toBe(true)
    expect(canAccess('ENGINEER', ['RESEARCHER'])).toBe(false)
    expect(canAccess('REVIEWER', ['ENGINEER', 'REVIEWER'])).toBe(true)
    expect(canAccess('RESEARCHER', ['ENGINEER', 'REVIEWER'])).toBe(false)
  })

  it('denies access without an authenticated role', () => {
    expect(canAccess(undefined, undefined)).toBe(false)
    expect(canAccess(undefined, ['ENGINEER'])).toBe(false)
  })

  it('resolves detail routes to their parent screen metadata', () => {
    expect(routeMeta('/alerts/alert-001')).toEqual({
      section: 'Operations',
      title: 'Alerts & Review',
    })
    expect(routeMeta('/unknown')).toEqual({ section: 'PUMPVERITY AI', title: 'Page' })
  })
})
