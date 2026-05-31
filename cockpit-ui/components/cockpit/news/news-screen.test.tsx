import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NewsScreen, resolveNewsLookbackDateFrom } from './news-screen'

describe('NewsScreen actionability', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows DATA_MISSING before any news query is submitted', async () => {
    render(<NewsScreen />)

    await waitFor(() => {
      expect(screen.getByText('News evidence state')).toBeInTheDocument()
    })
    expect(screen.getByText('DATA_MISSING')).toBeInTheDocument()
    expect(screen.getByText(/no query has been submitted/i)).toBeInTheDocument()
  })

  it('surfaces missing published_at instead of presenting the result as fresh', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              score: 0.87,
              payload: {
                title: 'CSL filing notice',
                text: 'Filing context with no market-data evidence.',
                url: 'https://example.com/csl-filing',
                ticker: 'CSL',
                provider: 'asx',
                chunk_id: 'chunk-csl-filing',
              },
            },
          ],
        }),
      }),
    )

    render(<NewsScreen />)

    await userEvent.type(await screen.findByPlaceholderText(/search news articles/i), 'CSL price trend')
    await userEvent.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(screen.getByText('CSL filing notice')).toBeInTheDocument()
    })
    expect(screen.getAllByText('DATA_MISSING').length).toBeGreaterThan(0)
    expect(screen.getByText('DATE MISSING')).toBeInTheDocument()
    expect(screen.getByText(/freshness cannot be proven/i)).toBeInTheDocument()
  })

  it('translates lookback selections into backend date filters', () => {
    const now = new Date('2026-05-31T12:00:00.000Z')

    expect(resolveNewsLookbackDateFrom('24h', now)).toBe('2026-05-30T12:00:00.000Z')
    expect(resolveNewsLookbackDateFrom('7d', now)).toBe('2026-05-24T12:00:00.000Z')
    expect(resolveNewsLookbackDateFrom('30d', now)).toBe('2026-05-01T12:00:00.000Z')
    expect(resolveNewsLookbackDateFrom('all', now)).toBeUndefined()
  })

  it('includes the selected lookback in the news search request payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<NewsScreen />)

    await userEvent.type(await screen.findByPlaceholderText(/search news articles/i), 'BHP lithium')
    await userEvent.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/rag/query',
        expect.objectContaining({
          method: 'POST',
        }),
      )
    })
    const [, init] = fetchMock.mock.calls[0]
    const body = JSON.parse(String(init?.body))
    expect(body).toMatchObject({
      query: 'BHP lithium',
      source: 'news',
      top_k: 20,
    })
    expect(body.date_from).toEqual(expect.any(String))
  })
})
