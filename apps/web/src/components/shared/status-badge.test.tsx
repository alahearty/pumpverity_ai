import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBadge } from './status-badge'

describe('StatusBadge', () => {
  it('distinguishes equipment faults from sensor-invalid states', () => {
    const { rerender } = render(<StatusBadge status="FAULT" />)
    expect(screen.getByText('Fault')).toBeInTheDocument()

    rerender(<StatusBadge status="SENSOR_INVALID" />)
    expect(screen.getByText('Sensor invalid')).toBeInTheDocument()
    expect(screen.getByText('Sensor invalid').closest('span')).toHaveClass('text-violet-700')
  })

  it('labels connectivity and review statuses', () => {
    const { rerender } = render(<StatusBadge status="OFFLINE_BUFFERING" />)
    expect(screen.getByText('Offline — buffering')).toBeInTheDocument()

    rerender(<StatusBadge status="REVIEWED" />)
    expect(screen.getByText('Reviewed')).toBeInTheDocument()
  })

  it('formats unknown values instead of hiding them', () => {
    render(<StatusBadge status="NEW_STATE" />)
    expect(screen.getByText('New State')).toBeInTheDocument()
  })
})
