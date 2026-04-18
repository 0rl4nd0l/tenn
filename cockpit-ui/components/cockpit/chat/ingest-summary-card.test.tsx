import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { IngestSummaryCard } from './ingest-summary-card'

describe('IngestSummaryCard', () => {
  const summary = {
    sourceId: 'yt_abc',
    title: 'CBA Results Review',
    chunkCount: 12,
    detectedTickers: ['CBA.AX', 'BHP.AX'],
    status: 'pending' as const,
    sourceKind: 'ephemeral' as const,
  }

  it('renders title, chunk count, and tickers', () => {
    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={false}
        onAttach={() => {}}
        onDetach={() => {}}
        onAddTicker={() => {}}
      />,
    )

    expect(screen.getByText(/CBA Results Review/)).toBeInTheDocument()
    expect(screen.getByText(/12 chunks/)).toBeInTheDocument()
    expect(screen.getByText('CBA.AX')).toBeInTheDocument()
    expect(screen.getByText('BHP.AX')).toBeInTheDocument()
  })

  it('calls onAttach when Attach is clicked', async () => {
    const onAttach = vi.fn()

    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={false}
        onAttach={onAttach}
        onDetach={() => {}}
        onAddTicker={() => {}}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /attach/i }))

    expect(onAttach).toHaveBeenCalledWith('yt_abc')
  })

  it('swaps Attach for Detach when isAttached', async () => {
    const onDetach = vi.fn()

    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={true}
        onAttach={() => {}}
        onDetach={onDetach}
        onAddTicker={() => {}}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /detach/i }))

    expect(onDetach).toHaveBeenCalledWith('yt_abc')
  })

  it('calls onAddTicker with the chosen ticker', async () => {
    const onAddTicker = vi.fn()

    render(
      <IngestSummaryCard
        summary={summary}
        isAttached={true}
        onAttach={() => {}}
        onDetach={() => {}}
        onAddTicker={onAddTicker}
      />,
    )

    await userEvent.click(screen.getAllByRole('button', { name: /add to watchlist/i })[0]!)

    expect(onAddTicker).toHaveBeenCalledWith('CBA.AX')
  })
})
