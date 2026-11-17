import type { HealthStatus } from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export function fetchHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>('/health')
}
