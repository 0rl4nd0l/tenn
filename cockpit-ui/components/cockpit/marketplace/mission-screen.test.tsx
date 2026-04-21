import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMissionScreen } from './mission-screen'

describe('MarketplaceMissionScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders browser health, missions, recent scan jobs, and selected scan output', async () => {
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
                progress_pct: 0,
                started_at: '2026-04-18T10:00:00Z',
                items_found: null,
              },
            ],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            job_id: 'job-1',
            action_id: 'marketplace_scan',
            status: 'queued',
            progress_stage: 'Queued',
            progress_pct: 0,
            started_at: '2026-04-18T10:00:00Z',
            result: 'queued output',
            stdout_path: '/reports/cockpit/logs/job-1.out.log',
          }),
        }),
    )

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getAllByText('Dual-cab ute').length).toBeGreaterThan(0)
    })
    expect(screen.getByText('ready')).toBeInTheDocument()
    expect(screen.getAllByText('Dual-cab ute').length).toBeGreaterThan(0)
    expect(screen.getAllByText('queued').length).toBeGreaterThan(0)
    expect(screen.getByText('Marketplace Assistant')).toBeInTheDocument()
    expect(screen.getByText('Scan Output')).toBeInTheDocument()
    expect(screen.getByText('queued output')).toBeInTheDocument()
    expect(screen.getByText('/reports/cockpit/logs/job-1.out.log')).toBeInTheDocument()
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

  it('shows a desktop-session warning before launch when the backend reports desktop_session_missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'desktop_session_missing',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            logged_in: false,
            challenge_detected: false,
            last_checked_at: '2026-04-18T10:00:00Z',
            detail: 'No graphical desktop session is available for a local Marketplace browser profile in this shell.',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ items: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ items: [] }),
        }),
    )

    render(<MarketplaceMissionScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText(/launch browser needs a graphical desktop session/i)).toBeInTheDocument()
    })
    expect(
      screen.getAllByText(/no graphical desktop session is available for a local marketplace browser profile in this shell/i).length,
    ).toBeGreaterThan(0)
    expect(
      screen.getByText(/marketplace_browser_helper\.py/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/launch chrome manually with remote debugging on port 9222, then refresh/i),
    ).toBeInTheDocument()
  })

  it('shows a headless attach warning when CDP is reachable but Marketplace probing times out', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            status: 'browser_unavailable',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            logged_in: false,
            challenge_detected: false,
            last_checked_at: '2026-04-19T00:30:00Z',
            detail:
              'marketplace_browser_unavailable: Browser debugger is reachable, but the Marketplace probe timed out during CDP attach after about 5s. This Chrome session is running in headless mode, and the current Marketplace probe could not attach cleanly through Playwright CDP.',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ items: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ items: [] }),
        }),
    )

    render(<MarketplaceMissionScreen apiKey="" />)

    await waitFor(() => {
      expect(
        screen.getByText(/headless chrome is exposing cdp, but marketplace probing is not attachable yet/i),
      ).toBeInTheDocument()
    })
    expect(screen.getAllByText(/timed out during cdp attach/i).length).toBeGreaterThan(0)
    expect(
      screen.getByText(/the current marketplace scanner still needs a cdp session that playwright can attach to/i),
    ).toBeInTheDocument()
  })

  it('loads new scan output when a recent scan is selected', async () => {
    const fetchMock = vi
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
          last_checked_at: '2026-04-20T01:00:00Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              job_id: 'job-1',
              action_id: 'marketplace_scan',
              status: 'running',
              progress_stage: 'Scanning mission one',
              progress_pct: 35,
              started_at: '2026-04-20T01:01:00Z',
            },
            {
              job_id: 'job-2',
              action_id: 'marketplace_scan',
              status: 'success',
              progress_stage: 'Marketplace scan complete',
              progress_pct: 100,
              started_at: '2026-04-20T01:02:00Z',
              ended_at: '2026-04-20T01:04:00Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-1',
          action_id: 'marketplace_scan',
          status: 'running',
          progress_stage: 'Scanning mission one',
          progress_pct: 35,
          started_at: '2026-04-20T01:01:00Z',
          result: 'job one output',
          stdout_path: '/reports/cockpit/logs/job-1.out.log',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-2',
          action_id: 'marketplace_scan',
          status: 'success',
          progress_stage: 'Marketplace scan complete',
          progress_pct: 100,
          started_at: '2026-04-20T01:02:00Z',
          ended_at: '2026-04-20T01:04:00Z',
          result: 'job two output',
          stdout_path: '/reports/cockpit/logs/job-2.out.log',
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('job one output')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /inspect scan job-2/i }))

    await waitFor(() => {
      expect(screen.getByText('job two output')).toBeInTheDocument()
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/marketplace/scans/job-2?tail=80',
      expect.objectContaining({
        cache: 'no-store',
      }),
    )
  })
})
