import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMatchesScreen } from './matches-screen'

describe('MarketplaceMatchesScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders saved Marketplace matches even without a local API key', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
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
              listing_media: [
                'https://cdn.example.com/listing-1.jpg',
                'https://cdn.example.com/listing-2.jpg',
              ],
              status: 'new',
              metadata: {
                price_evidence: {
                  detail_price_text: null,
                  card_price_text: '$22,500',
                  resolved_price_text: '$22,500',
                  resolved_price_value: 22500,
                  source: 'search_card',
                  warning: 'Detail page did not expose a price; preserved search-card price.',
                },
              },
              value_context: {
                state: 'scored',
                value_score: 84,
                value_label: 'good value',
                value_confidence: 'medium',
                benchmark_snapshot_id: 'snap_1',
                fair_low: 760,
                fair_high: 980,
                used_median: 870,
                retail_anchor_price: 1499,
                price_movement_summary: 'Listing is below the used median.',
                explanation: 'Compared with the latest saved RTX 3090 benchmark snapshot.',
                warnings: [],
                notes: [],
                linked_tracked_product_id: 'tp_3090',
                linked_tracked_product_name: 'NVIDIA RTX 3090',
                mission_mode: 'requirement_driven',
                value_source: 'matched_candidate_benchmark',
                matched_candidate_tracked_product_id: 'tp_3090',
                matched_candidate_name: 'NVIDIA RTX 3090',
                candidate_match_confidence: 0.91,
                benchmark_freshness_status: 'fresh',
                benchmark_sample_size: 6,
              },
              updated_at: '2026-04-18T10:00:00Z',
            },
          ],
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('2014 Toyota Hilux SR5 4x4')).toBeInTheDocument()
    })
    expect(screen.getByText('$22,500')).toBeInTheDocument()
    expect(screen.getByText(/below local median/i)).toBeInTheDocument()
    expect(screen.getByText(/photos: 2/i)).toBeInTheDocument()
    expect(screen.getByText(/source: search card/i)).toBeInTheDocument()
    expect(screen.getByText(/preserved search-card price/i)).toBeInTheDocument()
    expect(screen.getByAltText(/listing photo for 2014 toyota hilux sr5 4x4/i)).toBeInTheDocument()
    expect(screen.getByText(/used-market value/i)).toBeInTheDocument()
    expect(screen.getByText(/good value/i)).toBeInTheDocument()
    expect(screen.getByText(/nvidia rtx 3090/i)).toBeInTheDocument()
    expect(screen.getByText(/matched candidate/i)).toBeInTheDocument()
    expect(screen.getByText(/candidate match/i)).toBeInTheDocument()
    expect(screen.getByText(/listing is below the used median/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('shows a photo unavailable state when a listing has no media', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            match_id: 'mp_match_2',
            mission_id: 'mp_mission_1',
            mission_name: 'Dual-cab ute',
            listing_id: '456',
            listing_url: 'https://www.facebook.com/marketplace/item/456/',
            title: '2013 Ford Ranger XLT',
            price: '$19,900',
            location: 'Coburg VIC',
            captured_at: '2026-04-18T10:00:00Z',
            score: 80,
            decision_band: 'candidate',
            reasons_for: [],
            reasons_against: [],
            confidence: 0.72,
            raw_text_snapshot: 'Visible listing text',
            status: 'new',
            metadata: {},
            updated_at: '2026-04-18T10:00:00Z',
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('2013 Ford Ranger XLT')).toBeInTheDocument()
    })
    expect(screen.getByText(/listing photos unavailable/i)).toBeInTheDocument()
    expect(screen.getByText(/photos: 0/i)).toBeInTheDocument()
  })
})
