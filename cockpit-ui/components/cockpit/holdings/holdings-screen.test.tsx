import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HoldingsScreen } from './holdings-screen'

function holding(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    holding_id: 'h-1',
    ticker: 'BHP',
    account_label: 'Broker',
    thesis_bucket: 'Core',
    status: 'active',
    quantity: 100,
    avg_cost: 42.5,
    cost_currency: 'AUD',
    opened_at: '2026-01-01',
    updated_at: '2026-04-22T00:00:00Z',
    note: 'starter',
    ...overrides,
  }
}

function holdings(count: number): ReturnType<typeof holding>[] {
  return Array.from({ length: count }, (_, index) =>
    holding({
      holding_id: `h-${index + 1}`,
      ticker: `TK${String(index + 1).padStart(2, '0')}`,
      account_label: index % 2 === 0 ? 'Broker' : 'SMSF',
      opened_at: `2026-01-${String((index % 28) + 1).padStart(2, '0')}`,
    }),
  )
}

describe('HoldingsScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists holdings and renders summary metrics', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [holding(), holding({ holding_id: 'h-2', ticker: 'CBA', status: 'archived', account_label: 'SMSF' })],
        }),
      }),
    )

    render(<HoldingsScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('BHP')).toBeInTheDocument())
    expect(screen.getByText('CBA')).toBeInTheDocument()
    expect(screen.getByText('Positions')).toBeInTheDocument()
    expect(screen.getByText(/Cost basis known: 2/i)).toBeInTheDocument()
    expect(screen.getByText(/2 shown/)).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Amount mode' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Bar mode' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Daily range' })).toBeInTheDocument()
  })

  it('edits a holding and sends advanced fields in PATCH payload', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [holding()] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => holding({ status: 'archived', note: 'updated note' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [holding({ status: 'archived', note: 'updated note', updated_at: '2026-04-22T02:00:00Z' })],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<HoldingsScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('BHP')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))

    const statusInput = screen.getByDisplayValue('active')
    await userEvent.clear(statusInput)
    await userEvent.type(statusInput, 'archived')

    const noteInput = screen.getByDisplayValue('starter')
    await userEvent.clear(noteInput)
    await userEvent.type(noteInput, 'updated note')

    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/holdings/h-1',
        expect.objectContaining({ method: 'PATCH' }),
      )
    })

    const patchCall = fetchMock.mock.calls.find((call) => call[0] === '/api/cockpit/holdings/h-1')
    expect(patchCall).toBeDefined()
    const requestInit = patchCall?.[1] as RequestInit
    const body = JSON.parse(String(requestInit.body)) as { status?: string; note?: string }
    expect(body.status).toBe('archived')
    expect(body.note).toBe('updated note')

    await waitFor(() => expect(screen.getByText('archived')).toBeInTheDocument())
  })

  it('shows validation error when quantity is non-numeric', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<HoldingsScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('No holdings yet.')).toBeInTheDocument())

    await userEvent.type(screen.getByPlaceholderText('Ticker (e.g. BHP)'), 'BHP')
    await userEvent.type(screen.getByPlaceholderText('Quantity'), 'abc')
    await userEvent.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => expect(screen.getByText('Quantity must be numeric')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('paginates holdings with next/prev controls', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: holdings(12),
        }),
      }),
    )

    render(<HoldingsScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('TK01')).toBeInTheDocument())
    expect(screen.queryByText('TK12')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(screen.getByText('TK12')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Prev' }))
    await waitFor(() => expect(screen.getByText('TK01')).toBeInTheDocument())
  })
})
