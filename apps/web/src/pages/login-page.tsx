import {
  Activity,
  Bot,
  BrainCircuit,
  ShieldCheck,
  WifiOff,
} from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { BrandMark } from '@/components/shared/brand-mark'
import { ResearchNotice } from '@/components/shared/research-notice'
import { Badge } from '@/components/ui/badge'
import { LoginForm, type LoginValues } from '@/features/auth/login-form'
import { useAuth } from '@/providers/auth-provider'

interface LocationState {
  from?: string
}

function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const requestedDestination = (location.state as LocationState | null)?.from
  const destination =
    requestedDestination?.startsWith('/') && !requestedDestination.startsWith('//')
      ? requestedDestination
      : '/dashboard'

  async function handleLogin(values: LoginValues) {
    await login(values)
    navigate(destination, { replace: true })
  }

  return (
    <div className="min-h-screen bg-canvas lg:grid lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-navy-950 via-navy-900 to-navy-800 px-12 py-10 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute inset-0 bg-grid-dark opacity-60" />
        <div className="pointer-events-none absolute -right-24 top-1/4 size-96 rounded-full bg-accent-500/10 blur-3xl" />
        <div className="relative z-10 flex items-center gap-3">
          <BrandMark className="size-11 bg-white/5" />
          <div>
            <p className="text-sm font-semibold tracking-tight">PUMPVERITY AI</p>
            <p className="text-[11px] text-slate-400">Condition Intelligence</p>
          </div>
        </div>

        <div className="relative z-10 my-auto max-w-xl space-y-8 py-12">
          <Badge variant="navy" className="border-accent-500/30 bg-accent-500/10 text-accent-100">
            Uncertainty-aware edge monitoring
          </Badge>
          <div className="space-y-4">
            <h1 className="text-balance text-4xl font-semibold leading-[1.12] tracking-tight text-white">
              Evidence-led condition monitoring for centrifugal pumps.
            </h1>
            <p className="max-w-lg text-sm leading-relaxed text-slate-300">
              A low-cost research platform for vibration-based fault detection that distinguishes
              equipment condition, sensor validity and connectivity — without pretending they are
              the same thing.
            </p>
          </div>
          <ul className="space-y-4">
            <li className="flex gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-accent-200">
                <Activity className="size-4" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Signal quality before inference</p>
                <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
                  Invalid or disconnected sensors suppress equipment-condition decisions.
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-accent-200">
                <BrainCircuit className="size-4" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Normal, fault or explicit uncertainty</p>
                <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
                  Abstention is a first-class outcome, not a hidden confidence cut-off.
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-accent-200">
                <WifiOff className="size-4" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Offline-first by design</p>
                <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
                  Edge inference and buffering continue when the monitoring server is unavailable.
                </p>
              </div>
            </li>
          </ul>
        </div>

        <div className="relative z-10 space-y-3">
          <ResearchNotice variant="dark" />
          <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
            NCDMB-oriented indigenous technology research
          </p>
        </div>
      </aside>

      <main className="flex min-h-screen flex-col items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md space-y-8">
          <div className="flex items-center gap-3 lg:hidden">
            <BrandMark className="size-10" />
            <div>
              <p className="text-sm font-semibold text-navy-900">PUMPVERITY AI</p>
              <p className="text-[11px] text-slate-500">Condition Intelligence</p>
            </div>
          </div>

          <div className="space-y-2">
            <Badge variant="accent" className="gap-1.5">
              <ShieldCheck className="size-3" aria-hidden="true" />
              Secure local session
            </Badge>
            <h2 className="text-2xl font-semibold tracking-tight text-navy-900">
              Sign in to the monitoring workspace
            </h2>
            <p className="text-sm leading-relaxed text-slate-500">
              Authorised research team access only. All monitoring views are served from the local
              PUMPVERITY API and its database.
            </p>
          </div>

          <LoginForm onSubmit={handleLogin} />

          <details className="rounded-xl border border-industrial-200 bg-industrial-50/70 p-4 text-xs text-industrial-900">
            <summary className="flex cursor-pointer items-center gap-2 font-semibold">
              <Bot className="size-4" aria-hidden="true" />
              Engineering Copilot - sign-in help
            </summary>
            <p className="mt-2 leading-relaxed text-industrial-900/80">
              The Engineering Copilot becomes available after authentication. It never asks for
              your password, token or API key, and it cannot access monitoring MCP tools from this
              public screen. Check the seeded email/username and the password configured in the
              local API environment; never share credentials in a chat.
            </p>
          </details>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex gap-3">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-accent-600" aria-hidden="true" />
              <div className="space-y-1 text-[11px] leading-relaxed text-slate-500">
                <p className="font-semibold text-navy-900">Session handling</p>
                <p>
                  Access tokens are held in memory. The refresh session uses an HttpOnly cookie
                  scoped to the authentication endpoints. Roles are enforced by the backend.
                </p>
              </div>
            </div>
          </div>

          <p className="text-center text-[10px] leading-relaxed text-slate-400">
            PUMPVERITY AI research prototype · Not for certified industrial safety use
          </p>
        </div>
      </main>
    </div>
  )
}

export { LoginPage }
