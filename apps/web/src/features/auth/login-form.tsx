import { zodResolver } from '@hookform/resolvers/zod'
import { AlertCircle, Eye, EyeOff, Loader2, LockKeyhole, UserRound } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiClientError } from '@/lib/api'

const loginSchema = z.object({
  identifier: z
    .string()
    .trim()
    .min(3, 'Enter your email address or username.')
    .max(255, 'This value is too long.'),
  password: z
    .string()
    .min(8, 'Password must contain at least 8 characters.')
    .max(128, 'Password is too long.'),
})

export type LoginValues = z.infer<typeof loginSchema>

interface LoginFormProps {
  onSubmit: (values: LoginValues) => Promise<void>
}

function LoginForm({ onSubmit }: LoginFormProps) {
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState<{ message: string; requestId: string | null } | null>(
    null,
  )
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: '', password: '' },
  })

  async function submit(values: LoginValues) {
    setServerError(null)
    try {
      await onSubmit(values)
    } catch (error) {
      if (error instanceof ApiClientError) {
        setServerError({ message: error.message, requestId: error.requestId })
      } else {
        setServerError({
          message: 'The monitoring server could not be reached. Check the local API and retry.',
          requestId: null,
        })
      }
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit(submit)} noValidate>
      {serverError ? (
        <div
          role="alert"
          className="flex gap-2.5 rounded-lg border border-red-200 bg-fault-soft px-3.5 py-3 text-sm text-red-800"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <div className="space-y-1">
            <p className="font-medium">{serverError.message}</p>
            {serverError.requestId ? (
              <p className="font-mono text-[10px] text-red-700/70">
                Request ID: {serverError.requestId}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="space-y-1.5">
        <Label htmlFor="identifier">Email or username</Label>
        <div className="relative">
          <UserRound
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
            aria-hidden="true"
          />
          <Input
            id="identifier"
            autoComplete="username"
            placeholder="name@petrosense.local"
            className="pl-9"
            aria-invalid={Boolean(errors.identifier)}
            aria-describedby={errors.identifier ? 'identifier-error' : undefined}
            {...register('identifier')}
          />
        </div>
        {errors.identifier ? (
          <p id="identifier-error" className="text-xs font-medium text-fault">
            {errors.identifier.message}
          </p>
        ) : null}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <LockKeyhole
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
            aria-hidden="true"
          />
          <Input
            id="password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="Enter your password"
            className="px-9"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
          <button
            type="button"
            onClick={() => setShowPassword((current) => !current)}
            className="absolute right-2 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
        {errors.password ? (
          <p id="password-error" className="text-xs font-medium text-fault">
            {errors.password.message}
          </p>
        ) : null}
      </div>

      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            Signing in…
          </>
        ) : (
          'Sign in to workspace'
        )}
      </Button>

      <p className="text-center text-[11px] leading-relaxed text-slate-400">
        Accounts are provisioned locally by the research administrator. Failed attempts are
        recorded in the audit log.
      </p>
    </form>
  )
}

export { LoginForm }
