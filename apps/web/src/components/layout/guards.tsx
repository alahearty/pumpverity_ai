import type { Role } from '@petrosense/shared-contracts'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { AppShell } from '@/components/layout/app-shell'
import { FullPageLoader } from '@/components/shared/full-page-loader'
import { UnauthorizedPage } from '@/pages/unauthorized-page'
import { useAuth } from '@/providers/auth-provider'
import { canAccess } from '@/routes/navigation'

function ProtectedLayout() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <FullPageLoader />
  if (status !== 'authenticated') {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  }
  return <AppShell />
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') return <FullPageLoader message="Checking session…" />
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />
  return children
}

function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return null
  if (!canAccess(user.role, roles)) return <UnauthorizedPage requiredRoles={roles} />
  return children
}

export { ProtectedLayout, PublicOnly, RequireRole }
