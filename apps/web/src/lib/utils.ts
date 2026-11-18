import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

const HAS_TIMEZONE = /(Z|[+-]\d{2}:?\d{2})$/i

/**
 * Parses an API timestamp. The API stores UTC, but some columns round-trip through SQLite
 * without an offset; a bare ISO string would otherwise be read in the browser's local zone.
 */
export function parseApiDate(value: string): Date {
  const trimmed = value.trim()
  const isoDateTime = /^\d{4}-\d{2}-\d{2}T/.test(trimmed)
  return new Date(isoDateTime && !HAS_TIMEZONE.test(trimmed) ? `${trimmed}Z` : trimmed)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Not recorded'
  const date = parseApiDate(value)
  if (Number.isNaN(date.getTime())) return 'Invalid timestamp'
  return `${new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  }).format(date)} UTC`
}

export function formatScenario(scenario: string | null | undefined): string {
  if (!scenario) return 'Unspecified'
  return scenario
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function formatRole(role: string): string {
  return role
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function pluralise(count: number, singular: string, plural?: string): string {
  return `${count} ${count === 1 ? singular : (plural ?? `${singular}s`)}`
}
