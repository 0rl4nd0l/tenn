import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
          price_comparison: {
            listing_price: 22500,
            used_market_median: 25000,
            retail_anchor_price: 31000,
            retail_anchor_label: 'dealer_rrp',
            fair_range_low: 21000,
            fair_range_high: 26000,
            delta_vs_used_median: { amount: -2500, percent: -10 },
            delta_vs_retail_anchor: { amount: -8500, percent: -27.4 },
            verdict: 'discount',
            color: 'emerald',
          },
          user_feedback: null,
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
    expect(screen.getByText(/price comparison/i)).toBeInTheDocument()
    expect(screen.getAllByText(/retail\/rrp/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/-10%/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('explains when a listing price exists but benchmark anchors are missing', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: 'mp_match_listing_only',
        mission_id: 'mp_mission_storage',
        mission_name: 'NVMe storage',
        listing_id: '123',
        listing_url: 'https://www.facebook.com/marketplace/item/123/',
        title: 'Kingston NV2 2TB NVMe SSD',
        price: 'AU$300 Kingston NV2 2TB NVMe SSD Melbourne, VIC',
        price_value: 300,
        location: 'Melbourne VIC',
        seller_name: null,
        captured_at: '2026-05-04T01:28:29Z',
        score: 95,
        decision_band: 'strong_match',
        reasons_for: ['Matched mission keyword: 2TB'],
        reasons_against: [],
        confidence: 0.66,
        raw_text_snapshot: 'Kingston NV2 2TB NVMe SSD.',
        status: 'new',
        metadata: {},
        price_comparison: {
          listing_price: 300,
          used_market_median: null,
          retail_anchor_price: null,
          delta_vs_used_median: { amount: null, percent: null },
          verdict: 'unavailable',
          color: 'slate',
          comparison_state: 'missing_benchmark_anchor',
          unavailable_reason:
            'Listing price was captured, but no used-market benchmark or retail/RRP anchor is available for the matched product.',
          next_action:
            'Link or calibrate a tracked product benchmark, then add accepted marketplace observations or a retail anchor.',
        },
        user_feedback: null,
        updated_at: '2026-05-04T01:28:29Z',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchDetailScreen apiKey="" matchId="mp_match_listing_only" />)

    await waitFor(() => {
      expect(screen.getByText('Kingston NV2 2TB NVMe SSD')).toBeInTheDocument()
    })
    expect(screen.getByText(/benchmark unavailable/i)).toBeInTheDocument()
    expect(screen.getByText(/listing price was captured/i)).toBeInTheDocument()
    expect(screen.getByText(/tracked product benchmark/i)).toBeInTheDocument()
  })

  it('explains when a low-confidence retail anchor is ignored', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: 'mp_match_ignored_anchor',
        mission_id: 'mp_mission_ram',
        mission_name: 'RAM',
        listing_id: '456',
        listing_url: 'https://www.facebook.com/marketplace/item/456/',
        title: 'Corsair Vengeance LPX 32GB DDR4',
        price: '$50',
        price_value: 50,
        location: 'Melbourne VIC',
        seller_name: null,
        captured_at: '2026-05-04T01:28:29Z',
        score: 80,
        decision_band: 'candidate',
        reasons_for: ['Matched mission keyword: 32GB'],
        reasons_against: [],
        confidence: 0.66,
        raw_text_snapshot: 'Corsair Vengeance LPX 32GB DDR4.',
        status: 'new',
        metadata: {},
        benchmark: {
          source: 'centre_com',
          matched_product: 'Corsair Vengeance 32GB DDR5-6000 CL36 Memory Kit',
          current_price: 189,
          confidence: 0.4,
          low_confidence: true,
          review_status: 'pending_review',
        },
        price_comparison: {
          listing_price: 50,
          retail_anchor_price: null,
          verdict: 'unavailable',
          color: 'slate',
          comparison_state: 'retail_anchor_needs_review',
          unavailable_reason:
            'A retail benchmark candidate exists, but it was not used because the retail benchmark match still requires review.',
          next_action:
            'Accept the retail benchmark review if it is correct, or link a better tracked product/retail anchor before comparing prices.',
        },
        user_feedback: null,
        updated_at: '2026-05-04T01:28:29Z',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchDetailScreen apiKey="" matchId="mp_match_ignored_anchor" />)

    await waitFor(() => {
      expect(screen.getByText('Corsair Vengeance LPX 32GB DDR4')).toBeInTheDocument()
    })
    expect(screen.getByText(/retail anchor needs review/i)).toBeInTheDocument()
    expect(screen.getByText(/not used/i)).toBeInTheDocument()
    expect(screen.getByText(/accept the retail benchmark review/i)).toBeInTheDocument()
  })

  it('records not interested feedback from the detail screen', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: 'mp_match_feedback',
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
          status: 'new',
          metadata: {},
          price_comparison: {
            listing_price: 1050,
            used_market_median: 1000,
            delta_vs_used_median: { amount: 50, percent: 5 },
            verdict: 'near_market',
            color: 'amber',
          },
          user_feedback: null,
          updated_at: '2026-04-18T10:00:00Z',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: 'mp_match_feedback',
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
          status: 'new',
          metadata: {},
          price_comparison: {
            listing_price: 1050,
            used_market_median: 1000,
            delta_vs_used_median: { amount: 50, percent: 5 },
            verdict: 'near_market',
            color: 'amber',
          },
          user_feedback: {
            match_id: 'mp_match_feedback',
            feedback: 'not_interested',
            note: null,
            created_at: '2026-04-18T10:01:00Z',
            updated_at: '2026-04-18T10:01:00Z',
          },
          updated_at: '2026-04-18T10:01:00Z',
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchDetailScreen apiKey="" matchId="mp_match_feedback" />)

    await waitFor(() => {
      expect(screen.getByText('RTX 3090 listing')).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('button', { name: /not interested/i }))

    // Note panel should appear; confirm without adding a note
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^confirm$/i })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('button', { name: /^confirm$/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/marketplace/matches/mp_match_feedback/feedback',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ feedback: 'not_interested', note: null }),
        }),
      )
    })
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
