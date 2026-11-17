import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMatchesScreen } from './matches-screen'

function jsonResponse(body: unknown, ok = true) {
  return {
    ok,
    json: async () => body,
  }
}

function minimalMatch(overrides: Record<string, unknown> = {}) {
  return {
    match_id: 'mp_match_default',
    mission_id: 'mp_mission_default',
    mission_name: 'Default mission',
    listing_id: 'listing_default',
    listing_url: 'https://www.facebook.com/marketplace/item/default/',
    title: 'Default listing',
    price: '$100',
    location: 'Melbourne VIC',
    captured_at: '2026-05-04T01:28:29Z',
    first_found_at: '2026-05-04T01:28:29Z',
    last_seen_at: '2026-05-04T01:28:29Z',
    score: 50,
    decision_band: 'candidate',
    reasons_for: ['Matched mission keyword'],
    reasons_against: [],
    confidence: 0.66,
    raw_text_snapshot: 'Visible listing text',
    listing_media: [],
    status: 'reviewed',
    metadata: {},
    user_feedback: null,
    updated_at: '2026-05-04T01:28:29Z',
    ...overrides,
  }
}

function installPointerCaptureMock() {
  const prototype = HTMLElement.prototype as unknown as Record<string, unknown>
  if (typeof prototype.hasPointerCapture !== 'function') {
    Object.defineProperty(HTMLElement.prototype, 'hasPointerCapture', {
      configurable: true,
      value: () => false,
    })
  }
  if (typeof prototype.setPointerCapture !== 'function') {
    Object.defineProperty(HTMLElement.prototype, 'setPointerCapture', {
      configurable: true,
      value: () => {},
    })
  }
  if (typeof prototype.releasePointerCapture !== 'function') {
    Object.defineProperty(HTMLElement.prototype, 'releasePointerCapture', {
      configurable: true,
      value: () => {},
    })
  }
}

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
              first_found_at: '2026-04-18T09:00:00Z',
              last_seen_at: '2026-04-18T12:30:00Z',
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
              deal_metrics: {
                state: 'scored',
                listing_price: 22500,
                used_market_median: 25000,
                retail_anchor_price: 31000,
                delta_vs_used_median: { amount: -2500, percent: -10 },
                delta_vs_retail_anchor: { amount: -8500, percent: -27.4 },
                deal_score: 84,
                deal_label: 'good_value',
                benchmark_sample_size: 6,
                comparable_group: {
                  key: 'vehicle:toyota-hilux',
                  label: 'Vehicle / Toyota Hilux',
                  category: 'vehicle',
                  basis: ['model'],
                },
                benchmark_health: {
                  label: 'high',
                  sample_size: 6,
                  freshness_status: 'fresh',
                  confidence_label: 'high',
                  source_diversity: 2,
                },
                price_movement: {
                  direction: 'drop',
                  amount: -1000,
                  percent: -4.3,
                  previous_price: 23500,
                  current_price: 22500,
                },
                alert_policy: {
                  allowed: false,
                  blocked_reasons: ['used-market discount is unknown'],
                  rules: { min_discount_pct: 15 },
                },
              },
              price_comparison: {
                listing_price: 22500,
                used_market_median: 25000,
                retail_anchor_price: 31000,
                delta_vs_used_median: { amount: -2500, percent: -10 },
                delta_vs_retail_anchor: { amount: -8500, percent: -27.4 },
                verdict: 'discount',
                color: 'emerald',
              },
              user_feedback: null,
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
    expect(screen.getAllByText('$22,500').length).toBeGreaterThan(0)
    const card = screen.getByTestId('marketplace-match-card')
    expect(within(card).getByText('NEW')).toBeInTheDocument()
    expect(within(card).getByText('RECENTLY SEEN')).toBeInTheDocument()
    expect(within(card).getByText(/first found/i)).toBeInTheDocument()
    expect(within(card).getByText(/last seen/i)).toBeInTheDocument()
    expect(screen.getByText(/below local median/i)).toBeInTheDocument()
    expect(screen.getByText(/photos: 2/i)).toBeInTheDocument()
    expect(screen.getByText(/source: search card/i)).toBeInTheDocument()
    expect(screen.getByText(/preserved search-card price/i)).toBeInTheDocument()
    expect(screen.getByAltText(/listing photo for 2014 toyota hilux sr5 4x4/i)).toBeInTheDocument()
    expect(screen.getByText(/used-market value/i)).toBeInTheDocument()
    expect(screen.getAllByText(/good value/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/nvidia rtx 3090/i)).toBeInTheDocument()
    expect(screen.getByText(/matched candidate/i)).toBeInTheDocument()
    expect(screen.getByText(/candidate match/i)).toBeInTheDocument()
    expect(screen.getByText(/listing is below the used median/i)).toBeInTheDocument()
    expect(screen.getByText(/price comparison/i)).toBeInTheDocument()
    expect(screen.getByText(/marketplace avg/i)).toBeInTheDocument()
    expect(screen.getByText(/value 84 - good value/i)).toBeInTheDocument()
    expect(screen.getByText(/group vehicle \/ toyota hilux/i)).toBeInTheDocument()
    expect(screen.getByText(/bench high/i)).toBeInTheDocument()
    expect(screen.getByText(/drop 4.3%/i)).toBeInTheDocument()
    expect(screen.getByText(/no alert: used-market discount is unknown/i)).toBeInTheDocument()
    expect(screen.getByText(/vs used -10%/i)).toBeInTheDocument()
    expect(screen.getByText(/n=6/i)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('uses first-found recency for Newest and preserves score sorting', async () => {
    const makeMatch = (overrides: Record<string, unknown>) => ({
      match_id: 'mp_match_default',
      mission_id: 'mp_mission_default',
      mission_name: 'Default mission',
      listing_id: 'listing_default',
      listing_url: 'https://www.facebook.com/marketplace/item/default/',
      title: 'Default listing',
      price: '$100',
      location: 'Melbourne VIC',
      captured_at: '2026-05-04T01:28:29Z',
      first_found_at: '2026-05-04T01:28:29Z',
      last_seen_at: '2026-05-04T01:28:29Z',
      score: 50,
      decision_band: 'candidate',
      reasons_for: ['Matched mission keyword'],
      reasons_against: [],
      confidence: 0.66,
      raw_text_snapshot: 'Visible listing text',
      listing_media: [],
      status: 'new',
      metadata: {},
      user_feedback: null,
      updated_at: '2026-05-04T01:28:29Z',
      ...overrides,
    })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          makeMatch({
            match_id: 'mp_match_low',
            mission_id: 'mp_mission_furniture',
            mission_name: 'Furniture',
            listing_id: 'listing_low',
            title: 'Office chair',
            score: 63,
            first_found_at: '2026-05-06T09:00:00Z',
            captured_at: '2026-05-06T09:05:00Z',
          }),
          makeMatch({
            match_id: 'mp_match_high',
            mission_id: 'mp_mission_gpu',
            mission_name: 'GPU',
            listing_id: 'listing_high',
            title: 'RTX 4090 GPU',
            score: 96,
            first_found_at: '2026-05-04T09:00:00Z',
            captured_at: '2026-05-06T12:00:00Z',
          }),
          makeMatch({
            match_id: 'mp_match_mid',
            mission_id: 'mp_mission_vehicle',
            mission_name: 'Vehicle',
            listing_id: 'listing_mid',
            title: 'Toyota Hilux',
            score: 81,
            first_found_at: '2026-05-05T09:00:00Z',
            captured_at: '2026-05-05T09:05:00Z',
          }),
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('RTX 4090 GPU')).toBeInTheDocument()
    })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/cockpit/marketplace/matches?sort=first_found_desc')
    const cardTitles = screen
      .getAllByTestId('marketplace-match-card')
      .map((card) => within(card).getByRole('heading', { level: 3 }).textContent)
    expect(cardTitles).toEqual(['Office chair', 'Toyota Hilux', 'RTX 4090 GPU'])
    expect(screen.getByTestId('marketplace-match-grid')).toHaveClass('xl:grid-cols-3')

    installPointerCaptureMock()
    await userEvent.click(screen.getAllByRole('combobox')[2])
    await userEvent.click(screen.getByRole('option', { name: /best score/i }))

    await waitFor(() => {
      const scoreSortedTitles = screen
        .getAllByTestId('marketplace-match-card')
        .map((card) => within(card).getByRole('heading', { level: 3 }).textContent)
      expect(scoreSortedTitles).toEqual(['RTX 4090 GPU', 'Toyota Hilux', 'Office chair'])
    })

    await userEvent.click(screen.getByLabelText(/select rtx 4090 gpu/i))
    expect(screen.getByText(/1 selected/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^dismiss$/i })).toBeEnabled()
  })

  it('filters New only to status-new or recently first-found matches', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-05-07T00:00:00Z'))
    const makeMatch = (overrides: Record<string, unknown>) => ({
      match_id: 'mp_match_default',
      mission_id: 'mp_mission_default',
      mission_name: 'Default mission',
      listing_id: 'listing_default',
      listing_url: 'https://www.facebook.com/marketplace/item/default/',
      title: 'Default listing',
      price: '$100',
      location: 'Melbourne VIC',
      captured_at: '2026-05-01T00:00:00Z',
      first_found_at: '2026-05-01T00:00:00Z',
      last_seen_at: '2026-05-01T00:00:00Z',
      score: 50,
      decision_band: 'candidate',
      reasons_for: ['Matched mission keyword'],
      reasons_against: [],
      confidence: 0.66,
      raw_text_snapshot: 'Visible listing text',
      listing_media: [],
      status: 'reviewed',
      metadata: {},
      user_feedback: null,
      updated_at: '2026-05-01T00:00:00Z',
      ...overrides,
    })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          makeMatch({
            match_id: 'mp_match_recent_reviewed',
            title: 'Recently first-found reviewed listing',
            first_found_at: '2026-05-06T10:00:00Z',
            last_seen_at: '2026-05-06T10:00:00Z',
          }),
          makeMatch({
            match_id: 'mp_match_status_new',
            title: 'Status-new older listing',
            first_found_at: '2026-04-20T10:00:00Z',
            last_seen_at: '2026-04-20T10:00:00Z',
            status: 'new',
          }),
          makeMatch({
            match_id: 'mp_match_old_reviewed',
            title: 'Old reviewed listing',
            first_found_at: '2026-04-01T10:00:00Z',
            last_seen_at: '2026-04-01T10:00:00Z',
          }),
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('Old reviewed listing')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByLabelText(/new only/i))

    expect(screen.getByText('Recently first-found reviewed listing')).toBeInTheDocument()
    expect(screen.getByText('Status-new older listing')).toBeInTheDocument()
    expect(screen.queryByText('Old reviewed listing')).not.toBeInTheDocument()
  })

  it('explains when a listing price exists but benchmark anchors are missing', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            match_id: 'mp_match_listing_only',
            mission_id: 'mp_mission_storage',
            mission_name: 'NVMe storage',
            listing_id: '123',
            listing_url: 'https://www.facebook.com/marketplace/item/123/',
            title: 'Kingston NV2 2TB NVMe SSD',
            price: 'AU$300 Kingston NV2 2TB NVMe SSD Melbourne, VIC',
            price_value: 300,
            location: 'Melbourne VIC',
            captured_at: '2026-05-04T01:28:29Z',
            score: 95,
            decision_band: 'strong_match',
            reasons_for: ['Matched mission keyword: 2TB'],
            reasons_against: [],
            confidence: 0.66,
            raw_text_snapshot: 'Kingston NV2 2TB NVMe SSD.',
            listing_media: [],
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
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('Kingston NV2 2TB NVMe SSD')).toBeInTheDocument()
    })
    expect(screen.getByText('Needs setup')).toBeInTheDocument()
    expect(screen.getByText(/benchmark unavailable/i)).toBeInTheDocument()
    expect(screen.getByText(/listing price was captured/i)).toBeInTheDocument()
    expect(screen.getByText(/tracked product benchmark/i)).toBeInTheDocument()
  })

  it('explains when a low-confidence retail anchor is ignored', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            match_id: 'mp_match_ignored_anchor',
            mission_id: 'mp_mission_ram',
            mission_name: 'RAM',
            listing_id: '123',
            listing_url: 'https://www.facebook.com/marketplace/item/123/',
            title: 'Corsair Vengeance LPX 32GB DDR4',
            price: '$50',
            price_value: 50,
            location: 'Melbourne VIC',
            captured_at: '2026-05-04T01:28:29Z',
            score: 80,
            decision_band: 'candidate',
            reasons_for: ['Matched mission keyword: 32GB'],
            reasons_against: [],
            confidence: 0.66,
            raw_text_snapshot: 'Corsair Vengeance LPX 32GB DDR4.',
            listing_media: [],
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
              ignored_retail_anchor: {
                price: 189,
                review_status: 'pending_review',
                low_confidence: true,
                reason: 'the retail benchmark match still requires review',
              },
            },
            user_feedback: null,
            updated_at: '2026-05-04T01:28:29Z',
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('Corsair Vengeance LPX 32GB DDR4')).toBeInTheDocument()
    })
    expect(screen.getByText(/retail anchor needs review/i)).toBeInTheDocument()
    expect(screen.getByText(/not used/i)).toBeInTheDocument()
    expect(screen.getByText(/accept the retail benchmark review/i)).toBeInTheDocument()
  })

  it('records interested feedback on a match card', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              match_id: 'mp_match_feedback',
              mission_id: 'mp_mission_1',
              mission_name: 'GPU mission',
              listing_id: '789',
              listing_url: 'https://www.facebook.com/marketplace/item/789/',
              title: 'RTX 3090 24GB',
              price: '$900',
              price_value: 900,
              location: 'Sydney NSW',
              captured_at: '2026-04-18T10:00:00Z',
              score: 91,
              decision_band: 'strong_match',
              reasons_for: ['Strong product match'],
              reasons_against: [],
              confidence: 0.9,
              raw_text_snapshot: 'Visible listing text',
              status: 'new',
              metadata: {},
              price_comparison: {
                listing_price: 900,
                used_market_median: 1200,
                delta_vs_used_median: { amount: -300, percent: -25 },
                verdict: 'strong_discount',
                color: 'green',
              },
              user_feedback: null,
              updated_at: '2026-04-18T10:00:00Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: 'mp_match_feedback',
          mission_id: 'mp_mission_1',
          mission_name: 'GPU mission',
          listing_id: '789',
          listing_url: 'https://www.facebook.com/marketplace/item/789/',
          title: 'RTX 3090 24GB',
          price: '$900',
          price_value: 900,
          location: 'Sydney NSW',
          captured_at: '2026-04-18T10:00:00Z',
          score: 91,
          decision_band: 'strong_match',
          reasons_for: ['Strong product match'],
          reasons_against: [],
          confidence: 0.9,
          raw_text_snapshot: 'Visible listing text',
          status: 'new',
          metadata: {},
          price_comparison: {
            listing_price: 900,
            used_market_median: 1200,
            delta_vs_used_median: { amount: -300, percent: -25 },
            verdict: 'strong_discount',
            color: 'green',
          },
          user_feedback: {
            match_id: 'mp_match_feedback',
            feedback: 'interested',
            note: null,
            created_at: '2026-04-18T10:01:00Z',
            updated_at: '2026-04-18T10:01:00Z',
          },
          updated_at: '2026-04-18T10:01:00Z',
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText('RTX 3090 24GB')).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('button', { name: /^interested$/i }))

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
          body: JSON.stringify({ feedback: 'interested', note: null }),
        }),
      )
    })
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
    expect(screen.getByText(/first found \(capture\)/i)).toBeInTheDocument()
  })

  it('explains when no Marketplace missions exist for empty matches', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/cockpit/marketplace/matches')) {
        return Promise.resolve(jsonResponse({ items: [] }))
      }
      if (url.includes('/api/cockpit/marketplace/missions')) {
        return Promise.resolve(jsonResponse({ items: [] }))
      }
      return Promise.reject(new Error(`unexpected fetch ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText(/no Marketplace missions configured yet/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/require a saved mission/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open mission setup/i })).toHaveAttribute('href', '/marketplace')
  })

  it('explains when active filters hide existing matches', async () => {
    installPointerCaptureMock()
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/cockpit/marketplace/missions')) {
        return Promise.resolve(jsonResponse({
          items: [
            {
              mission_id: 'mp_mission_1',
              name: 'GPU mission',
              status: 'active',
              mission_type: 'saved_search',
              brief: 'Find GPUs',
              category_hint: null,
              hard_filters: {},
              soft_preferences: {},
              search_config: {},
              scan_config: {},
              last_error: null,
              created_at: '2026-05-04T01:28:29Z',
              updated_at: '2026-05-04T01:28:29Z',
              last_scan_at: '2026-05-04T02:00:00Z',
            },
          ],
        }))
      }
      if (url.includes('/api/cockpit/marketplace/matches?status=new')) {
        return Promise.resolve(jsonResponse({ items: [] }))
      }
      if (url.includes('/api/cockpit/marketplace/matches')) {
        return Promise.resolve(jsonResponse({
          items: [minimalMatch({ title: 'Reviewed RTX 3090 listing' })],
        }))
      }
      return Promise.reject(new Error(`unexpected fetch ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMatchesScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('Reviewed RTX 3090 listing')).toBeInTheDocument()
    })

    await userEvent.click(screen.getAllByRole('combobox')[0])
    await userEvent.click(screen.getByRole('option', { name: /^new$/i }))

    await waitFor(() => {
      expect(screen.getByText(/filters are hiding existing matches/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/unfiltered Marketplace evidence contains 1 match/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /clear filters/i }))

    await waitFor(() => {
      expect(screen.getByText('Reviewed RTX 3090 listing')).toBeInTheDocument()
    })
  })
})
