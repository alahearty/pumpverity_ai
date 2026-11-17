import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedLayout, PublicOnly, RequireRole } from '@/components/layout/guards'
import { FullPageLoader } from '@/components/shared/full-page-loader'

const LoginPage = lazy(() =>
  import('@/pages/login-page').then((module) => ({ default: module.LoginPage })),
)
const DashboardPage = lazy(() =>
  import('@/pages/dashboard-page').then((module) => ({ default: module.DashboardPage })),
)
const LiveMonitoringPage = lazy(() =>
  import('@/pages/monitoring-page').then((module) => ({
    default: module.LiveMonitoringPage,
  })),
)
const AnalysisPage = lazy(() =>
  import('@/pages/analysis-page').then((module) => ({ default: module.AnalysisPage })),
)
const AlertsPage = lazy(() =>
  import('@/pages/alerts-page').then((module) => ({ default: module.AlertsPage })),
)
const PumpsPage = lazy(() =>
  import('@/pages/pumps-page').then((module) => ({ default: module.PumpsPage })),
)
const SensorsPage = lazy(() =>
  import('@/pages/sensors-page').then((module) => ({ default: module.SensorsPage })),
)
const HistoryPage = lazy(() =>
  import('@/pages/history-page').then((module) => ({ default: module.HistoryPage })),
)
const ReportsPage = lazy(() =>
  import('@/pages/reports-page').then((module) => ({ default: module.ReportsPage })),
)
const ModelsPage = lazy(() =>
  import('@/pages/models-page').then((module) => ({ default: module.ModelsPage })),
)
const SettingsPage = lazy(() =>
  import('@/pages/settings-page').then((module) => ({ default: module.SettingsPage })),
)
const UsersPage = lazy(() =>
  import('@/pages/users-page').then((module) => ({ default: module.UsersPage })),
)
const NotFoundPage = lazy(() =>
  import('@/pages/not-found-page').then((module) => ({ default: module.NotFoundPage })),
)

function AppRoutes() {
  return (
    <Suspense fallback={<FullPageLoader message="Loading workspace…" />}>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicOnly>
              <LoginPage />
            </PublicOnly>
          }
        />

        <Route element={<ProtectedLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route
            path="monitoring"
            element={
              <RequireRole roles={['ENGINEER', 'RESEARCHER']}>
                <LiveMonitoringPage />
              </RequireRole>
            }
          />
          <Route
            path="analysis"
            element={
              <RequireRole roles={['ENGINEER', 'RESEARCHER']}>
                <AnalysisPage />
              </RequireRole>
            }
          />
          <Route
            path="analysis/:predictionId"
            element={
              <RequireRole roles={['ENGINEER', 'RESEARCHER']}>
                <AnalysisPage />
              </RequireRole>
            }
          />
          <Route
            path="alerts"
            element={
              <RequireRole roles={['ENGINEER', 'REVIEWER']}>
                <AlertsPage />
              </RequireRole>
            }
          />
          <Route
            path="alerts/:alertId"
            element={
              <RequireRole roles={['ENGINEER', 'REVIEWER']}>
                <AlertsPage />
              </RequireRole>
            }
          />
          <Route
            path="pumps"
            element={
              <RequireRole roles={['ENGINEER']}>
                <PumpsPage />
              </RequireRole>
            }
          />
          <Route
            path="pumps/new"
            element={
              <RequireRole roles={['ENGINEER']}>
                <PumpsPage />
              </RequireRole>
            }
          />
          <Route
            path="sensors"
            element={
              <RequireRole roles={['ENGINEER', 'RESEARCHER']}>
                <SensorsPage />
              </RequireRole>
            }
          />
          <Route path="history" element={<HistoryPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route
            path="models"
            element={
              <RequireRole roles={['RESEARCHER']}>
                <ModelsPage />
              </RequireRole>
            }
          />
          <Route
            path="models/:modelId"
            element={
              <RequireRole roles={['RESEARCHER']}>
                <ModelsPage />
              </RequireRole>
            }
          />
          <Route path="settings" element={<SettingsPage />} />
          <Route
            path="users"
            element={
              <RequireRole roles={['ADMINISTRATOR']}>
                <UsersPage />
              </RequireRole>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export { AppRoutes }
