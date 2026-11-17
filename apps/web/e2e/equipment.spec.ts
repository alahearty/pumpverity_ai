import { expect, test } from '@playwright/test'

import { ALLOW_WRITES, E2E_PASSWORD, signIn } from './helpers'

test.describe('equipment workflow', () => {
  test.skip(!E2E_PASSWORD, 'Set PETROSENSE_E2E_PASSWORD to run equipment UI tests.')

  test('opens pump registration and validates required identity fields', async ({ page }) => {
    await signIn(page)
    await page.getByRole('link', { name: /^pumps/i }).click()
    await expect(page.getByRole('heading', { name: 'Pump registration', exact: true })).toBeVisible()

    await page.getByRole('button', { name: /register pump/i }).click()
    await expect(page.getByRole('heading', { name: /register laboratory pump/i })).toBeVisible()
    await page.getByRole('button', { name: /register pump and sensor/i }).click()

    await expect(page.getByText('Pump code is required.')).toBeVisible()
    await expect(page.getByText('Sensor code is required.')).toBeVisible()

    await page.getByRole('button', { name: /cancel/i }).click()
    await expect(page.getByRole('button', { name: /register pump/i })).toBeVisible()
  })

  test('registers a pump and sensor through the UI', async ({ page }) => {
    test.skip(!ALLOW_WRITES, 'Set PETROSENSE_E2E_ALLOW_WRITES=1 to run write tests.')

    const suffix = Date.now()
    const pumpCode = `E2E-${suffix}`
    const sensorCode = `E2E-VIB-${suffix}`

    await signIn(page)
    await page.getByRole('link', { name: /^pumps/i }).click()
    await page.getByRole('button', { name: /register pump/i }).click()

    await page.getByLabel('Pump ID').fill(pumpCode)
    await page.getByLabel('Pump name').fill('End-to-end Test Pump')
    await page.getByLabel('Sensor ID').fill(sensorCode)
    await page.getByRole('button', { name: /register pump and sensor/i }).click()

    await expect(page.getByText(new RegExp(`Registered ${pumpCode}`))).toBeVisible()
    await expect(page.getByText(pumpCode, { exact: true })).toBeVisible()
    await expect(page.getByText(sensorCode, { exact: true })).toBeVisible()

    await page.getByRole('link', { name: /sensor health/i }).click()
    await expect(page.getByRole('heading', { name: 'Sensor health', exact: true })).toBeVisible()
    await expect(page.getByText(sensorCode, { exact: true })).toBeVisible()
  })
})
