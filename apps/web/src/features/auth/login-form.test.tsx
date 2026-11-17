import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ApiClientError } from '@/lib/api'
import { LoginForm } from './login-form'

describe('LoginForm', () => {
  it('shows validation messages for an empty submission', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(async () => {})
    render(<LoginForm onSubmit={onSubmit} />)

    await user.click(screen.getByRole('button', { name: /sign in to workspace/i }))

    expect(await screen.findByText('Enter your email address or username.')).toBeInTheDocument()
    expect(
      await screen.findByText('Password must contain at least 8 characters.'),
    ).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('rejects a short password before calling the API', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(async () => {})
    render(<LoginForm onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText('Email or username'), 'engineer@petrosense.local')
    await user.type(screen.getByLabelText('Password'), 'short')
    await user.click(screen.getByRole('button', { name: /sign in to workspace/i }))

    expect(
      await screen.findByText('Password must contain at least 8 characters.'),
    ).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits trimmed credentials', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(async () => {})
    render(<LoginForm onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText('Email or username'), '  engineer  ')
    await user.type(screen.getByLabelText('Password'), 'ValidPass!234')
    await user.click(screen.getByRole('button', { name: /sign in to workspace/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith({
      identifier: 'engineer',
      password: 'ValidPass!234',
    })
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(<LoginForm onSubmit={vi.fn(async () => {})} />)

    const passwordInput = screen.getByLabelText('Password')
    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: /show password/i }))
    expect(passwordInput).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: /hide password/i }))
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('renders API failures with a request identifier', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(async () => {
      throw new ApiClientError(
        'Invalid email/username or password.',
        401,
        'INVALID_CREDENTIALS',
        'req-test-123',
      )
    })
    render(<LoginForm onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText('Email or username'), 'engineer')
    await user.type(screen.getByLabelText('Password'), 'WrongPass!234')
    await user.click(screen.getByRole('button', { name: /sign in to workspace/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid email/username or password.',
    )
    expect(screen.getByText(/req-test-123/)).toBeInTheDocument()
  })
})
