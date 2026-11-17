import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Role, User } from '@petrosense/shared-contracts'

import { ProtectedLayout, RequireRole } from './guards'

const auth = vi.hoisted(() => ({
  status: 'anonymous' as 'loading' | 'authenticated' | 'anonymous',
  user: null as User | null,
  isAuthenticated: false,
  login: async () => {},
  logout: async () => {},
}))

vi.mock('@/providers/auth-provider', () => ({
  useAuth: () => auth,
}))

function makeUser(role: Role): User {
  return {
    id: 'user-1',
    email: 'engineer@petrosense.local',
    username: 'engineer',
    full_name: 'Chinedu Okafor',
    role,
    is_active: true,
    must_change_password: false,
    created_at: '2026-01-01T00:00:00Z',
    last_login_at: null,
  }
}

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>Login screen</div>} />
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<div>Dashboard content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('route guards', () => {
  beforeEach(() => {
    auth.status = 'anonymous'
    auth.user = null
    auth.isAuthenticated = false
    auth.login = async () => {}
    auth.logout = async () => {}
  })

  it('redirects anonymous visitors to login', () => {
    renderProtected()
    expect(screen.getByText('Login screen')).toBeInTheDocument()
  })

  it('shows a session loader while authentication is restored', () => {
    auth.status = 'loading'
    renderProtected()
    expect(screen.getByText(/restoring secure session/i)).toBeInTheDocument()
  })

  it('renders a restricted page when a role is not permitted', () => {
    auth.status = 'authenticated'
    auth.user = makeUser('ENGINEER')
    auth.isAuthenticated = true

    render(
      <MemoryRouter>
        <RequireRole roles={['ADMINISTRATOR']}>
          <div>Administrator content</div>
        </RequireRole>
      </MemoryRouter>,
    )

    expect(screen.getByText('Restricted area')).toBeInTheDocument()
    expect(screen.queryByText('Administrator content')).not.toBeInTheDocument()
  })

  it('allows an administrator through a role-specific guard', () => {
    auth.status = 'authenticated'
    auth.user = makeUser('ADMINISTRATOR')
    auth.isAuthenticated = true

    render(
      <MemoryRouter>
        <RequireRole roles={['ENGINEER']}>
          <div>Engineering content</div>
        </RequireRole>
      </MemoryRouter>,
    )

    expect(screen.getByText('Engineering content')).toBeInTheDocument()
  })
})
