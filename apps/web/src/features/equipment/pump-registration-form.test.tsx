import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { OperatingRegime, PumpCreate } from '@petrosense/shared-contracts'

import { PumpRegistrationForm } from './pump-registration-form'

const REGIMES: OperatingRegime[] = [
  {
    id: 'regime-1',
    code: 'STEADY_STATE',
    name: 'Steady state',
    description: 'Nominal operation',
    is_active: true,
  },
  {
    id: 'regime-2',
    code: 'STARTUP',
    name: 'Startup',
    description: 'Acceleration',
    is_active: true,
  },
]

describe('PumpRegistrationForm', () => {
  it('validates required pump and sensor identity', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(async () => {})
    render(<PumpRegistrationForm regimes={REGIMES} onSubmit={onSubmit} onCancel={() => {}} />)

    await user.click(screen.getByRole('button', { name: /register pump and sensor/i }))

    expect(await screen.findByText('Pump code is required.')).toBeInTheDocument()
    expect(await screen.findByText('Pump name is required.')).toBeInTheDocument()
    expect(await screen.findByText('Sensor code is required.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits pump and nested sensor values', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(async (_payload: PumpCreate) => {})
    render(<PumpRegistrationForm regimes={REGIMES} onSubmit={onSubmit} onCancel={() => {}} />)

    await user.type(screen.getByLabelText('Pump ID'), 'lab-pump-02')
    await user.type(screen.getByLabelText('Pump name'), 'Auxiliary Pump')
    await user.type(screen.getByLabelText('Sensor ID'), 'vib-02')
    await user.click(screen.getByRole('button', { name: /register pump and sensor/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    const payload = onSubmit.mock.calls[0][0]
    expect(payload.pump_code).toBe('lab-pump-02')
    expect(payload.name).toBe('Auxiliary Pump')
    expect(payload.default_regime_id).toBeNull()
    expect(payload.sensor?.sensor_code).toBe('vib-02')
    expect(payload.sensor?.mounting_axis).toBe('RADIAL_X')
    expect(payload.sensor?.sampling_rate_hz).toBe(2048)
  })
})
