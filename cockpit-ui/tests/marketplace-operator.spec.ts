import { expect, test, type Page, type Route } from '@playwright/test'

type Mission = {
  mission_id: string
  name: string
  status: string
  mission_type: string
  brief: string
  user_goal: string | null
  category_hint: string | null
  hard_filters: Record<string, unknown>
  soft_preferences: Record<string, unknown>
  search_config: Record<string, unknown>
  scan_config: Record<string, unknown>
  benchmark_sources: string[]
  deployment_args: Record<string, unknown>
  last_error: string | null
  created_from_chat_message_id: string | null
  created_at: string
  updated_at: string
  last_scan_at: string | null
}

type ScanJob = {
  job_id: string
  action_id: 'marketplace_scan'
  mission_id: string | null
  status: string
  started_at: string
  ended_at: string | null
  exit_code: number | null
  stdout_path: string
  stderr_path: string
  progress_stage: string
  progress_pct: number
  result?: string
}

type Match = {
  match_id: string
  mission_id: string
  mission_name: string
  listing_id: string
  listing_url: string
  title: string
  price: string
  price_value: number
  location: string
  seller_name: string
  captured_at: string
  score: number
  decision_band: string
  reasons_for: string[]
  reasons_against: string[]
  confidence: number
  raw_text_snapshot: string
  listing_media?: string[]
  screenshot_path?: string | null
  status: string
  metadata: Record<string, unknown>
  benchmark: {
    source: string
    category: string
    matched_product: string | null
    current_price: number | null
    median_30d: number | null
    listing_delta_pct: number | null
    freshness_hours: number | null
    confidence: number
    low_confidence: boolean
    review_status: string
    warning: string | null
    rationale: string[]
    wording: string
  }
  updated_at: string
}

function nowIso(): string {
  return new Date('2026-04-22T10:00:00Z').toISOString()
}

function makeMission(id: string, name: string, status: string): Mission {
  return {
    mission_id: id,
    name,
    status,
    mission_type: 'find_good_deals',
    brief: `Mission brief for ${name}`,
    user_goal: `Find good deals for ${name}`,
    category_hint: 'gpu',
    hard_filters: {
      include_keywords: ['gpu'],
      exclude_keywords: [],
      location_names: ['Melbourne'],
      price_max: 2000,
    },
    soft_preferences: { preferred_brands: ['MSI'] },
    search_config: { query_variants_enabled: true, broadening_enabled: true, max_queries_per_run: 6 },
    scan_config: { scan_interval_minutes: 15, aggressive_alerting: false },
    benchmark_sources: ['centre_com'],
    deployment_args: {},
    last_error: null,
    created_from_chat_message_id: null,
    created_at: nowIso(),
    updated_at: nowIso(),
    last_scan_at: null,
  }
}

