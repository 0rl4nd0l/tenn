import { render, screen, waitFor, within } from '@testing-library/react'
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

  it('creates a mission with explicit auto-scan status and cadence', async () => {
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
          last_checked_at: '2026-04-21T00:00:00Z',
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
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          mission_id: 'mp-new',
          name: 'RTX 3090',
          status: 'paused',
        }),
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
          last_checked_at: '2026-04-21T00:00:05Z',
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

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })

    await userEvent.type(screen.getByPlaceholderText(/vintage watches/i), 'RTX 3090')
    await userEvent.type(screen.getByPlaceholderText(/e\.g\. 1500/i), '900')
    await userEvent.type(
      screen.getByPlaceholderText(/describe what you are looking for/i),
      'Find a clean RTX 3090 around Melbourne with no repair history.',
    )
    await userEvent.type(screen.getByPlaceholderText(/rolex, omega, tudor/i), 'RTX 3090, NVIDIA')
    await userEvent.click(screen.getByRole('switch', { name: /auto scan for new mission/i }))
    await userEvent.clear(screen.getByPlaceholderText(/e\.g\. 5/i))
    await userEvent.type(screen.getByPlaceholderText(/e\.g\. 5/i), '3')
    const createMissionCard = screen.getByText(/create new mission/i).closest('[data-slot="card"]')
    expect(createMissionCard).toBeTruthy()
    await userEvent.click(
      within(createMissionCard as HTMLElement).getByRole('button', { name: /^create mission$/i }),
    )

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(7)
    })

    expect(fetchMock.mock.calls[3][0]).toBe('/api/cockpit/marketplace/missions')
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual(
      expect.objectContaining({
        name: 'RTX 3090',
        status: 'paused',
        scan_config: {
          scan_interval_minutes: 3,
          aggressive_alerting: false,
        },
        soft_preferences: {
          preferred_brands: [],
        },
      }),
    )
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

  it('lets the user toggle auto scan and save a faster cadence for an existing mission', async () => {
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
          last_checked_at: '2026-04-21T00:00:00Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              mission_id: 'mp-mission-1',
              name: 'GPU hunter',
              status: 'paused',
              brief: 'Watch for good value GPUs.',
              category_hint: 'electronics',
              hard_filters: {},
              soft_preferences: {},
              search_config: {},
              scan_config: {
                scan_interval_minutes: 15,
                aggressive_alerting: false,
              },
              created_at: '2026-04-21T00:00:00Z',
              updated_at: '2026-04-21T00:00:00Z',
              last_scan_at: '2026-04-21T00:10:00Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          mission_id: 'mp-mission-1',
          status: 'active',
        }),
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
          last_checked_at: '2026-04-21T00:00:05Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              mission_id: 'mp-mission-1',
              name: 'GPU hunter',
              status: 'active',
              brief: 'Watch for good value GPUs.',
              category_hint: 'electronics',
              hard_filters: {},
              soft_preferences: {},
              search_config: {},
              scan_config: {
                scan_interval_minutes: 15,
                aggressive_alerting: false,
              },
              created_at: '2026-04-21T00:00:00Z',
              updated_at: '2026-04-21T00:00:05Z',
              last_scan_at: '2026-04-21T00:10:00Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          mission_id: 'mp-mission-1',
          status: 'active',
        }),
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
          last_checked_at: '2026-04-21T00:00:10Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              mission_id: 'mp-mission-1',
              name: 'GPU hunter',
              status: 'active',
              brief: 'Watch for good value GPUs.',
              category_hint: 'electronics',
              hard_filters: {},
              soft_preferences: {},
              search_config: {},
              scan_config: {
                scan_interval_minutes: 5,
                aggressive_alerting: false,
              },
              created_at: '2026-04-21T00:00:00Z',
              updated_at: '2026-04-21T00:00:10Z',
              last_scan_at: '2026-04-21T00:10:00Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('GPU hunter')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('switch', { name: /auto scan gpu hunter/i }))

    await waitFor(() => {
      expect(fetchMock.mock.calls[3]?.[0]).toBe('/api/cockpit/marketplace/missions/mp-mission-1')
    })
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual({ status: 'active' })

    const cadenceInput = screen.getByRole('spinbutton', { name: /scan cadence for gpu hunter/i })
    await userEvent.clear(cadenceInput)
    await userEvent.type(cadenceInput, '5')
    await userEvent.click(screen.getByRole('button', { name: /save cadence/i }))

    await waitFor(() => {
      expect(fetchMock.mock.calls[7]?.[0]).toBe('/api/cockpit/marketplace/missions/mp-mission-1')
    })
    expect(JSON.parse(String(fetchMock.mock.calls[7][1]?.body))).toEqual(
      expect.objectContaining({
        scan_config: expect.objectContaining({
          scan_interval_minutes: 5,
        }),
      }),
    )
    expect(screen.getByText(/auto scan cadence updated to every 5 minutes/i)).toBeInTheDocument()
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

  it('stops a selected running marketplace scan', async () => {
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
          last_checked_at: '2026-04-21T02:00:00Z',
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
              job_id: 'job-stop-1',
              action_id: 'marketplace_scan',
              status: 'running',
              progress_stage: 'Collecting cards',
              progress_pct: 22,
              started_at: '2026-04-21T02:00:10Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-stop-1',
          action_id: 'marketplace_scan',
          status: 'running',
          progress_stage: 'Collecting cards',
          progress_pct: 22,
          started_at: '2026-04-21T02:00:10Z',
          result: 'still working',
          stdout_path: '/reports/cockpit/logs/job-stop-1.out.log',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ok: true,
          job_id: 'job-stop-1',
          status: 'cancelling',
        }),
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
          last_checked_at: '2026-04-21T02:00:15Z',
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
              job_id: 'job-stop-1',
              action_id: 'marketplace_scan',
              status: 'running',
              progress_stage: 'Cancelling',
              progress_pct: 22,
              started_at: '2026-04-21T02:00:10Z',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-stop-1',
          action_id: 'marketplace_scan',
          status: 'running',
          progress_stage: 'Cancelling',
          progress_pct: 22,
          started_at: '2026-04-21T02:00:10Z',
          result: 'still working',
          stdout_path: '/reports/cockpit/logs/job-stop-1.out.log',
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('still working')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /stop scan/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/action/jobs/job-stop-1/stop',
        expect.objectContaining({
          method: 'POST',
        }),
      )
    })
    expect(screen.getByText(/scan cancellation requested/i)).toBeInTheDocument()
  })

  it('edits an existing mission in place', async () => {
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
          last_checked_at: '2026-04-21T03:00:00Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              mission_id: 'mp-edit-1',
              name: 'GPU mission',
              status: 'active',
              brief: 'Find a GPU.',
              category_hint: 'electronics',
              hard_filters: {
                include_keywords: ['GPU'],
                exclude_keywords: ['broken'],
                location_names: ['Melbourne'],
                price_max: 500,
              },
              soft_preferences: {
                preferred_brands: ['MSI'],
              },
              search_config: {
                query_variants_enabled: true,
                broadening_enabled: true,
                max_queries_per_run: 6,
              },
              scan_config: {
                scan_interval_minutes: 15,
                aggressive_alerting: false,
              },
              created_at: '2026-04-21T03:00:00Z',
              updated_at: '2026-04-21T03:00:00Z',
              last_scan_at: null,
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          mission_id: 'mp-edit-1',
          name: 'GPU mission updated',
          status: 'paused',
        }),
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
          last_checked_at: '2026-04-21T03:00:05Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              mission_id: 'mp-edit-1',
              name: 'GPU mission updated',
              status: 'paused',
              brief: 'Find a clean RTX 3090 around Melbourne.',
              category_hint: 'electronics',
              hard_filters: {
                include_keywords: ['RTX 3090'],
                exclude_keywords: ['broken'],
                location_names: ['Melbourne', 'Richmond'],
                price_max: 900,
              },
              soft_preferences: {
                preferred_brands: ['MSI', 'ASUS'],
              },
              search_config: {
                query_variants_enabled: true,
                broadening_enabled: true,
                max_queries_per_run: 6,
              },
              scan_config: {
                scan_interval_minutes: 10,
                aggressive_alerting: false,
              },
              created_at: '2026-04-21T03:00:00Z',
              updated_at: '2026-04-21T03:00:05Z',
              last_scan_at: null,
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('GPU mission')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /edit mission/i }))

    const nameInput = screen.getByRole('textbox', { name: /edit name for gpu mission/i })
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'GPU mission updated')

    const briefInput = screen.getByRole('textbox', { name: /edit brief for gpu mission/i })
    await userEvent.clear(briefInput)
    await userEvent.type(briefInput, 'Find a clean RTX 3090 around Melbourne.')

    const includeInput = screen.getByRole('textbox', { name: /edit include keywords for gpu mission/i })
    await userEvent.clear(includeInput)
    await userEvent.type(includeInput, 'RTX 3090')

    const locationsInput = screen.getByRole('textbox', { name: /edit locations for gpu mission/i })
    await userEvent.clear(locationsInput)
    await userEvent.type(locationsInput, 'Melbourne, Richmond')

    const brandsInput = screen.getByRole('textbox', { name: /edit preferred brands for gpu mission/i })
    await userEvent.clear(brandsInput)
    await userEvent.type(brandsInput, 'MSI, ASUS')

    const priceInput = screen.getByRole('spinbutton', { name: /edit max price for gpu mission/i })
    await userEvent.clear(priceInput)
    await userEvent.type(priceInput, '900')

    const cadenceInput = screen.getByRole('spinbutton', { name: /edit scan cadence for gpu mission/i })
    await userEvent.clear(cadenceInput)
    await userEvent.type(cadenceInput, '10')

    await userEvent.click(screen.getByRole('switch', { name: /edit auto scan for gpu mission/i }))
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(fetchMock.mock.calls[3]?.[0]).toBe('/api/cockpit/marketplace/missions/mp-edit-1')
    })
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual(
      expect.objectContaining({
        name: 'GPU mission updated',
        status: 'paused',
        brief: 'Find a clean RTX 3090 around Melbourne.',
        hard_filters: expect.objectContaining({
          include_keywords: ['RTX 3090'],
          location_names: ['Melbourne', 'Richmond'],
          price_max: 900,
        }),
        soft_preferences: expect.objectContaining({
          preferred_brands: ['MSI', 'ASUS'],
        }),
        scan_config: expect.objectContaining({
          scan_interval_minutes: 10,
        }),
      }),
    )
    expect(screen.getByText(/saved changes for gpu mission/i)).toBeInTheDocument()
  }, 10_000)
})
