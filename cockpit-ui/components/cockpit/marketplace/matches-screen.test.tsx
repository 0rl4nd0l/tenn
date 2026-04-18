import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMatchesScreen } from './matches-screen'

describe('MarketplaceMatchesScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders saved Marketplace matches', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            {
              match_id: 'mp_match_1',
              mission_id: 'mp_mission_1',
              mission_name: 'Dual-cab ute',
              listing_id: '123',
              listing_url: 'https://www.facebook.com/marketplace/item/123/',
              title: '2014 Toyota Hilux SR5 4x4',
              price: '$22,500',
              location: 'Preston VIC',
              captured_at: '2026-04-18T10:00:00Z',
              score: 89,
              decision_band: 'strong_match',
              reasons_for: ['Below local median'],
              reasons_against: ['High kilometres'],
              confidence: 0.84,
              raw_text_snapshot: 'Visible listing text',
              status: 'new',
              metadata: {},
              updated_at: '2026-04-18T10:00:00Z',
            },
          ],
        }),
      }),
    )

    render(<MarketplaceMatchesScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('2014 Toyota Hilux SR5 4x4')).toBeInTheDocument()
    })
    expect(screen.getByText('$22,500')).toBeInTheDocument()
    expect(screen.getByText(/below local median/i)).toBeInTheDocument()
  })
})
