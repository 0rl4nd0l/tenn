import { expect, test, type Page, type Route } from '@playwright/test'

type HoldingRow = {
  holding_id: string
  ticker: string
  account_label: string | null
  thesis_bucket: string | null
  status: string | null
  quantity: number | null
  avg_cost: number | null
  cost_currency: string | null
  opened_at: string | null
  updated_at: string | null
  note: string | null
}

async function mockCockpitApis(page: Page): Promise<void> {
  let nextId = 3
  let holdings: HoldingRow[] = [
    {
      holding_id: 'h-1',
      ticker: 'BHP',
      account_label: 'Broker',
      thesis_bucket: 'Core',
      status: 'active',
      quantity: 100,
      avg_cost: 42.5,
      cost_currency: 'AUD',
      opened_at: '2026-01-01',
      updated_at: '2026-04-22T00:00:00Z',
      note: 'starter',
    },
    {
      holding_id: 'h-2',
      ticker: 'WES',
      account_label: 'SMSF',
      thesis_bucket: null,
      status: 'archived',
      quantity: 20,
      avg_cost: 71.2,
      cost_currency: 'AUD',
      opened_at: '2025-11-10',
      updated_at: '2026-04-21T00:00:00Z',
      note: null,
    },
  ]

  const preferences = {
    api_default_enabled: false,
    marketplace_prefer_cloud_routing: true,
  }

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
      if (method === 'PATCH') {
        const patch = (request.postDataJSON() as Record<string, unknown>) ?? {}
        if (typeof patch.api_default_enabled === 'boolean') {
          preferences.api_default_enabled = patch.api_default_enabled
        }
        if (typeof patch.marketplace_prefer_cloud_routing === 'boolean') {
          preferences.marketplace_prefer_cloud_routing = patch.marketplace_prefer_cloud_routing
        }
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(preferences),
      })
      return
    }

    if (pathname.endsWith('/api/cockpit/holdings')) {
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: holdings }),
        })
        return
      }

      if (method === 'POST') {
        const payload = (request.postDataJSON() as Partial<HoldingRow>) ?? {}
        const created: HoldingRow = {
          holding_id: `h-${nextId++}`,
          ticker: String(payload.ticker ?? '').toUpperCase(),
          account_label: payload.account_label ?? null,
          thesis_bucket: payload.thesis_bucket ?? null,
          status: payload.status ?? null,
          quantity: typeof payload.quantity === 'number' ? payload.quantity : null,
          avg_cost: typeof payload.avg_cost === 'number' ? payload.avg_cost : null,
          cost_currency: payload.cost_currency ?? null,
          opened_at: payload.opened_at ?? null,
          updated_at: '2026-04-22T03:00:00Z',
          note: payload.note ?? null,
        }
        holdings = [created, ...holdings]
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(created),
        })
        return
      }
    }

    const holdingMatch = pathname.match(/\/api\/cockpit\/holdings\/([^/]+)$/)
    if (holdingMatch) {
      const holdingId = decodeURIComponent(holdingMatch[1])
      const index = holdings.findIndex((row) => row.holding_id === holdingId)

      if (method === 'PATCH') {
        if (index < 0) {
          await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) })
          return
        }
        const payload = (request.postDataJSON() as Partial<HoldingRow>) ?? {}
        const updated: HoldingRow = {
          ...holdings[index],
          ...payload,
          ticker: String(payload.ticker ?? holdings[index].ticker).toUpperCase(),
          updated_at: '2026-04-22T04:00:00Z',
        }
        holdings[index] = updated
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updated),
        })
        return
      }

      if (method === 'DELETE') {
        if (index < 0) {
          await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) })
          return
        }
        holdings = holdings.filter((row) => row.holding_id !== holdingId)
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, holding_id: holdingId }),
        })
        return
      }
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    })
  })
}

test.describe('Holdings Screen', () => {
  test.beforeEach(async ({ page }) => {
    await mockCockpitApis(page)
  })

  test('navigates from sidebar and renders holdings summary', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link').filter({ hasText: 'Holdings' }).click()
    await expect(page).toHaveURL(/\/holdings/)

    await expect(page.locator('h1.text-lg.font-semibold')).toHaveText('Portfolio Holdings')
    await expect(page.getByText('Positions')).toBeVisible()
    await expect(page.getByText('BHP')).toBeVisible()
    await expect(page.getByText('WES')).toBeVisible()
  })

  test('creates, edits, and removes a holding', async ({ page }) => {
    await page.goto('/holdings')

    await page.locator('input[placeholder=\"Ticker (e.g. BHP)\"]').fill('CBA')
    await page.locator('input[placeholder=\"Quantity\"]').fill('12')
    await page.locator('input[placeholder=\"Avg cost\"]').fill('120.5')
    await page.locator('input[placeholder=\"Account\"]').fill('Main')
    await page.locator('input[placeholder=\"Status\"]').fill('active')
    await page.getByRole('button', { name: 'Add' }).click()

    await expect(page.getByText('CBA')).toBeVisible()

    const cbaRow = page.locator('tr', { hasText: 'CBA' })
    await cbaRow.getByRole('button', { name: 'Edit' }).click()

    const archivedInput = page.locator('input[value=\"active\"]').first()
    await archivedInput.fill('archived')

    await page.locator('input[value=\"Main\"]').first().fill('Main-Updated')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('archived')).toBeVisible()
    await expect(page.getByText('Main-Updated')).toBeVisible()

    await page.locator('tr', { hasText: 'CBA' }).getByRole('button', { name: 'Remove' }).click()
    await expect(page.getByRole('cell', { name: 'CBA' })).toHaveCount(0)
  })
})
