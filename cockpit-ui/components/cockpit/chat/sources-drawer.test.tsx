import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SourcesDrawer } from './sources-drawer'

describe('SourcesDrawer', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches /api/cockpit/commentary/recent when opened', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            source_id: 'yt_a',
            source_name: 'Video A',
            source_type: 'youtube',
            source_kind: 'ephemeral',
            approved_at: '2026-04-18T10:00:00Z',
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<SourcesDrawer open apiKey="k" onReattach={() => {}} onClose={() => {}} />)

    await waitFor(() => expect(screen.getByText('Video A')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/commentary/recent?limit=20',
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-API-Key': 'k' }),
      }),
    )
  })

  it('emits onReattach when an item is clicked', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            {
              source_id: 'yt_a',
              source_name: 'Video A',
              source_type: 'market_commentary',
              source_kind: 'concat',
              approved_at: '2026-04-18T10:00:00Z',
            },
          ],
        }),
      }),
    )
    const onReattach = vi.fn()

    render(<SourcesDrawer open apiKey="k" onReattach={onReattach} onClose={() => {}} />)

    await waitFor(() => screen.getByText('Video A'))
    await userEvent.click(screen.getByRole('button', { name: /re-?attach video a/i }))

    expect(onReattach).toHaveBeenCalledWith({
      sourceId: 'yt_a',
      sourceKind: 'concat',
      title: 'Video A',
    })
  })
})
