import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TerminalInput } from './terminal-input'

describe('TerminalInput', () => {
  it('exposes a durable accessible name for the command input', () => {
    render(<TerminalInput onSend={vi.fn()} />)

    expect(screen.getByRole('textbox', { name: /cockpit command or query/i })).toBeInTheDocument()
  })
})
