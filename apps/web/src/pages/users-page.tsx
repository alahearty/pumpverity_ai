import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Role } from '@petrosense/shared-contracts'
import {
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Search,
  ShieldCheck,
  UserRoundCog,
  Users,
} from 'lucide-react'
import { useState } from 'react'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { QueryError } from '@/components/shared/query-error'
import { StatusBadge } from '@/components/shared/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { fetchUsers } from '@/services/users-service'
import { formatDateTime, formatRole, initials, pluralise } from '@/lib/utils'

const PAGE_SIZE = 10
const ROLES: Role[] = ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER', 'REVIEWER']

function UsersPage() {
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<Role | 'ALL'>('ALL')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebouncedValue(search)

  const usersQuery = useQuery({
    queryKey: ['users', { page, search: debouncedSearch, role }],
    queryFn: () => fetchUsers({ page, page_size: PAGE_SIZE, q: debouncedSearch, role }),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  })

  const data = usersQuery.data
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const first = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const last = Math.min(page * PAGE_SIZE, total)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="User management"
        description="Accounts and roles provisioned for the research team. This build exposes a read-only administrator view; account changes are not available in this build."
        badge={<Badge variant="outline">Read-only</Badge>}
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => usersQuery.refetch()}
            disabled={usersQuery.isFetching}
          >
            <RotateCcw className="size-3.5" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-accent-200/70 bg-accent-50/60 p-4">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-accent-700" aria-hidden="true" />
        <div className="space-y-1 text-xs leading-relaxed text-accent-900">
          <p className="font-semibold">Backend-enforced access</p>
          <p className="text-accent-900/75">
            This list is available only to administrators. Engineer, researcher and reviewer
            accounts receive a forbidden response from the API even if they navigate directly to
            this route.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="gap-4 border-b border-slate-100 pb-4">
          <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Accounts</CardTitle>
              <CardDescription>
                {data ? pluralise(total, 'account') : 'Loading accounts…'}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-slate-400">
              <UserRoundCog className="size-3.5" aria-hidden="true" />
              Creation, deactivation and resets: not available
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden="true"
              />
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setPage(1)
                }}
                placeholder="Search name, email or username"
                className="pl-9"
                aria-label="Search accounts"
              />
            </div>
            <Select
              value={role}
              onChange={(event) => {
                setRole(event.target.value as Role | 'ALL')
                setPage(1)
              }}
              aria-label="Filter by role"
              className="sm:w-52"
            >
              <option value="ALL">All roles</option>
              {ROLES.map((option) => (
                <option key={option} value={option}>
                  {formatRole(option)}
                </option>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {usersQuery.isError ? (
            <div className="p-5">
              <QueryError error={usersQuery.error} onRetry={() => usersQuery.refetch()} />
            </div>
          ) : usersQuery.isPending ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="flex items-center gap-4">
                  <Skeleton className="size-9 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-3.5 w-44" />
                    <Skeleton className="h-3 w-64" />
                  </div>
                  <Skeleton className="h-6 w-24" />
                </div>
              ))}
            </div>
          ) : data && data.items.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Users}
                title="No accounts match the filters"
                description="Adjust the search term or role filter. The four seeded research accounts remain available in the database."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/70">
                  <TableHead>Account</TableHead>
                  <TableHead className="hidden md:table-cell">Username</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="hidden lg:table-cell">Last sign-in</TableHead>
                  <TableHead className="hidden xl:table-cell">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-navy-900/5 text-[11px] font-semibold text-navy-800">
                          {initials(user.full_name)}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-navy-900">
                            {user.full_name}
                          </p>
                          <p className="truncate text-xs text-slate-500">{user.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="hidden font-mono text-xs text-slate-500 md:table-cell">
                      {user.username}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={user.role} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={user.is_active ? 'ACTIVE' : 'INACTIVE'} />
                    </TableCell>
                    <TableCell className="hidden text-xs text-slate-500 lg:table-cell">
                      {formatDateTime(user.last_login_at)}
                    </TableCell>
                    <TableCell className="hidden text-xs text-slate-500 xl:table-cell">
                      {formatDateTime(user.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          <div className="flex flex-col gap-3 border-t border-slate-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-slate-500">
              {data ? `Showing ${first}–${last} of ${total}` : '—'}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1 || usersQuery.isFetching}
              >
                <ChevronLeft className="size-3.5" aria-hidden="true" />
                Previous
              </Button>
              <span className="px-1 text-xs text-slate-500">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page >= totalPages || usersQuery.isFetching}
              >
                Next
                <ChevronRight className="size-3.5" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export { UsersPage }

