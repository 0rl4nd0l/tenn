import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { TakeawaysPanel } from './takeaways-panel'

describe('TakeawaysPanel', () => {
  const payload = {
    sourceId: 'yt_abc',
    videoId: 'abc',
    takeaways: [
      {
        text: 'Bank margins compressed.',
        citations: [{ chunkId: 'c1', segmentStartSeconds: 12.5 }],
      },
    ],
    watchlistSuggestions: [
      {
        ticker: 'CBA.AX',
        commentary: 'Margin pressure noted in Q3.',
        citations: [{ chunkId: 'c1', segmentStartSeconds: 12.5 }],
      },
    ],
    model: 'llama-3',
    promptVersion: 'takeaways-v1',
  }

  it('renders takeaways with citation buttons', () => {
    render(
      <TakeawaysPanel
        payload={payload}
        onAddTicker={() => {}}
        onJumpToCitation={() => {}}
      />,
    )

    expect(screen.getByText(/Bank margins compressed/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /0:12/ })).toBeInTheDocument()
  })

  it('renders watchlist suggestions with Add button', async () => {
    const onAddTicker = vi.fn()

    render(
      <TakeawaysPanel
        payload={payload}
        onAddTicker={onAddTicker}
        onJumpToCitation={() => {}}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /add cba\.ax/i }))

    expect(onAddTicker).toHaveBeenCalledWith({
      ticker: 'CBA.AX',
      commentary: 'Margin pressure noted in Q3.',
      sourceId: 'yt_abc',
    })
  })

  it('emits citation clicks', async () => {
    const onJump = vi.fn()

    render(
      <TakeawaysPanel
        payload={payload}
        onAddTicker={() => {}}
        onJumpToCitation={onJump}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /0:12/ }))

    expect(onJump).toHaveBeenCalledWith({ chunkId: 'c1', segmentStartSeconds: 12.5 })
  })
})
