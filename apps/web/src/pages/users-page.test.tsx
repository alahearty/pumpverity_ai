import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { UsersPage } from './users-page'

const fetchUsers = vi.hoisted(() => vi.fn())

vi.mock('@/services/users-service', () => ({
  fetchUsers,
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <UsersPage />
    </QueryClientProvider>,
  )
}

const user = {
  id: 'user-1',
  email: 'admin@petrosense.local',
  username: 'admin',
  full_name: 'Amina Bello',
  role: 'ADMINISTRATOR' as const,
  is_active: true,
  must_change_password: false,
  created_at: '2026-01-01T00:00:00Z',
  last_login_at: '2026-11-16T10:00:00Z',
}

describe('UsersPage', () => {
  beforeEach(() => {
    fetchUsers.mockReset()
  })

  it('renders accounts returned by the administrator API', async () => {
    fetchUsers.mockResolvedValue({ items: [user], total: 1, page: 1, page_size: 10 })
    renderPage()

    expect(await screen.findByText('Amina Bello')).toBeInTheDocument()
    expect(screen.getByText('admin@petrosense.local')).toBeInTheDocument()
    expect(screen.getByText('Showing 1–1 of 1')).toBeInTheDocument()
  })

  it('shows an honest empty state when filters match no accounts', async () => {
    fetchUsers.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    renderPage()

    expect(await screen.findByText('No accounts match the filters')).toBeInTheDocument()
  })

  it('shows an API error with retry affordance', async () => {
    fetchUsers.mockRejectedValue(new Error('Network unavailable'))
    renderPage()

    expect(await screen.findByText('Unable to load data')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })
})
