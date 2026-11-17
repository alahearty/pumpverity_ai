import { Loader2 } from 'lucide-react'

import { BrandMark } from '@/components/shared/brand-mark'

function FullPageLoader({ message = 'Restoring secure session…' }: { message?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <BrandMark className="size-14" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-navy-900">PUMPVERITY AI</p>
          <p className="flex items-center justify-center gap-2 text-xs text-slate-500">
            <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
            {message}
          </p>
        </div>
      </div>
    </div>
  )
}

export { FullPageLoader }
