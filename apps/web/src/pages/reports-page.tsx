import { useQuery } from '@tanstack/react-query'
import type { ReportJob } from '@petrosense/shared-contracts'
import {
  Bot,
  Download,
  FileBarChart,
  FileText,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { QueryError } from '@/components/shared/query-error'
import { ResearchNotice } from '@/components/shared/research-notice'
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
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { downloadReport, fetchReports } from '@/services/reports-service'
import { formatDateTime } from '@/lib/utils'

function reportTypeLabel(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function DownloadButton({ report }: { report: ReportJob }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const available =
    report.status === 'COMPLETED' && Boolean(report.file_name)
  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        variant="secondary"
        size="sm"
        disabled={!available || busy}
        onClick={async () => {
          setBusy(true)
          setError(null)
          try {
            await downloadReport(report)
          } catch (caught) {
            setError(
              caught instanceof Error ? caught.message : 'Download failed.',
            )
          } finally {
            setBusy(false)
          }
        }}
      >
        <Download className="size-3.5" aria-hidden="true" />
        Download
      </Button>
      {error ? <span className="text-[10px] text-fault">{error}</span> : null}
    </div>
  )
}

function ReportsPage() {
  const [searchParams] = useSearchParams()
  const highlightedId = searchParams.get('reportId')
  const reportsQuery = useQuery({
    queryKey: ['reports', { page: 1, page_size: 100 }],
    queryFn: () => fetchReports({ page: 1, page_size: 100 }),
    refetchInterval: 30_000,
  })
  const reports = reportsQuery.data?.items ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Analysis"
        title="Reports and exports"
        description="Immutable report artefacts generated through the authorised Engineering Copilot MCP tool. Downloads remain traceable to the requester and dataset provenance."
        badge={<Badge variant="info">Copilot reporting foundation</Badge>}
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => reportsQuery.refetch()}
            disabled={reportsQuery.isFetching}
          >
            <RefreshCw className="size-3.5" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs leading-relaxed text-amber-950">
        <ShieldAlert className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden="true" />
        <p>
          Reports are generated from persisted monitoring evidence. Simulated records remain
          explicitly disclosed and cannot be presented as real-pump performance or verified
          experimental measurements.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-row items-start justify-between gap-3">
          <div>
            <CardTitle>Generated monitoring reports</CardTitle>
            <CardDescription>
              Ask the Engineering Copilot to prepare a report. A confirmation is required before
              the MCP write tool creates the artefact.
            </CardDescription>
          </div>
          <Badge variant="neutral">{reportsQuery.data?.total ?? 0}</Badge>
        </CardHeader>
        <CardContent className="p-0">
          {reportsQuery.isError ? (
            <div className="p-5">
              <QueryError
                error={reportsQuery.error}
                onRetry={() => reportsQuery.refetch()}
              />
            </div>
          ) : reportsQuery.isPending ? (
            <div className="space-y-2 p-5">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : reports.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={FileBarChart}
                title="No generated reports"
                description="Open the Engineering Copilot, select a pump and ask it to generate a monitoring report. The copilot will require confirmation before writing."
                action={
                  <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
                    <Bot className="size-3.5" aria-hidden="true" />
                    Use the Copilot button in the lower-right corner.
                  </span>
                }
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/70">
                  <TableHead>Report</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Requested by</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Provenance</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead aria-label="Actions" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report) => (
                  <TableRow
                    key={report.id}
                    className={
                      report.id === highlightedId
                        ? 'bg-industrial-50/80'
                        : undefined
                    }
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileText className="size-4 text-slate-400" aria-hidden="true" />
                        <div>
                          <p className="font-mono text-xs font-semibold text-navy-900">
                            {report.id.slice(0, 8)}
                          </p>
                          {report.id === highlightedId ? (
                            <Badge variant="info" className="mt-1">
                              Opened by Copilot
                            </Badge>
                          ) : null}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-slate-600">
                      {reportTypeLabel(report.report_type)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={report.status} />
                    </TableCell>
                    <TableCell className="text-xs text-slate-600">
                      {report.requested_by_name ?? 'Unknown'}
                    </TableCell>
                    <TableCell className="text-xs text-slate-600">
                      {formatDateTime(report.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={report.includes_simulated_data ? 'uncertain' : 'success'}
                      >
                        {report.includes_simulated_data
                          ? 'Includes simulated'
                          : 'Experimental only'}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-40 truncate font-mono text-[10px] text-slate-500">
                      {report.file_name ?? report.error_message ?? 'Unavailable'}
                      {report.file_sha256 ? (
                        <p className="mt-1 text-[9px] text-slate-400">
                          SHA-256 {report.file_sha256.slice(0, 12)}…
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <DownloadButton report={report} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ResearchNotice compact />
    </div>
  )
}

export { ReportsPage }
