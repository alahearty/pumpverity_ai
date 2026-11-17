import { expect, test } from '@playwright/test'

import {
  ALLOW_WRITES,
  E2E_EMAIL,
  E2E_PASSWORD,
  runSimulator,
  signIn,
} from './helpers'

test.describe('live monitoring and SSE', () => {
  test.skip(
    !E2E_PASSWORD || !ALLOW_WRITES,
    'Set PETROSENSE_E2E_PASSWORD and PETROSENSE_E2E_ALLOW_WRITES=1 to run live update tests.',
  )

  test('updates the live view after a new simulated scenario', async ({ page, request }) => {
    test.setTimeout(120_000)
    const suffix = Date.now()
    const pumpCode = `E2E-LIVE-${suffix}`
    const sensorCode = `E2E-LIVE-VIB-${suffix}`

    const login = await request.post('/api/v1/auth/login', {
      data: { identifier: E2E_EMAIL, password: E2E_PASSWORD },
    })
    expect(login.ok()).toBeTruthy()
    const token = (await login.json()).access_token as string
    const headers = { Authorization: `Bearer ${token}` }
    const activeResponse = await request.get('/api/v1/models/active', { headers })
    const activeModel = await activeResponse.json()
    test.skip(!activeModel, 'An active Stage 4 model is required for this live inference test.')

    const created = await request.post('/api/v1/pumps', {
      headers,
      data: {
        pump_code: pumpCode,
        name: 'E2E SSE Pump',
        pump_type: 'CENTRIFUGAL',
        location: 'Thermofluids Laboratory',
        rated_speed_rpm: 2900,
        status: 'ACTIVE',
        sensor: {
          sensor_code: sensorCode,
          sensor_type: 'VIBRATION',
          mounting_axis: 'RADIAL_X',
          mounting_position: 'Drive-end bearing housing',
          sampling_rate_hz: 2048,
        },
      },
    })
    expect(created.ok()).toBeTruthy()

    runSimulator([
      '--email',
      E2E_EMAIL,
      '--pump-code',
      pumpCode,
      '--sensor-code',
      sensorCode,
      '--scenario',
      'normal',
      '--windows',
      '2',
      '--seed',
      '17',
    ])

    await signIn(page)
    await page.getByRole('link', { name: /live monitoring/i }).click()
    await page
      .getByLabel('Pump')
      .selectOption({ label: `${pumpCode} — E2E SSE Pump` })

    await expect(page.getByText('Live stream connected')).toBeVisible()
    await expect(page.getByText('Normal').first()).toBeVisible()
    await expect(page.getByText('Latest AI decision')).toBeVisible()
    await expect(
      page.getByText(/PUMPVERITY lightweight linear v0\.1\.0/).first(),
    ).toBeVisible()
    await expect(page.getByText('No live channel').first()).toBeVisible()

    await page.waitForTimeout(1500)

    runSimulator([
      '--email',
      E2E_EMAIL,
      '--pump-code',
      pumpCode,
      '--sensor-code',
      sensorCode,
      '--scenario',
      'imbalance',
      '--windows',
      '2',
      '--seed',
      '18',
    ])

    await expect(page.getByText('Imbalance').first()).toBeVisible({ timeout: 25_000 })
    await expect(page.getByText('Fault').first()).toBeVisible({ timeout: 15_000 })

    await page
      .getByRole('navigation', { name: 'Primary' })
      .getByRole('link', { name: /ai analysis/i })
      .click()
    await expect(
      page.getByRole('heading', { name: 'AI analysis and prediction', exact: true }),
    ).toBeVisible()
    await expect(page.getByTestId('prediction-decision')).toHaveText('Fault')
    await expect(
      page.getByText(/PUMPVERITY lightweight linear v0\.1\.0/).first(),
    ).toBeVisible()
    await expect(page.getByText('Not a failure probability')).toBeVisible()

    await page
      .getByRole('navigation', { name: 'Primary' })
      .getByRole('link', { name: /alerts & review/i })
      .click()
    await expect(
      page.getByRole('heading', { name: 'Fault alerts and engineering review' }),
    ).toBeVisible()
    await page.getByLabel('Pump').selectOption({ label: pumpCode })
    await expect(
      page.getByRole('heading', { name: /Fault decision on/ }),
    ).toBeVisible({ timeout: 20_000 })

    await page.getByRole('button', { name: 'Acknowledge alert' }).click()
    await expect(
      page.getByText('Alert acknowledged and assigned to you.'),
    ).toBeVisible()
    await page.getByLabel('Action').selectOption('CONFIRM_LABEL')
    await page
      .getByLabel(/Engineering notes/)
      .fill('Fault signature confirmed in the Stage 5 end-to-end scenario.')
    await page.getByRole('button', { name: 'Record review' }).click()
    await expect(
      page.getByText(
        'Engineering review recorded without changing the original prediction.',
      ),
    ).toBeVisible()
    await expect(page.getByText('Label confirmed')).toBeVisible()

    await page.getByRole('button', { name: 'Open Engineering Copilot' }).click()
    await expect(
      page.getByRole('dialog', { name: 'PUMPVERITY AI Engineering Copilot' }),
    ).toBeVisible()
    await expect(page.getByText(/Ready/).first()).toBeVisible()
    await page
      .getByLabel('Message the Engineering Copilot')
      .fill('Why was this event marked uncertain?')
    await page.getByRole('button', { name: 'Send', exact: true }).click()
    await expect(page.getByText('Alert evidence').first()).toBeVisible({ timeout: 25_000 })
    await expect(
      page.getByText(/model outputs, not probabilities of mechanical failure/).first(),
    ).toBeVisible()

    await page
      .getByLabel('Message the Engineering Copilot')
      .fill('Generate a monitoring report')
    await page.getByRole('button', { name: 'Send', exact: true }).click()
    await expect(page.getByText('Confirmation required')).toBeVisible({ timeout: 20_000 })
    await page.getByRole('button', { name: 'Confirm and execute' }).click()
    await expect(page.getByText(/Monitoring report .* was generated/)).toBeVisible({
      timeout: 25_000,
    })
    await page.getByRole('button', { name: /Open report/ }).click()
    await expect(
      page.getByRole('heading', { name: 'Reports and exports', exact: true }),
    ).toBeVisible()
    await expect(page.getByText('Opened by Copilot')).toBeVisible({ timeout: 20_000 })
    await page.getByRole('button', { name: 'Close Copilot' }).click()

    await page
      .getByRole('navigation', { name: 'Primary' })
      .getByRole('link', { name: /historical trends/i })
      .click()
    await page
      .getByLabel('Pump')
      .selectOption({ label: `${pumpCode} - E2E SSE Pump` })
    await expect(page.getByText('Persisted alerts')).toBeVisible()
    await expect(page.getByText(/Fault alert \(\d+\)/)).toBeVisible()

    await page
      .getByRole('navigation', { name: 'Primary' })
      .getByRole('link', { name: /sensor health/i })
      .click()
    await page.getByLabel('Filter sensors by pump').selectOption({ label: pumpCode })
    await page.getByRole('button', { name: 'Run Copilot diagnostic' }).click()
    await expect(
      page.getByRole('dialog', { name: 'PUMPVERITY AI Engineering Copilot' }),
    ).toBeVisible()
    await expect(page.getByText('Sensor diagnostics').first()).toBeVisible({
      timeout: 20_000,
    })
    await expect(page.getByText(sensorCode).first()).toBeVisible()
  })
})





