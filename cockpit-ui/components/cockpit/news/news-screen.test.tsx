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
    expect(screen.getByText('DATA_MISSING evidence envelope')).toBeInTheDocument()
  })

  it('renders supplied backend evidence-envelope fields for news results', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          results: [
            {
              score: 0.91,
              payload: {
                title: 'A2M recall article',
                text: 'Local news context with inspectable source.',
                url: 'https://example.com/a2m-recall',
                ticker: 'A2M',
                provider: 'news',
                published_at: '2026-05-23T00:00:00.000Z',
                chunk_id: 'chunk-a2m-recall',
                source_label: 'local_news_context',
                evidence_labels: ['local_news_context', 'context_only'],
                source_coverage_status: 'context_only',
                source_label_taxonomy_version: 'source_label_semantics_v1',
                claim_verified_source_count: 0,
              },
            },
          ],
        }),
      }),
    )

    render(<NewsScreen />)

    await userEvent.type(await screen.findByPlaceholderText(/search news articles/i), 'A2M recall')
    await userEvent.click(screen.getByRole('button', { name: /^search$/i }))

    const headline = await screen.findByText('A2M recall article')
    expect(screen.getByText('coverage: context only')).toBeInTheDocument()

    await userEvent.click(headline)

    expect(screen.getByLabelText('Evidence envelope')).toBeInTheDocument()
    expect(screen.getByText('source: local news context')).toBeInTheDocument()
    expect(screen.getAllByText('local news context').length).toBeGreaterThan(0)
    expect(screen.getAllByText('context only').length).toBeGreaterThan(0)
    expect(screen.getByText('taxonomy: source label semantics v1')).toBeInTheDocument()
    expect(screen.getByText('claim verified sources: 0')).toBeInTheDocument()
  })
})
