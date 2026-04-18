import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceAlertsScreen } from './alerts-screen'

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
})
