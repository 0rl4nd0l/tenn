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
})
