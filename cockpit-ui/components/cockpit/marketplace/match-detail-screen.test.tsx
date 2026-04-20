import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMatchDetailScreen } from './match-detail-screen'

describe('MarketplaceMatchDetailScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders score breakdown and evidence for one Marketplace match without requiring a local API key', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          match_id: 'mp_match_1',
          mission_id: 'mp_mission_1',
          mission_name: 'Dual-cab ute',
          listing_id: '123',
          listing_url: 'https://www.facebook.com/marketplace/item/123/',
          title: '2014 Toyota Hilux SR5 4x4',
          price: '$22,500',
          location: 'Preston VIC',
          seller_name: 'Example Seller',
          captured_at: '2026-04-18T10:00:00Z',
          score: 89,
          decision_band: 'strong_match',
          reasons_for: ['Below local median'],
          reasons_against: ['High kilometres'],
          confidence: 0.84,
          raw_text_snapshot: 'Visible listing text',
          screenshot_path: '/tmp/hilux.png',
          status: 'new',
          metadata: {
            query: 'toyota hilux 4x4',
            material_change_reasons: ['price_drop'],
          },
          updated_at: '2026-04-18T10:00:00Z',
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchDetailScreen apiKey="" matchId="mp_match_1" />)

    await waitFor(() => {
      expect(screen.getByText('2014 Toyota Hilux SR5 4x4')).toBeInTheDocument()
    })
    expect(screen.getByText(/below local median/i)).toBeInTheDocument()
    expect(screen.getByText(/example seller/i)).toBeInTheDocument()
    expect(screen.getByText(/toyota hilux 4x4/i)).toBeInTheDocument()
    expect(screen.getByText(/price_drop/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
