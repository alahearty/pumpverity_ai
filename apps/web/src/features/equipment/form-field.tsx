import type { ReactNode } from 'react'

import { Label } from '@/components/ui/label'

interface FormFieldProps {
  label: string
  htmlFor: string
  error?: string
  hint?: string
  children: ReactNode
  className?: string
}

function FormField({ label, htmlFor, error, hint, children, className }: FormFieldProps) {
  return (
    <div className={className}>
      <div className="space-y-1.5">
        <Label htmlFor={htmlFor}>{label}</Label>
        {children}
        {error ? (
          <p id={`${htmlFor}-error`} className="text-xs font-medium text-fault">
            {error}
          </p>
        ) : hint ? (
          <p className="text-[11px] leading-relaxed text-slate-400">{hint}</p>
        ) : null}
      </div>
    </div>
  )
}

export { FormField }