async function mockMarketplaceOperatorApis(page: Page): Promise<void> {
  let missionCounter = 1
  let jobCounter = 1
  let lastCreatedMissionId: string | null = null
  let missions: Mission[] = [makeMission('mp-seed-1', 'Seed Mission', 'paused')]
  let jobs: ScanJob[] = []

  const matches: Match[] = [
    {
      match_id: 'match-photo',
      mission_id: 'mp-seed-1',
      mission_name: 'Seed Mission',
      listing_id: 'listing-photo',
      listing_url: 'https://www.facebook.com/marketplace/item/listing-photo/',
      title: 'MSI GeForce RTX 4080 SUPER 16GB',
      price: '$1,500',
      price_value: 1500,
      location: 'Richmond VIC',
      seller_name: 'GPU Seller',
      captured_at: nowIso(),
      score: 92,
      decision_band: 'strong_match',
      reasons_for: ['Good condition', 'Price below new retail benchmark'],
      reasons_against: [],
      confidence: 0.91,
      raw_text_snapshot: 'RTX 4080 SUPER 16GB, like new.',
      listing_media: [
        'https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=1200&q=60',
        'https://images.unsplash.com/photo-1518773553398-650c184e0bb3?auto=format&fit=crop&w=1200&q=60',
      ],
      status: 'new',
      metadata: {},
      benchmark: {
        source: 'centre_com',
        category: 'gpu',
        matched_product: 'MSI GeForce RTX 4080 SUPER VENTUS 3X OC 16GB',
        current_price: 1899,
        median_30d: 1879,
        listing_delta_pct: -21,
        freshness_hours: 6,
        confidence: 0.93,
        low_confidence: false,
        review_status: 'auto_accepted',
        warning: null,
        rationale: ['GPU SKU aligned'],
        wording: 'new retail benchmark',
      },
      updated_at: nowIso(),
    },
    {
      match_id: 'match-no-photo',
      mission_id: 'mp-seed-1',
      mission_name: 'Seed Mission',
      listing_id: 'listing-no-photo',
      listing_url: 'https://www.facebook.com/marketplace/item/listing-no-photo/',
      title: 'DDR5 32GB kit',
      price: '$130',
      price_value: 130,
      location: 'Coburg VIC',
      seller_name: 'Memory Seller',
      captured_at: nowIso(),
      score: 71,
      decision_band: 'candidate',
      reasons_for: ['Likely RAM kit'],
      reasons_against: ['SKU incomplete'],
      confidence: 0.62,
      raw_text_snapshot: 'Unknown brand DDR5 32GB kit.',
      status: 'new',
      metadata: {},
      benchmark: {
        source: 'centre_com',
        category: 'ram_kit',
        matched_product: 'Corsair Vengeance 32GB (2x16GB) DDR5-6000 CL36 Memory Kit',
        current_price: 189,
        median_30d: 195,
        listing_delta_pct: -31,
        freshness_hours: 48,
        confidence: 0.61,
        low_confidence: true,
        review_status: 'pending_review',
        warning: 'Low-confidence benchmark match requires manual review.',
        rationale: ['Token overlap only'],
        wording: 'new retail benchmark',
      },
      updated_at: nowIso(),
    },
  ]

  const byId = (matchId: string): Match => matches.find((m) => m.match_id === matchId) ?? matches[0]

  await page.route('**/api/cockpit/**', async (route: Route) => {
    const request = route.request()
    const method = request.method()
    const url = new URL(request.url())
    const { pathname } = url

    if (pathname.endsWith('/api/cockpit/health')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          services: [
            { name: 'backend', status: 'healthy' },
            { name: 'gpu', status: 'healthy', details: { utilization_pct: 0 } },
            { name: 'host', status: 'healthy', details: { load_avg_1m: 0.5 } },
          ],
        }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/preferences')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          api_default_enabled: false,
          web_search_enabled: true,
          marketplace_home_location: 'Melbourne',
          marketplace_prefer_cloud_routing: false,
        }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/config')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          llm_model: 'model:qwen-test',
          max_tokens: 2048,
          temperature: 0.2,
        }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/browser-health')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ready',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
          challenge_detected: false,
          last_checked_at: nowIso(),
          detail: 'Marketplace browser profile is ready.',
        }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/chat') && method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          content: {
            answer: JSON.stringify({
              assistant_message: 'Draft ready. You can deploy this mission now.',
              draft: {
                missionType: 'find_good_deals',
                name: 'RTX mission from chat',
                brief: 'Find RTX GPUs under $1600 in Melbourne.',
                hardFilters: {
                  includeKeywords: ['rtx', 'gpu'],
                  locationNames: ['Melbourne'],
                  priceMax: 1600,
                },
                softPreferences: { preferredBrands: ['MSI'] },
              },
              missing_fields: [],
              ready_to_create: true,
              suggested_action: 'confirm_create',
            }),
            source: 'local',
            model: 'model:qwen-test',
          },
        }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/missions') && method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: missions }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/missions') && method === 'POST') {
      const payload = (request.postDataJSON() as Record<string, unknown>) ?? {}
      const missionId = `mp-created-${missionCounter++}`
      lastCreatedMissionId = missionId
      const created = makeMission(
        missionId,
        String(payload.name ?? `Mission ${missionCounter}`),
        String(payload.status ?? 'paused'),
      )
      created.brief = String(payload.brief ?? created.brief)
      created.created_from_chat_message_id = String(payload.created_from_chat_message_id ?? '') || null
      missions = [created, ...missions]
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(created),
      })
      return
    }

    const missionPathMatch = pathname.match(/\/api\/cockpit\/marketplace\/missions\/([^/]+)$/)
    if (missionPathMatch && method === 'PATCH') {
      const missionId = decodeURIComponent(missionPathMatch[1])
      const patch = (request.postDataJSON() as Record<string, unknown>) ?? {}
      missions = missions.map((mission) =>
        mission.mission_id === missionId
          ? { ...mission, ...patch, updated_at: nowIso() }
          : mission,
      ) as Mission[]
      const updated = missions.find((mission) => mission.mission_id === missionId)
      await route.fulfill({
        status: updated ? 200 : 404,
        contentType: 'application/json',
        body: JSON.stringify(updated ?? { detail: 'Marketplace mission not found' }),
      })
      return
    }

    if (missionPathMatch && method === 'DELETE') {
      const missionId = decodeURIComponent(missionPathMatch[1])
      const index = missions.findIndex((mission) => mission.mission_id === missionId)
      if (index < 0) {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Marketplace mission not found' }),
        })
        return
      }
      const activeForMission = jobs.some(
        (job) => job.mission_id === missionId && (job.status === 'queued' || job.status === 'running'),
      )
      if (activeForMission) {
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Mission has an active scan job. Cancel it before deleting the mission.' }),
        })
        return
      }
      missions.splice(index, 1)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          mission_id: missionId,
          status: 'deleted',
          deleted_missions: 1,
          deleted_seen_listings: 0,
          deleted_matches: 0,
          deleted_alerts: 0,
          deleted_listing_product_matches: 0,
          deleted_listing_benchmark_scores: 0,
        }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/scans') && method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: jobs }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/scans') && method === 'POST') {
      const payload = (request.postDataJSON() as Record<string, unknown>) ?? {}
      const missionId = String(payload.mission_id ?? lastCreatedMissionId ?? missions[0]?.mission_id ?? '')
      const id = `scan-${jobCounter++}`
      const startedAt = nowIso()
      const created: ScanJob = {
        job_id: id,
        action_id: 'marketplace_scan',
        mission_id: missionId || null,
        status: id === 'scan-1' ? 'queued' : 'running',
        started_at: startedAt,
        ended_at: null,
        exit_code: null,
        stdout_path: `/reports/cockpit/logs/${id}.out.log`,
        stderr_path: `/reports/cockpit/logs/${id}.err.log`,
        progress_stage: id === 'scan-1' ? 'Queued' : 'Collecting listing cards',
        progress_pct: id === 'scan-1' ? 0 : 24,
      }
      jobs = [created, ...jobs]
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(created),
      })
      return
    }

    const scanPathMatch = pathname.match(/\/api\/cockpit\/marketplace\/scans\/([^/]+)$/)
    if (scanPathMatch && method === 'GET') {
      const jobId = decodeURIComponent(scanPathMatch[1])
      const found = jobs.find((job) => job.job_id === jobId)
      if (!found) {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'scan not found' }),
        })
        return
      }
      const resultText =
        found.status === 'cancelled'
          ? 'Marketplace scan cancelled by user request.'
          : found.status === 'running'
            ? `Scan ${found.job_id} running...\nCollecting listings...`
            : found.status === 'queued'
              ? 'Scan queued...'
              : `Scan ${found.job_id} complete.`
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...found,
          result: resultText,
        }),
      })
      return
    }

    const stopPathMatch = pathname.match(/\/api\/cockpit\/action\/jobs\/([^/]+)\/stop$/)
    if (stopPathMatch && method === 'POST') {
      const jobId = decodeURIComponent(stopPathMatch[1])
      jobs = jobs.map((job) =>
        job.job_id === jobId
          ? {
              ...job,
              status: 'cancelled',
              progress_stage: 'Cancelled',
              progress_pct: 100,
              ended_at: nowIso(),
              exit_code: 130,
            }
          : job,
      )
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, job_id: jobId, status: 'cancelled' }),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/matches') && method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: matches }),
      })
      return
    }

    const matchPathMatch = pathname.match(/\/api\/cockpit\/marketplace\/matches\/([^/]+)$/)
    if (matchPathMatch && method === 'GET') {
      const matchId = decodeURIComponent(matchPathMatch[1])
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(byId(matchId)),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/marketplace/benchmarks/refresh')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          retailer: 'centre_com',
          observed_at: nowIso(),
          canonical_created: 0,
          retailer_products_created: 0,
          price_observations_added: 8,
          live_observations_added: 8,
          fallback_observations_added: 0,
          fetch_failures: [],
          categories: ['cpu', 'gpu', 'nvme_m2', 'ram_kit'],
        }),
      })
      return
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    })
  })
}

