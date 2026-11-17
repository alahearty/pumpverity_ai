import { expect, test } from '@playwright/test'

import { E2E_EMAIL as EMAIL, E2E_PASSWORD as PASSWORD, signIn } from './helpers'

const SCREENS = [
  { nav: /dashboard/i, path: '/dashboard', heading: 'Dashboard' },
  { nav: /live monitoring/i, path: '/monitoring', heading: 'Live monitoring' },
  { nav: /ai analysis/i, path: '/analysis', heading: 'AI analysis and prediction' },
  { nav: /alerts & review/i, path: '/alerts', heading: 'Fault alerts and engineering review' },
  { nav: /^pumps/i, path: '/pumps', heading: 'Pump registration' },
  { nav: /sensor health/i, path: '/sensors', heading: 'Sensor health' },
  { nav: /historical trends/i, path: '/history', heading: 'Historical data and trends' },
  { nav: /reports & exports/i, path: '/reports', heading: 'Reports and exports' },
  { nav: /model registry/i, path: '/models', heading: 'Model management' },
  { nav: /system settings/i, path: '/settings', heading: 'System settings' },
  { nav: /user management/i, path: '/users', heading: 'User management' },
]

test.describe('authentication and screen map', () => {
  test.skip(!PASSWORD, 'Set PETROSENSE_E2E_PASSWORD to run the login smoke test.')

  test('redirects unauthenticated visitors to login', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login$/)
    await expect(
      page.getByRole('heading', { name: /sign in to the monitoring workspace/i }),
    ).toBeVisible()
  })

  test('rejects invalid credentials with an auditable error', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Email or username').fill(EMAIL)
    await page.getByLabel('Password', { exact: true }).fill('WrongPass!234')
    await page.getByRole('button', { name: /sign in to workspace/i }).click()
    await expect(page.getByRole('alert')).toContainText('Invalid email/username or password.')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('signs in, navigates the twelve-screen map and signs out', async ({ page }) => {
    await signIn(page)

    const primaryNavigation = page.getByRole('navigation', { name: 'Primary' })
    for (const screen of SCREENS) {
      await primaryNavigation.getByRole('link', { name: screen.nav }).click()
      await expect(page).toHaveURL(new RegExp(`${screen.path}$`))
      await expect(
        page.getByRole('heading', { name: screen.heading, exact: true }),
      ).toBeVisible()
    }

    await expect(page.getByText('Amina Bello').first()).toBeVisible()
    await page.getByRole('button', { name: /sign out/i }).first().click()
    await expect(page).toHaveURL(/\/login$/)
    await expect(
      page.getByRole('heading', { name: /sign in to the monitoring workspace/i }),
    ).toBeVisible()
  })

  test('restores a session after a page reload', async ({ page }) => {
    await signIn(page)
    await page.reload()
    await expect(page).toHaveURL(/\/dashboard$/)
    await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible()
  })
})
