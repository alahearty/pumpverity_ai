import type { SystemInfo } from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export function fetchSystemInfo(): Promise<SystemInfo> {
  return apiFetch<SystemInfo>('/system/info')
}
