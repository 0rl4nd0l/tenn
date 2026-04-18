import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMissionScreen } from './mission-screen'

describe('MarketplaceMissionScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders browser health, missions, and recent scan jobs', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'ready',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            logged_in: true,
            challenge_detected: false,
            last_checked_at: '2026-04-18T10:00:00Z',
            detail: 'Marketplace browser profile is ready.',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            items: [
              {
                mission_id: 'mp_mission_1',
                name: 'Dual-cab ute',
                status: 'active',
                brief: 'Find a reliable 4x4 dual cab under 25k.',
                category_hint: 'vehicles',
                hard_filters: {},
                soft_preferences: {},
                search_config: {},
                scan_config: {
                  strong_match_threshold: 85,
                  candidate_threshold: 70,
                },
                created_at: '2026-04-18T10:00:00Z',
                updated_at: '2026-04-18T10:00:00Z',
                last_scan_at: null,
              },
            ],
          }),
        })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              job_id: 'job-1',
              mission_name: 'Dual-cab ute',
              action_id: 'marketplace_scan',
              status: 'queued',
              progress_stage: 'Queued',
              started_at: '2026-04-18T10:00:00Z',
              items_found: null,
            },
          ],
        }),
      }),
    )

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getAllByText('Dual-cab ute').length).toBeGreaterThan(0)
    })
    expect(screen.getByText('ready')).toBeInTheDocument()
    expect(screen.getAllByText('Dual-cab ute').length).toBeGreaterThan(0)
    expect(screen.getByText('queued')).toBeInTheDocument()
  })

  it('launches the Marketplace browser even when apiKey is blank', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'browser_not_running',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
          logged_in: false,
          challenge_detected: false,
          last_checked_at: '2026-04-18T10:00:00Z',
          detail: 'Browser not running.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ result: 'Marketplace browser launched.' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'ready',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
          logged_in: true,
          challenge_detected: false,
          last_checked_at: '2026-04-18T10:01:00Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="" />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })

    await userEvent.click(screen.getByRole('button', { name: /launch browser/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/action/execute',
        expect.objectContaining({
          method: 'POST',
        }),
      )
    })
    expect(screen.getByText(/browser launch request sent/i)).toBeInTheDocument()
  })
})
