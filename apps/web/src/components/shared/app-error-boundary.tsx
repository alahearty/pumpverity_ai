import { Component, type ErrorInfo, type ReactNode } from 'react'

import { BrandMark } from '@/components/shared/brand-mark'
import { Button } from '@/components/ui/button'

interface AppErrorBoundaryState {
  hasError: boolean
}

class AppErrorBoundary extends Component<{ children: ReactNode }, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('PUMPVERITY UI error', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-canvas px-6">
          <div className="max-w-md space-y-4 rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
            <BrandMark className="mx-auto size-12" />
            <div className="space-y-1.5">
              <h1 className="text-lg font-semibold text-navy-900">The workspace hit an error</h1>
              <p className="text-sm leading-relaxed text-slate-500">
                No operational data has been altered. Reload the application to restore the
                session, or contact the research administrator if the error persists.
              </p>
            </div>
            <Button onClick={() => window.location.reload()}>Reload workspace</Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export { AppErrorBoundary }
