import { expect, test, type Page } from '@playwright/test'

import {
  CHAT_ENTRY_ROUTE,
  CHAT_INPUT_PLACEHOLDER,
  VISIBLE_PRIMARY_ROUTES,
  createMockCounters,
  createRouteParityReporter,
  inspectVisibleRoute,
  mockCockpitApis,
  resolveVerificationTarget,
  sendChat,
} from './chat-browser-harness'

const verificationTarget = resolveVerificationTarget()
const parityReporter = createRouteParityReporter(verificationTarget)

async function expectNormalDiagnosticHandoffHidden(page: Page, reportId: string): Promise<void> {
  await expect(page.getByText('Potential issue captured for operator review.').last()).toBeVisible()
  await expect(page.getByText('Evidence state: DATA_MISSING').last()).toBeVisible()
  await expect(page.getByText(`report: ${reportId}`)).toHaveCount(0)
  await expect(page.getByText(reportId)).toHaveCount(0)
  await expect(page.getByText('View diagnostic', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Draft repair prompt', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Investigation packet', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Deploy Codex' })).toHaveCount(0)
  await expect(page.getByText(/CODEX PROMPT|codex exec/i)).toHaveCount(0)
}

test.describe.configure({ mode: 'serial' })

test.afterAll(() => {
  parityReporter.write()
})

test.describe('Cockpit browser chat regression and route parity', () => {
  test('server and chat shell are reachable on the configured verification target', async ({ page }) => {
    const counters = createMockCounters()
    await mockCockpitApis(page, counters)

    const response = await page.goto(CHAT_ENTRY_ROUTE)
    await expect(page).toHaveTitle(/Financial Cockpit/)
    await expect(page.getByPlaceholder(CHAT_INPUT_PLACEHOLDER)).toBeVisible()
    const status = response?.status() ?? 0
    expect(status).toBe(200)

    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Server and chat shell',
      expected: 'Configured base URL returns 200 for /full-chat and renders chat input',
      observed: `HTTP ${status}; title "${await page.title()}"; chat input visible`,
      status: 'PASS',
      notes: verificationTarget,
    })
  })

  test('mocked chat states preserve analyst shell, action, diagnostic, source, feedback, and guard behavior', async ({ page }) => {
    const counters = createMockCounters()
    await mockCockpitApis(page, counters)
    await page.goto(CHAT_ENTRY_ROUTE)
    await expect(page.getByPlaceholder(CHAT_INPUT_PLACEHOLDER)).toBeVisible()

    await sendChat(page, 'plain conversational response', 'Sure, I can help narrow that down.')
    await expect(page.getByText(/Sources:/)).toHaveCount(0)
    await expect(page.getByText(/Trust:/)).toHaveCount(0)
    await expect(page.getByText(/^Error:/)).toHaveCount(0)
    await expect(page.getByText(/CODEX PROMPT|codex exec/i)).toHaveCount(0)
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Plain conversational message',
      expected: 'Lightweight answer with no analyst shell, no error card, and no raw operator text',
      observed: 'Plain mocked answer rendered without Sources/Trust shell labels or raw diagnostic text',
      status: 'PASS',
      notes: 'SSE mocked; no live model call',
    })

    await sendChat(page, 'analyst shell response for BHP', 'BHP answer with evidence summary.')
    await expect(page.getByText('Entity: BHP').first()).toBeVisible()
    await expect(page.getByText('Partial evidence').first()).toBeVisible()
    await expect(page.getByText('Sources: 2').first()).toBeVisible()
    await expect(page.getByText('Evidence: filings + news').first()).toBeVisible()
    await expect(page.getByText('Key facts').first()).toBeVisible()
    await expect(page.getByText('Missing data / gaps').first()).toBeVisible()
    await expect(page.getByText('market_context').first()).toBeVisible()
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Analyst shell message',
      expected: 'Ticker, answer type, source count, evidence summary, key facts, and gap banner render',
      observed: 'BHP partial-evidence shell rendered with source count 2, filings + news evidence, key facts, and market_context gap',
      status: 'PASS',
      notes: 'Metadata and source list supplied through mocked SSE',
    })

    const sourceToggle = page.getByRole('button', { name: '[2 sources]' }).first()
    await expect(page.getByText('BHP FY25 annual report').first()).toBeVisible()
    await sourceToggle.click()
    await expect(page.getByText('BHP FY25 annual report')).toHaveCount(0)
    await page.getByRole('button', { name: 'Review evidence' }).first().click()
    await expect(page.getByText('BHP FY25 annual report').first()).toBeVisible()
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Source list',
      expected: 'Source list can close and reopen; rendered count matches metadata',
      observed: 'Inline [2 sources] list closed, Review evidence reopened it, and two-source metadata remained visible',
      status: 'PASS',
      notes: 'Drawer-equivalent inline source list exercised',
    })

    await sendChat(page, 'action proposal response', 'Action ready: Run company analysis.')
    await expect(page.getByText('Action proposal').first()).toBeVisible()
    await expect(page.getByText('Run company analysis').first()).toBeVisible()
    await expect(page.getByText('Confirmation required').first()).toBeVisible()
    await expect(page.getByText('Long job').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Confirm' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Cancel' }).first()).toBeVisible()
    expect(counters.actionJobPostCount).toBe(0)
    await page.getByRole('button', { name: 'Cancel' }).first().click()
    await expect(page.getByText('Action cancelled: Run company analysis').first()).toBeVisible()
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Action proposal card',
      expected: 'Confirmation state and confirm/cancel controls render without auto-execution',
      observed: `Action card rendered; backend action POST count stayed ${counters.actionJobPostCount} until cancelled`,
      status: 'PASS',
      notes: 'Mutating backend action route mocked and counted',
    })

    await sendChat(page, 'thesis note proposal response', 'Thesis note proposal ready.')
    await expect(page.getByText('Entity: BHP').last()).toBeVisible()
    await expect(page.getByText('Memory write').first()).toBeVisible()
    await expect(page.getByText('Save thesis note').first()).toBeVisible()
    await expect(page.getByText('Entity: NOTE')).toHaveCount(0)
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Thesis-note proposal',
      expected: 'NOTE is not treated as ticker; referenced entity and memory/write confirmation are visible',
      observed: 'Entity BHP rendered, Entity NOTE absent, Memory write and confirmation labels visible',
      status: 'PASS',
      notes: 'create_thesis action preview mocked',
    })

    await sendChat(page, 'unsupported financial claim guard response', 'I cannot verify that financial claim from visible evidence.')
    await expect(page.getByText('Unsupported / not verified').first()).toBeVisible()
    await expect(page.getByText('Data missing').first()).toBeVisible()
    await expect(page.getByText('Evidence incomplete').first()).toBeVisible()
    await expect(page.getByText('Claim-supported')).toHaveCount(0)
    await expect(page.getByText('Financial truth evidence')).toHaveCount(0)
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Unsupported financial claim guard',
      expected: 'Unsupported claim guard remains represented without claim-verified or financial-truth promotion',
      observed: 'Unsupported / not verified, Data missing, and Evidence incomplete labels rendered; claim-supported and financial-truth labels absent',
      status: 'PASS',
      notes: 'No financial truth, extraction, or prompt behavior changed',
    })

    await sendChat(page, 'diagnostic flag response', 'Potential issue detected.')
    await expectNormalDiagnosticHandoffHidden(page, 'auto_browser_regression')
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Diagnostic/flag card hygiene',
      expected: 'Normal users see DATA_MISSING recovery text without operator report paths, diagnostic links, repair prompts, or Deploy Codex controls',
      observed: 'Normal diagnostic handoff rendered DATA_MISSING recovery text; report id, diagnostic link, repair prompt, investigation packet, Deploy Codex, raw prompt, and CLI text were absent',
      status: 'PASS',
      notes: 'Auto-flag payload mocked in SSE done event',
    })

    await page.getByRole('button', { name: '[flag response]' }).last().click()
    await expect(page.getByRole('dialog', { name: 'Flag response' })).toBeVisible()
    await page.getByPlaceholder(/Optional note/).fill('browser regression flag flow')
    await page.getByRole('button', { name: 'Save flag' }).click()
    await expectNormalDiagnosticHandoffHidden(page, 'flag_browser_regression')
    expect(counters.feedbackFlagPostCount).toBe(1)
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Feedback flag flow',
      expected: 'Flag dialog opens and mocked normal-user flag result renders DATA_MISSING recovery without operator controls or raw prompt dump',
      observed: `Flag saved through mocked route; feedback POST count ${counters.feedbackFlagPostCount}; operator report id, links, Deploy Codex, raw prompt, and CLI text hidden`,
      status: 'PASS',
      notes: 'No destructive backend action required',
    })
  })

  test('/full-chat hides operator diagnostics for normal users', async ({ page }) => {
    const counters = createMockCounters()
    await mockCockpitApis(page, counters)
    await page.goto(CHAT_ENTRY_ROUTE)
    await expect(page.getByPlaceholder(CHAT_INPUT_PLACEHOLDER)).toBeVisible()

    await sendChat(page, 'diagnostic flag response', 'Potential issue detected.')
    await expectNormalDiagnosticHandoffHidden(page, 'auto_browser_regression')
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Diagnostic/flag card hygiene',
      expected: 'Normal users see DATA_MISSING recovery text without operator report paths, diagnostic links, repair prompts, or Deploy Codex controls',
      observed: 'Mocked auto_flag rendered normal recovery text; report id, diagnostic link, repair prompt, investigation packet, Deploy Codex, raw prompt, and CLI text were absent',
      status: 'PASS',
      notes: 'Auto-flag payload mocked in SSE done event',
    })

    await page.getByRole('button', { name: '[flag response]' }).last().click()
    await expect(page.getByRole('dialog', { name: 'Flag response' })).toBeVisible()
    await page.getByPlaceholder(/Optional note/).fill('browser regression flag flow')
    await page.getByRole('button', { name: 'Save flag' }).click()
    await expectNormalDiagnosticHandoffHidden(page, 'flag_browser_regression')
    expect(counters.feedbackFlagPostCount).toBe(1)
    await expect(page.getByText(/CODEX PROMPT|codex exec/i)).toHaveCount(0)
    parityReporter.add({
      route: CHAT_ENTRY_ROUTE,
      area: 'Feedback flag flow',
      expected: 'Manual flag flow saves feedback without exposing operator report ids, paths, diagnostic links, repair prompts, or Deploy Codex controls',
      observed: `Flag saved through mocked route; feedback POST count ${counters.feedbackFlagPostCount}; normal recovery text visible and operator controls hidden`,
      status: 'PASS',
      notes: 'No destructive backend action required',
    })
  })

  test('visible primary routes load without browser 404 or 500 pages', async ({ page }) => {
    const counters = createMockCounters()
    await mockCockpitApis(page, counters)

    const brokenRoutes: string[] = []
    for (const item of VISIBLE_PRIMARY_ROUTES) {
      const result = await inspectVisibleRoute(page, item.route)
      if (result.status === 'FAIL') {
        brokenRoutes.push(`${item.route} HTTP ${result.statusCode}`)
      }

      parityReporter.add({
        route: item.route,
        area: item.area,
        expected: 'Route loads in browser without Next.js 404 or 500 page',
        observed: `HTTP ${result.statusCode}${result.notConnected ? '; visible not-connected/disabled state detected' : ''}`,
        status: result.status,
        notes: result.status === 'FAIL'
          ? [...result.errors, result.bodyText].filter(Boolean).join(' | ').slice(0, 180)
          : 'Primary route smoke with mocked non-destructive API responses',
      })
    }

    expect(brokenRoutes, brokenRoutes.join(', ')).toEqual([])
  })
})
