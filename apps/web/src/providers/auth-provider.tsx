import type { AuthSession, LoginRequest, User } from '@petrosense/shared-contracts'
import { createContext, use, useEffect, useMemo, useState, type ReactNode } from 'react'

import {
  loginWithPassword,
  logoutSession,
  refreshSession,
  setSessionListener,
} from '@/lib/api'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthState {
  status: AuthStatus
  user: User | null
}

interface AuthContextValue extends AuthState {
  isAuthenticated: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function stateFromSession(session: AuthSession | null): AuthState {
  return session
    ? { status: 'authenticated', user: session.user }
    : { status: 'anonymous', user: null }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading', user: null })

  useEffect(() => {
    let active = true
    setSessionListener((session) => {
      if (active) setState(stateFromSession(session))
    })
    refreshSession().catch(() => {
      if (active) setState({ status: 'anonymous', user: null })
    })
    return () => {
      active = false
      setSessionListener(null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      isAuthenticated: state.status === 'authenticated',
      login: async (credentials) => {
        const session = await loginWithPassword(credentials)
        setState(stateFromSession(session))
      },
      logout: async () => {
        await logoutSession()
        setState({ status: 'anonymous', user: null })
      },
    }),
    [state],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth(): AuthContextValue {
  const context = use(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
