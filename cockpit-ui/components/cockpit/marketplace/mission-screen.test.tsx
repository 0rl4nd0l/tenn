import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceMissionScreen } from './mission-screen'

function findLastFetchCall(fetchMock: ReturnType<typeof vi.fn>, url: string) {
  const calls = fetchMock.mock.calls.filter((call) => call[0] === url)
  return calls[calls.length - 1]
}

function findLastFetchCallWithMethod(
  fetchMock: ReturnType<typeof vi.fn>,
  url: string,
  method: string,
) {
  const calls = fetchMock.mock.calls.filter(
    (call) =>
      call[0] === url &&
      String((call[1] as RequestInit | undefined)?.method || 'GET').toUpperCase() ===
        method.toUpperCase(),
  )
  return calls[calls.length - 1]
}

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
          json: async () => ({ items: [] }),
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
      expect(fetchMock).toHaveBeenCalledTimes(4)
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
          job_id: 'job-mp-new',
          action_id: 'marketplace_scan',
          status: 'queued',
          progress_stage: 'queued',
          progress_pct: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'ready',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
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
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(4)
    })

    await userEvent.type(screen.getByPlaceholderText(/vintage watches/i), 'RTX 3090')
    await userEvent.type(screen.getByPlaceholderText(/e\.g\. 1500/i), '900')
    await userEvent.type(
      screen.getByPlaceholderText(/describe what you are looking for/i),
      'Find a clean RTX 3090 around Melbourne with no repair history.',
    )
    await userEvent.type(screen.getByPlaceholderText(/rolex, omega, tudor/i), 'RTX 3090, NVIDIA')
    await userEvent.type(screen.getByPlaceholderText(/melbourne, richmond, box hill/i), 'Melbourne')
    await userEvent.click(screen.getByRole('switch', { name: /auto scan for new mission/i }))
    await userEvent.clear(screen.getByPlaceholderText(/e\.g\. 5/i))
    await userEvent.type(screen.getByPlaceholderText(/e\.g\. 5/i), '3')
    const createMissionCard = screen.getByText(/create new mission/i).closest('[data-slot="card"]')
    expect(createMissionCard).toBeTruthy()
    await userEvent.click(
      within(createMissionCard as HTMLElement).getByRole('button', { name: /^create mission$/i }),
    )

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(10)
    })

    const createMissionCall = findLastFetchCallWithMethod(
      fetchMock,
      '/api/cockpit/marketplace/missions',
      'POST',
    )
    expect(createMissionCall).toBeDefined()
    expect(JSON.parse(String(createMissionCall?.[1]?.body))).toEqual(
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
    expect(findLastFetchCall(fetchMock, '/api/cockpit/marketplace/scans')).toBeDefined()
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
      expect(findLastFetchCall(fetchMock, '/api/cockpit/marketplace/missions/mp-mission-1')).toBeDefined()
    })
    const autoScanToggleCall = findLastFetchCall(
      fetchMock,
      '/api/cockpit/marketplace/missions/mp-mission-1',
    )
    expect(JSON.parse(String(autoScanToggleCall?.[1]?.body))).toEqual({ status: 'active' })

    const cadenceInput = screen.getByRole('spinbutton', { name: /scan cadence for gpu hunter/i })
    await userEvent.clear(cadenceInput)
    await userEvent.type(cadenceInput, '5')
    await userEvent.click(screen.getByRole('button', { name: /save cadence/i }))

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.filter(
          (call) => call[0] === '/api/cockpit/marketplace/missions/mp-mission-1',
        ).length,
      ).toBeGreaterThanOrEqual(2)
    })
    const cadenceSaveCall = fetchMock.mock.calls
      .filter((call) => call[0] === '/api/cockpit/marketplace/missions/mp-mission-1')
      .at(-1)
    expect(JSON.parse(String(cadenceSaveCall?.[1]?.body))).toEqual(
      expect.objectContaining({
        scan_config: expect.objectContaining({
          scan_interval_minutes: 5,
        }),
      }),
    )
    expect(screen.getByText(/auto scan cadence updated to every 5 minutes/i)).toBeInTheDocument()
  })

  it('shows a headless attach warning when CDP is reachable but Marketplace probing times out', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/cockpit/marketplace/browser-health') {
        return {
          ok: true,
          json: async () => ({
            status: 'browser_unavailable',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            challenge_detected: false,
            last_checked_at: '2026-04-19T00:30:00Z',
            detail:
              'marketplace_browser_unavailable: Browser debugger is reachable, but the Marketplace probe timed out during CDP attach after about 5s. This Chrome session is running in headless mode, and the current Marketplace probe could not attach cleanly through Playwright CDP.',
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/missions') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/scans') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/matches') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      return { ok: false, json: async () => ({ detail: `Unhandled URL in test: ${url}` }) }
    })

    vi.stubGlobal('fetch', fetchMock)

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

  it('blocks scan controls when Facebook reports a checkpoint challenge', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = String(init?.method || 'GET').toUpperCase()
      if (url === '/api/cockpit/marketplace/browser-health') {
        return {
          ok: true,
          json: async () => ({
            status: 'challenge_detected',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            challenge_detected: true,
            last_checked_at: '2026-04-19T00:30:00Z',
            detail: 'The browser session hit a Facebook checkpoint or challenge page.',
            scan_allowed: false,
            scan_blocker: 'The browser session hit a Facebook checkpoint or challenge page.',
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/missions') {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                mission_id: 'mp-challenge-1',
                name: 'GPU challenge mission',
                status: 'active',
                brief: 'Find a suitable GPU in Melbourne.',
                category_hint: 'electronics',
                hard_filters: {},
                soft_preferences: {},
                search_config: {},
                scan_config: { scan_interval_minutes: 15, aggressive_alerting: false },
                created_at: '2026-04-19T00:00:00Z',
                updated_at: '2026-04-19T00:00:00Z',
                last_scan_at: null,
              },
            ],
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/scans' && method === 'GET') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/matches') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      return { ok: false, json: async () => ({ detail: `Unhandled URL in test: ${url}` }) }
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="" />)

    await waitFor(() => {
      expect(screen.getByText(/facebook checkpoint is blocking marketplace scans/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/clear the checkpoint or challenge/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /scan now/i })).toBeDisabled()
    expect(
      fetchMock.mock.calls.some(
        (call) =>
          call[0] === '/api/cockpit/marketplace/scans' &&
          String((call[1] as RequestInit | undefined)?.method || 'GET').toUpperCase() === 'POST',
      ),
    ).toBe(false)
  })

  it('keeps benchmark review listings at the bottom and sorts by mission or missing data', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/cockpit/marketplace/browser-health') {
        return {
          ok: true,
          json: async () => ({
            status: 'ready',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            challenge_detected: false,
            last_checked_at: '2026-04-30T08:00:00Z',
            detail: 'Marketplace browser profile is ready.',
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/missions') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/scans') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/matches') {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                match_id: 'match-beta',
                mission_id: 'mission-beta',
                mission_name: 'Beta Storage',
                listing_id: 'listing-beta',
                listing_url: 'https://example.test/beta',
                title: 'CUSU SSD 2TB Brand New in Box',
                price: null,
                price_value: null,
                location: 'Melbourne',
                seller_name: 'Seller B',
                captured_at: '2026-04-30T09:00:00Z',
                score: 42,
                decision_band: 'needs_review',
                reasons_for: [],
                reasons_against: [],
                confidence: 0.2,
                raw_text_snapshot: '',
                screenshot_path: null,
                listing_media: [],
                status: 'new',
                metadata: {
                  price_evidence: {
                    source: 'search_card',
                    warning: 'Card price was unavailable.',
                  },
                },
                benchmark: {
                  source: 'centre_com',
                  category: 'storage',
                  matched_product: null,
                  current_price: null,
                  median_30d: null,
                  listing_delta_pct: null,
                  freshness_hours: null,
                  confidence: 0.2,
                  low_confidence: true,
                  review_status: 'pending_review',
                  warning: 'Low-confidence benchmark match requires manual review.',
                  rationale: [],
                  wording: 'new retail benchmark',
                },
                value_context: null,
                updated_at: '2026-04-30T09:00:00Z',
              },
              {
                match_id: 'match-alpha',
                mission_id: 'mission-alpha',
                mission_name: 'Alpha Storage',
                listing_id: 'listing-alpha',
                listing_url: 'https://example.test/alpha',
                title: 'Alpha SSD 2TB listing',
                price: 'A$180',
                price_value: 180,
                location: 'Melbourne',
                seller_name: 'Seller A',
                captured_at: '2026-04-30T08:00:00Z',
                score: 91,
                decision_band: 'strong_match',
                reasons_for: [],
                reasons_against: [],
                confidence: 0.9,
                raw_text_snapshot: '',
                screenshot_path: null,
                listing_media: [],
                status: 'new',
                metadata: {
                  price_evidence: {
                    source: 'detail',
                    resolved_price_text: 'A$180',
                    resolved_price_value: 180,
                  },
                },
                benchmark: {
                  source: 'centre_com',
                  category: 'storage',
                  matched_product: 'Crucial P3 Plus 2TB',
                  current_price: 197,
                  median_30d: 205,
                  listing_delta_pct: -12.2,
                  freshness_hours: 12,
                  confidence: 0.86,
                  low_confidence: false,
                  review_status: 'auto_scored',
                  warning: null,
                  rationale: ['Matched capacity and NVMe wording.'],
                  wording: 'new retail benchmark',
                },
                value_context: null,
                updated_at: '2026-04-30T08:00:00Z',
              },
            ],
          }),
        }
      }
      return { ok: false, json: async () => ({ detail: `Unhandled URL in test: ${url}` }) }
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('Listings & New Retail Benchmark Review')).toBeInTheDocument()
    })

    const scanOutputHeading = screen.getByText('Scan Output')
    const reviewHeading = screen.getByText('Listings & New Retail Benchmark Review')
    expect(
      Boolean(scanOutputHeading.compareDocumentPosition(reviewHeading) & Node.DOCUMENT_POSITION_FOLLOWING),
    ).toBe(true)

    let reviewCards = screen.getAllByTestId('marketplace-benchmark-listing')
    expect(within(reviewCards[0]).getByText('Alpha SSD 2TB listing')).toBeInTheDocument()
    expect(within(reviewCards[1]).getByText('CUSU SSD 2TB Brand New in Box')).toBeInTheDocument()

    await userEvent.selectOptions(
      screen.getByLabelText(/sort benchmark review listings/i),
      'missing',
    )

    await waitFor(() => {
      reviewCards = screen.getAllByTestId('marketplace-benchmark-listing')
      expect(within(reviewCards[0]).getByText('CUSU SSD 2TB Brand New in Box')).toBeInTheDocument()
    })
    expect(within(reviewCards[0]).getByText('Listing price missing')).toBeInTheDocument()
    expect(within(reviewCards[0]).getByText('Current retail price missing')).toBeInTheDocument()
  })

  it('uses price comparison state in benchmark review cards', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/cockpit/marketplace/browser-health') {
        return {
          ok: true,
          json: async () => ({
            status: 'ready',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            challenge_detected: false,
            last_checked_at: '2026-05-04T08:00:00Z',
            detail: 'Marketplace browser profile is ready.',
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/missions') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/scans') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/matches') {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                match_id: 'match-listing-only',
                mission_id: 'mission-storage',
                mission_name: 'Storage',
                listing_id: 'listing-storage',
                listing_url: 'https://example.test/storage',
                title: 'Kingston NV2 2TB NVMe SSD',
                price: 'AU$300 Kingston NV2 2TB NVMe SSD Melbourne, VIC',
                price_value: 300,
                location: 'Melbourne',
                seller_name: null,
                captured_at: '2026-05-04T08:00:00Z',
                score: 95,
                decision_band: 'strong_match',
                reasons_for: ['Matched mission keyword: 2TB'],
                reasons_against: [],
                confidence: 0.9,
                raw_text_snapshot: 'Kingston NV2 2TB NVMe SSD',
                screenshot_path: null,
                listing_media: [],
                status: 'new',
                metadata: {},
                benchmark: null,
                value_context: null,
                price_comparison: {
                  listing_price: 300,
                  used_market_median: null,
                  retail_anchor_price: null,
                  verdict: 'unavailable',
                  color: 'slate',
                  comparison_state: 'missing_benchmark_anchor',
                  unavailable_reason:
                    'Listing price was captured, but no used-market benchmark or retail/RRP anchor is available for the matched product.',
                  next_action:
                    'Link or calibrate a tracked product benchmark, then add accepted marketplace observations or a retail anchor.',
                },
                updated_at: '2026-05-04T08:00:00Z',
              },
            ],
          }),
        }
      }
      return { ok: false, json: async () => ({ detail: `Unhandled URL in test: ${url}` }) }
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('Kingston NV2 2TB NVMe SSD')).toBeInTheDocument()
    })
    const card = screen.getByTestId('marketplace-benchmark-listing')
    expect(within(card).getByText('needs setup')).toBeInTheDocument()
    expect(within(card).getByText('benchmark unavailable')).toBeInTheDocument()
    expect(within(card).getByText(/listing price was captured/i)).toBeInTheDocument()
    expect(within(card).getByText(/tracked product benchmark/i)).toBeInTheDocument()
    expect(within(card).queryByText('Listing price missing')).not.toBeInTheDocument()
  })

  it('links and unlinks one primary tracked product for a mission', async () => {
    let linked = false
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = String(init?.method || 'GET').toUpperCase()

      if (url === '/api/cockpit/marketplace/browser-health') {
        return {
          ok: true,
          json: async () => ({
            status: 'ready',
            cdp_url: 'http://127.0.0.1:9222',
            browser_family: 'chrome',
            profile_path: '/tmp/profile',
            challenge_detected: false,
            last_checked_at: '2026-04-24T00:00:00Z',
            detail: 'Marketplace browser profile is ready.',
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/missions' && method === 'GET') {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                mission_id: 'mp-link-1',
                name: 'GPU value mission',
                status: 'active',
                brief: 'Find RTX 3090 listings.',
                category_hint: 'gpu',
                hard_filters: {},
                soft_preferences: {},
                search_config: {},
                scan_config: { scan_interval_minutes: 15, aggressive_alerting: false },
                created_at: '2026-04-24T00:00:00Z',
                updated_at: '2026-04-24T00:00:00Z',
                last_scan_at: null,
                primary_tracked_product: linked
                  ? {
                      mission_id: 'mp-link-1',
                      tracked_product_id: 'tp_3090',
                      link_type: 'primary',
                      created_at: '2026-04-24T00:00:01Z',
                      updated_at: '2026-04-24T00:00:01Z',
                      tracked_product: {
                        tracked_product_id: 'tp_3090',
                        canonical_key: 'gpu:nvidia:rtx_3090',
                        category: 'gpu',
                        brand: 'NVIDIA',
                        model_family: 'RTX 3090',
                        variant: null,
                        attributes: {},
                        aliases: [],
                        negative_terms: [],
                        status: 'active',
                        created_at: '2026-04-24T00:00:00Z',
                        updated_at: '2026-04-24T00:00:00Z',
                      },
                    }
                  : null,
                benchmark_state: linked
                  ? {
                      status: 'scored',
                      freshness_status: 'fresh',
                      confidence_label: 'medium',
                      sample_size: 6,
                      snapshot_id: 'snap_1',
                      fair_low: 760,
                      fair_high: 980,
                      used_median: 870,
                      warnings: [],
                      notes: [],
                    }
                  : null,
              },
            ],
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/scans') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/matches') {
        return { ok: true, json: async () => ({ items: [] }) }
      }
      if (url === '/api/cockpit/marketplace/price-intelligence/tracked-products') {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                tracked_product_id: 'tp_3090',
                canonical_key: 'gpu:nvidia:rtx_3090',
                category: 'gpu',
                brand: 'NVIDIA',
                model_family: 'RTX 3090',
                variant: null,
                attributes: {},
                aliases: [],
                negative_terms: [],
                status: 'active',
                created_at: '2026-04-24T00:00:00Z',
                updated_at: '2026-04-24T00:00:00Z',
              },
            ],
          }),
        }
      }
      if (url === '/api/cockpit/marketplace/missions/mp-link-1/link-product' && method === 'POST') {
        linked = true
        return {
          ok: true,
          json: async () => ({ mission_id: 'mp-link-1' }),
        }
      }
      if (
        url === '/api/cockpit/marketplace/missions/mp-link-1/link-product' &&
        method === 'DELETE'
      ) {
        linked = false
        return {
          ok: true,
          json: async () => ({ mission_id: 'mp-link-1' }),
        }
      }
      return { ok: false, json: async () => ({ detail: `Unhandled URL in test: ${method} ${url}` }) }
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('GPU value mission')).toBeInTheDocument()
    })
    expect(screen.getByText(/no primary tracked product linked/i)).toBeInTheDocument()
    expect(screen.getByText(/not linked/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /load tracked products/i }))

    const select = await screen.findByRole('combobox', {
      name: /linked tracked product for gpu value mission/i,
    })
    await userEvent.selectOptions(select, 'tp_3090')

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          (call) =>
            call[0] === '/api/cockpit/marketplace/missions/mp-link-1/link-product' &&
            String((call[1] as RequestInit | undefined)?.method || 'GET').toUpperCase() === 'POST',
        ),
      ).toBe(true)
    })
    const linkCall = findLastFetchCallWithMethod(
      fetchMock,
      '/api/cockpit/marketplace/missions/mp-link-1/link-product',
      'POST',
    )
    expect(JSON.parse(String(linkCall?.[1]?.body))).toEqual({ tracked_product_id: 'tp_3090' })
    expect(await screen.findByText(/linked gpu value mission to nvidia rtx 3090/i)).toBeInTheDocument()
    expect(screen.getByText('fresh')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()

    const linkedSelect = screen.getByRole('combobox', {
      name: /linked tracked product for gpu value mission/i,
    })
    await userEvent.selectOptions(linkedSelect, '')

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          (call) =>
            call[0] === '/api/cockpit/marketplace/missions/mp-link-1/link-product' &&
            String((call[1] as RequestInit | undefined)?.method || 'GET').toUpperCase() === 'DELETE',
        ),
      ).toBe(true)
    })
    expect(screen.getByText(/unlinked tracked product from gpu value mission/i)).toBeInTheDocument()
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
        json: async () => ({ items: [] }),
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
      '/api/cockpit/marketplace/scans/job-2?tail=500',
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
        json: async () => ({ items: [] }),
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
        json: async () => ({ items: [] }),
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

    const outputCard = screen.getByText('Scan Output').closest('[data-slot="card"]')
    expect(outputCard).toBeTruthy()
    await userEvent.click(
      within(outputCard as HTMLElement).getByRole('button', { name: /^stop scan$/i }),
    )

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
      expect(findLastFetchCall(fetchMock, '/api/cockpit/marketplace/missions/mp-edit-1')).toBeDefined()
    })
    const saveEditCall = findLastFetchCall(fetchMock, '/api/cockpit/marketplace/missions/mp-edit-1')
    expect(JSON.parse(String(saveEditCall?.[1]?.body))).toEqual(
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

  it('deletes a non-running mission from the active list', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'ready',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
          challenge_detected: false,
          last_checked_at: '2026-04-22T01:00:00Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              mission_id: 'mp-del-1',
              name: 'Disposable mission',
              status: 'paused',
              brief: 'Temporary mission to delete.',
              category_hint: 'gpu',
              hard_filters: {},
              soft_preferences: {},
              search_config: {},
              scan_config: { scan_interval_minutes: 15, aggressive_alerting: false },
              created_at: '2026-04-22T01:00:00Z',
              updated_at: '2026-04-22T01:00:00Z',
              last_scan_at: null,
            },
          ],
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ok: true,
          mission_id: 'mp-del-1',
          status: 'deleted',
          deleted_missions: 1,
          deleted_seen_listings: 0,
          deleted_matches: 0,
          deleted_alerts: 0,
          deleted_listing_product_matches: 0,
          deleted_listing_benchmark_scores: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'ready',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
          challenge_detected: false,
          last_checked_at: '2026-04-22T01:00:03Z',
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) })

    vi.stubGlobal('fetch', fetchMock)

    render(<MarketplaceMissionScreen apiKey="k" />)

    await waitFor(() => {
      expect(screen.getByText('Disposable mission')).toBeInTheDocument()
    })
    await userEvent.click(
      screen.getByRole('button', { name: /delete mission disposable mission/i }),
    )

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/cockpit/marketplace/missions/mp-del-1',
        expect.objectContaining({
          method: 'DELETE',
        }),
      )
    })
    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/deleted mission disposable mission/i)).toBeInTheDocument()
  })
})
