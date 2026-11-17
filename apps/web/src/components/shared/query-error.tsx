import { AlertTriangle, RotateCcw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ApiClientError } from '@/lib/api'
import { cn } from '@/lib/utils'

interface QueryErrorProps {
  error: unknown
  onRetry?: () => void
  className?: string
}

function QueryError({ error, onRetry, className }: QueryErrorProps) {
  const message =
    error instanceof ApiClientError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'The request could not be completed.'
  const requestId = error instanceof ApiClientError ? error.requestId : null

  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-start gap-3 rounded-2xl border border-red-200/80 bg-gradient-to-b from-red-50 to-white p-5 text-sm shadow-[0_16px_40px_-34px_rgba(120,20,20,0.4)]',
        className,
      )}
    >
      <div className="flex items-center gap-2 font-semibold text-red-800">
        <AlertTriangle className="size-4" aria-hidden="true" />
        Unable to load data
      </div>
      <p className="text-red-800/80">{message}</p>
      {requestId ? (
        <p className="font-mono text-[11px] text-red-700/70">Request ID: {requestId}</p>
      ) : null}
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RotateCcw className="size-3.5" aria-hidden="true" />
          Retry
        </Button>
      ) : null}
    </div>
  )
}

export { QueryError }
