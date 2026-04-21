import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HoldingsScreen } from './holdings-screen'

describe('HoldingsScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists items fetched from /api/cockpit/holdings', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            {
              holding_id: 'h-1',
              ticker: 'BHP',
              account_label: 'Broker',
              thesis_bucket: null,
              status: 'active',
              quantity: 100,
              avg_cost: 42.5,
              cost_currency: null,
              opened_at: null,
              updated_at: null,
              note: 'starter',
            },
          ],
        }),
      }),
    )

    render(<HoldingsScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('BHP')).toBeInTheDocument())
    expect(screen.getByText('Broker')).toBeInTheDocument()
  })

  it('edits an existing holding row and saves it', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              holding_id: 'h-1',
              ticker: 'BHP',
              account_label: 'Broker',
              thesis_bucket: null,
              status: 'active',
              quantity: 100,
              avg_cost: 42.5,
              cost_currency: null,
              opened_at: null,
              updated_at: null,
              note: 'starter',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          holding_id: 'h-1',
          ticker: 'BHP',
          account_label: 'Brokerage A',
          thesis_bucket: null,
          status: 'active',
          quantity: 125,
          avg_cost: 41.2,
          cost_currency: null,
          opened_at: null,
          updated_at: null,
          note: 'updated',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              holding_id: 'h-1',
              ticker: 'BHP',
              account_label: 'Brokerage A',
              thesis_bucket: null,
              status: 'active',
              quantity: 125,
              avg_cost: 41.2,
              cost_currency: null,
              opened_at: null,
              updated_at: null,
              note: 'updated',
            },
          ],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<HoldingsScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('BHP')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))

    const accountInput = screen.getByDisplayValue('Broker')
    await userEvent.clear(accountInput)
    await userEvent.type(accountInput, 'Brokerage A')

    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/holdings/h-1',
        expect.objectContaining({ method: 'PATCH' }),
      )
    })
    await waitFor(() => expect(screen.getByText('Brokerage A')).toBeInTheDocument())
  })
})

