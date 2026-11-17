import type { Page, ReportJob } from '@petrosense/shared-contracts'

import { apiFetch, downloadAuthenticatedFile } from '@/lib/api'

export function fetchReports(
  query: { page?: number; page_size?: number } = {},
): Promise<Page<ReportJob>> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    page_size: String(query.page_size ?? 50),
  })
  return apiFetch<Page<ReportJob>>(`/reports?${params.toString()}`)
}

export function downloadReport(report: ReportJob): Promise<void> {
  return downloadAuthenticatedFile(
    `/reports/${report.id}/download`,
    report.file_name ?? `${report.id}.json`,
  )
}
