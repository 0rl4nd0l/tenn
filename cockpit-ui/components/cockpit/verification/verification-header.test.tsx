import type { ComponentProps } from 'react'

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { VerificationHeader } from './verification-header'

function renderHeader(overrides: Partial<ComponentProps<typeof VerificationHeader>> = {}) {
  const props: ComponentProps<typeof VerificationHeader> = {
    ticker: 'BHP',
    extractionMethod: 'auto',
    strictMethod: false,
    reviewSession: null,
    failedChecksCount: 0,
    onTickerChange: vi.fn(),
    onMethodChange: vi.fn(),
    onStrictMethodChange: vi.fn(),
    ...overrides,
  }
  render(<VerificationHeader {...props} />)
  return props
}

describe('VerificationHeader', () => {
  it('exposes durable accessible names for shared extraction controls', () => {
    renderHeader()

    expect(screen.getByRole('textbox', { name: 'Active Ticker' })).toHaveValue('BHP')
    expect(screen.getByRole('combobox', { name: 'Method / Provider' })).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: 'Strict Mode' })).toBeInTheDocument()
  })

  it('keeps existing control handlers wired', async () => {
    const user = userEvent.setup()
    const onTickerChange = vi.fn()
    const onStrictMethodChange = vi.fn()
    renderHeader({ onTickerChange, onStrictMethodChange })

    await user.type(screen.getByRole('textbox', { name: 'Active Ticker' }), 'c')
    await user.click(screen.getByRole('switch', { name: 'Strict Mode' }))

    expect(onTickerChange).toHaveBeenLastCalledWith('BHPC')
    expect(onStrictMethodChange).toHaveBeenCalledWith(true)
  })
})
