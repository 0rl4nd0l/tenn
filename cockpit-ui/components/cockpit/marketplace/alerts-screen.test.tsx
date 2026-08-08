import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceAlertsScreen } from './alerts-screen'

function jsonResponse(body: unknown, ok = true) {
  return {
    ok,
    json: async () => body,
  }
}

describe('MarketplaceAlertsScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders Marketplace alerts', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [
            {
              alert_id: 'mp_alert_1',
              mission_id: 'mp_mission_1',
              mission_name: 'Dual-cab ute',
              match_id: 'mp_match_1',
              match_title: '2014 Toyota Hilux SR5 4x4',
              listing_url: 'https://www.facebook.com/marketplace/item/123/',
              price: '$22,500',
              location: 'Preston VIC',
              decision_band: 'strong_match',
              status: 'new',
              created_at: '2026-04-18T10:00:00Z',
              updated_at: '2026-04-18T10:00:00Z',
              trigger_reason: 'new_listing',
              metadata: {},
            },
          ],
        }),
      }),
    )

    render(<MarketplaceAlertsScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('2014 Toyota Hilux SR5 4x4')).toBeInTheDocument()
    })
    expect(screen.getByText(/trigger: new_listing/i)).toBeInTheDocument()
  })

  it('explains when missions exist but no alert-producing scan has run', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/cockpit/marketplace/alerts')) {
        return Promise.resolve(jsonResponse({ items: [] }))
      }
      if (url.includes('/api/cockpit/marketplace/missions')) {
        return Promise.resolve(jsonResponse({
          items: [
            {
              mission_id: 'mp_mission_1',
              name: 'Dual-cab ute',
              status: 'active',
              mission_type: 'saved_search',
              brief: 'Find dual-cab utes',
              category_hint: null,
              hard_filters: {},
              soft_preferences: {},
              search_config: {},
              scan_config: {},
              last_error: null,
              created_at: '2026-04-18T10:00:00Z',
              updated_at: '2026-04-18T10:00:00Z',
              last_scan_at: null,
            },
          ],
        }))
      }
      return Promise.reject(new Error(`unexpected fetch ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceAlertsScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText(/no scan run is recorded/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/none include last_scan_at/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open mission setup/i })).toHaveAttribute('href', '/marketplace')
  })

  it('preserves DATA_MISSING when mission context cannot explain empty alerts', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/cockpit/marketplace/alerts')) {
        return Promise.resolve(jsonResponse({ items: [] }))
      }
      if (url.includes('/api/cockpit/marketplace/missions')) {
        return Promise.resolve(jsonResponse({ detail: 'mission context unavailable' }, false))
      }
      return Promise.reject(new Error(`unexpected fetch ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceAlertsScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText(/DATA_MISSING: Marketplace mission context unavailable/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/could not be loaded: mission context unavailable/i)).toBeInTheDocument()
  })
})
