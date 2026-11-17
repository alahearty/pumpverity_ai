import type { Role } from '@petrosense/shared-contracts'
import {
  Activity,
  BellRing,
  Boxes,
  BrainCircuit,
  FileBarChart,
  Gauge,
  History,
  LayoutDashboard,
  Radar,
  Settings,
  Users,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  stage?: number
  roles?: Role[]
  end?: boolean
}

export interface NavSection {
  label: string
  items: NavItem[]
}

export const NAV_SECTIONS: NavSection[] = [
  {
    label: 'Overview',
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard, end: true },
    ],
  },
  {
    label: 'Operations',
    items: [
      {
        label: 'Live Monitoring',
        to: '/monitoring',
        icon: Activity,
        roles: ['ENGINEER', 'RESEARCHER'],
      },
      {
        label: 'AI Analysis',
        to: '/analysis',
        icon: BrainCircuit,
        roles: ['ENGINEER', 'RESEARCHER'],
      },
      {
        label: 'Alerts & Review',
        to: '/alerts',
        icon: BellRing,
        roles: ['ENGINEER', 'REVIEWER'],
      },
    ],
  },
  {
    label: 'Assets',
    items: [
      { label: 'Pumps', to: '/pumps', icon: Gauge, roles: ['ENGINEER'] },
      {
        label: 'Sensor Health',
        to: '/sensors',
        icon: Radar,
        roles: ['ENGINEER', 'RESEARCHER'],
      },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { label: 'Historical Trends', to: '/history', icon: History },
      { label: 'Reports & Exports', to: '/reports', icon: FileBarChart },
    ],
  },
  {
    label: 'Governance',
    items: [
      { label: 'Model Registry', to: '/models', icon: Boxes, roles: ['RESEARCHER'] },
      { label: 'System Settings', to: '/settings', icon: Settings, stage: 7 },
      { label: 'User Management', to: '/users', icon: Users, roles: ['ADMINISTRATOR'] },
    ],
  },
]

export const ROUTE_META: Record<string, { section: string; title: string }> = {
  '/dashboard': { section: 'Overview', title: 'Dashboard' },
  '/monitoring': { section: 'Operations', title: 'Live Monitoring' },
  '/analysis': { section: 'Operations', title: 'AI Analysis' },
  '/alerts': { section: 'Operations', title: 'Alerts & Review' },
  '/pumps': { section: 'Assets', title: 'Pump Registry' },
  '/sensors': { section: 'Assets', title: 'Sensor Health' },
  '/history': { section: 'Analysis', title: 'Historical Trends' },
  '/reports': { section: 'Analysis', title: 'Reports & Exports' },
  '/models': { section: 'Governance', title: 'Model Registry' },
  '/settings': { section: 'Governance', title: 'System Settings' },
  '/users': { section: 'Governance', title: 'User Management' },
}

export function canAccess(role: Role | undefined, roles?: Role[]): boolean {
  if (!role) return false
  if (!roles) return true
  return role === 'ADMINISTRATOR' || roles.includes(role)
}

export function routeMeta(pathname: string): { section: string; title: string } {
  if (ROUTE_META[pathname]) return ROUTE_META[pathname]
  const base = Object.keys(ROUTE_META).find(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  )
  return base ? ROUTE_META[base] : { section: 'PUMPVERITY AI', title: 'Page' }
}

