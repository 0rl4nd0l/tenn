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
            warnings: ['Condition certainty is weak.'],
            notes: [],
            linked_tracked_product_id: 'tp_3090',
            linked_tracked_product_name: 'NVIDIA RTX 3090',
            mission_mode: 'requirement_driven',
            value_source: 'matched_candidate_benchmark',
            matched_candidate_tracked_product_id: 'tp_3090',
            matched_candidate_name: 'NVIDIA RTX 3090',
            candidate_match_confidence: 0.91,
            requirement_fit_score: 95,
            benchmark_freshness_status: 'fresh',
            benchmark_sample_size: 6,
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
    expect(screen.getByText(/listing photos unavailable for this capture/i)).toBeInTheDocument()
    expect(screen.getByText(/used-market value/i)).toBeInTheDocument()
    expect(screen.getByText(/good value/i)).toBeInTheDocument()
    expect(screen.getByText(/nvidia rtx 3090/i)).toBeInTheDocument()
    expect(screen.getAllByText(/matched candidate/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/requirement fit/i)).toBeInTheDocument()
    expect(screen.getByText(/listing is below the used median/i)).toBeInTheDocument()
    expect(screen.getByText(/condition certainty is weak/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('renders listing photo gallery when media urls are available', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: 'mp_match_2',
        mission_id: 'mp_mission_1',
        mission_name: 'GPU mission',
        listing_id: '456',
        listing_url: 'https://www.facebook.com/marketplace/item/456/',
        title: 'RTX 3090 listing',
        price: '$1,050',
        location: 'Richmond VIC',
        seller_name: 'GPU Seller',
        captured_at: '2026-04-18T10:00:00Z',
        score: 92,
        decision_band: 'strong_match',
        reasons_for: ['Good condition'],
        reasons_against: [],
        confidence: 0.91,
        raw_text_snapshot: 'Visible listing text',
        listing_media: [
          'https://cdn.example.com/gpu-1.jpg',
          'https://cdn.example.com/gpu-2.jpg',
        ],
        status: 'new',
        metadata: {},
        updated_at: '2026-04-18T10:00:00Z',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchDetailScreen apiKey="" matchId="mp_match_2" />)

    await waitFor(() => {
      expect(screen.getByText('RTX 3090 listing')).toBeInTheDocument()
    })
    expect(screen.getByAltText(/listing photo 1 for rtx 3090 listing/i)).toBeInTheDocument()
    expect(screen.getByAltText(/listing photo 2 for rtx 3090 listing/i)).toBeInTheDocument()
  })
})
