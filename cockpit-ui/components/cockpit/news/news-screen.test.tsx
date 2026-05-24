import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NewsScreen } from './news-screen'

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
})