test.describe('Marketplace Operator Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await mockMarketplaceOperatorApis(page)
  })

  test('supports chat to mission deploy, scan output/cancel, delete, and photo+benchmark review', async ({
    page,
  }) => {
    await page.goto('/marketplace')

    await expect(page.getByRole('heading', { name: 'Marketplace Missions' })).toBeVisible()
    await expect(page.getByText('Marketplace Assistant')).toBeVisible()

    await page
      .getByPlaceholder('Describe what you want to buy, your budget, location, and deal-breakers...')
      .fill('Find used RTX 4080 cards under $1600 near Melbourne.')
    await expect(page.getByRole('button', { name: /^Send$/i })).toBeEnabled()
    await page.getByRole('button', { name: /^Send$/i }).click()
    await expect(page.getByText(/draft ready/i)).toBeVisible()
    await expect(page.getByText(/Mission Preview/i)).toBeVisible()
    await expect(page.locator('pre').filter({ hasText: '"mission_type": "find_good_deals"' })).toBeVisible()

    await page.getByRole('button', { name: /Deploy \+ Run Now/i }).click()
    await expect(page.getByText(/Created mission and queued scan/i)).toBeVisible()

    await page.getByRole('button', { name: /Inspect scan/i }).first().click()
    await expect(page.getByRole('log', { name: 'Marketplace scan output' })).toBeVisible()
    await expect(page.getByRole('log', { name: 'Marketplace scan output' })).toContainText(/scan/i)

    await page.locator('[data-slot="card"]').filter({ hasText: 'Scan Output' }).getByRole('button', { name: /^Stop Scan$/i }).click()
    await expect(page.getByText(/scan status: cancelled|scan cancellation requested/i)).toBeVisible()
    await expect(page.getByRole('log', { name: 'Marketplace scan output' })).toContainText(/cancelled/i)

    await page
      .getByPlaceholder('Describe what you want to buy, your budget, location, and deal-breakers...')
      .fill('Create another GPU sourcing mission with similar filters.')
    await page.getByRole('button', { name: /^Send$/i }).click()
    await expect(page.getByText(/draft ready/i)).toBeVisible()
    await page.getByRole('button', { name: /Deploy \+ Run Now/i }).click()
    await expect(page.getByRole('log', { name: 'Marketplace scan output' })).toContainText(/scan-2|running/i)

    page.once('dialog', (dialog) => {
      void dialog.accept()
    })
    await page.getByRole('button', { name: /Delete mission Seed Mission/i }).click()
    await expect(page.getByText(/Deleted mission Seed Mission/i)).toBeVisible()

    await expect(page.getByText('Listings & New Retail Benchmark Review')).toBeVisible()
    await expect(page.getByText(/wording: new retail benchmark/i).first()).toBeVisible()
    await expect(page.getByText(/needs review/i)).toBeVisible()
    await expect(page.getByText(/photos: 2/i)).toBeVisible()

    await page.getByRole('link').filter({ hasText: 'Matches' }).click()
    await expect(page).toHaveURL(/\/marketplace\/matches/)
    await expect(page.getByText('MSI GeForce RTX 4080 SUPER 16GB')).toBeVisible()
    await expect(page.getByText('DDR5 32GB kit')).toBeVisible()
    await expect(page.getByText(/listing photos unavailable/i)).toBeVisible()

    await page.locator('a[href*="/marketplace/matches/match-photo"]').first().click()
    await expect(page).toHaveURL(/\/marketplace\/matches\/match-photo/)
    await expect(page.getByAltText(/listing photo 1/i)).toBeVisible()
    await page.getByRole('link', { name: /Back to Matches/i }).click()

    await page.locator('a[href*="/marketplace/matches/match-no-photo"]').first().click()
    await expect(page).toHaveURL(/\/marketplace\/matches\/match-no-photo/)
    await expect(page.getByText(/listing photos unavailable for this capture/i)).toBeVisible()
    await expect(page.getByText(/low confidence/i)).toBeVisible()
    await expect(page.getByText(/review: pending_review/i)).toBeVisible()
  })
})
