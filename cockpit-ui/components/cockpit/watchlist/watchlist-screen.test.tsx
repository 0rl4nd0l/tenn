import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WatchlistScreen } from './watchlist-screen'

describe('WatchlistScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('lists items fetched from /api/cockpit/watchlist', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            {
              ticker: 'CBA.AX',
              added_at: '2026-04-18T00:00:00Z',
              source_id: 'yt_a',
              note: 'test',
              stance: 'watch',
            },
          ],
        }),
      }),
    )

    render(<WatchlistScreen apiKey="k" />)

    await waitFor(() => expect(screen.getByText('CBA.AX')).toBeInTheDocument())
  })

  it('surfaces 409 duplicate errors inline', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({ ok: false, status: 409, text: async () => 'duplicate' })

    vi.stubGlobal('fetch', fetchMock)

    render(<WatchlistScreen apiKey="k" />)

    await userEvent.click(screen.getByRole('button', { name: /add ticker/i }))
    await userEvent.type(screen.getByLabelText(/ticker/i), 'BHP.AX')
    await userEvent.click(screen.getByRole('button', { name: /^add$/i }))

    await waitFor(() => {
      expect(screen.getByText(/already in watchlist/i)).toBeInTheDocument()
    })
  })

  it('shows holdings-derived candidates when the watchlist is empty', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            { ticker: 'bhp.ax', account_label: 'Core portfolio', status: 'active' },
            { ticker: 'BHP.AX', account_label: 'Trading', status: 'active' },
            { ticker: 'CBA.AX', account_label: null, status: 'archived' },
          ],
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              ticker: 'BHP.AX',
              added_at: '2026-04-18T00:00:00Z',
              source_id: null,
              note: 'Current holding in Core portfolio',
              stance: 'watch',
            },
          ],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<WatchlistScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('BHP.AX')).toBeInTheDocument()
      expect(screen.getByText('Source: Current holding in Core portfolio')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /add bhp\.ax/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/watchlist',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            ticker: 'BHP.AX',
            note: 'Current holding in Core portfolio',
            stance: 'watch',
          }),
        }),
      )
    })
  })

  it('shows DATA_MISSING when no empty-state candidate source is available', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
        .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) }),
    )

    render(<WatchlistScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText(/DATA_MISSING: no current holdings/i)).toBeInTheDocument()
    })
  })

  it('shows DATA_MISSING when the watchlist source is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status: 503 }))

    render(<WatchlistScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText(/DATA_MISSING: no current holdings/i)).toBeInTheDocument()
    })
  })
})
