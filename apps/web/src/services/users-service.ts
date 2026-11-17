import type { Page, Role, User } from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export interface UserQuery {
  page?: number
  page_size?: number
  q?: string
  role?: Role | 'ALL'
  is_active?: boolean
}

export function fetchUsers(query: UserQuery = {}): Promise<Page<User>> {
  const params = new URLSearchParams()
  params.set('page', String(query.page ?? 1))
  params.set('page_size', String(query.page_size ?? 25))
  if (query.q?.trim()) params.set('q', query.q.trim())
  if (query.role && query.role !== 'ALL') params.set('role', query.role)
  if (query.is_active !== undefined) params.set('is_active', String(query.is_active))
  return apiFetch<Page<User>>(`/users?${params.toString()}`)
}
