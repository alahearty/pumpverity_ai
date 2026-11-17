import { Suspense, useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import { EngineeringCopilot } from '@/components/copilot/engineering-copilot'
import { PresenterDock } from '@/components/demo/presenter-dock'
import { Sidebar } from '@/components/layout/sidebar'
import { Topbar } from '@/components/layout/topbar'
import { PageHeader } from '@/components/shared/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/providers/auth-provider'
import { CopilotContextProvider } from '@/providers/copilot-context-provider'

function RouteLoading() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Loading view"
        description="Preparing the next authenticated workspace."
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-80 w-full" />
    </div>
  )
}

function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [logoutPending, setLogoutPending] = useState(false)
  const { logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [location.pathname])

  async function handleLogout() {
    setLogoutPending(true)
    try {
      await logout()
      navigate('/login', { replace: true })
    } finally {
      setLogoutPending(false)
    }
  }

  return (
    <CopilotContextProvider>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="min-h-screen bg-canvas">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onLogout={handleLogout}
        />
        <div className="flex min-h-screen flex-col lg:pl-72">
          <Topbar
            onMenuClick={() => setSidebarOpen(true)}
            onLogout={handleLogout}
            logoutPending={logoutPending}
          />
          <main
            id="main-content"
            tabIndex={-1}
            className="mx-auto w-full max-w-[1560px] flex-1 px-4 py-6 outline-none sm:px-6 lg:px-8 lg:py-8"
          >
            <Suspense fallback={<RouteLoading />}>
              <Outlet />
            </Suspense>
          </main>
          <footer className="mx-auto w-full max-w-[1560px] border-t border-slate-200/60 px-4 py-5 text-[10px] leading-relaxed text-slate-400 sm:px-6 lg:px-8">
            <p>
              PUMPVERITY AI is an academic research prototype. It is not certified for industrial
              safety, automatic shutdown or predictive-maintenance decisions. Simulated and
              experimental data are kept distinct.
            </p>
          </footer>
          <PresenterDock />
        </div>
      </div>
      <EngineeringCopilot />
    </CopilotContextProvider>
  )
}

export { AppShell }
