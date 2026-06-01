import fs from 'node:fs'
import path from 'node:path'

import { expect, test, type Page, type Route } from '@playwright/test'

type ParityStatus =
  | 'PASS'
  | 'FAIL'
  | 'PARTIAL'
  | 'UNVERIFIED'
  | 'NOT_CONNECTED'
  | 'BLOCKED'

type ParityRow = {
  route: string
  area: string
  expected: string
  observed: string
  status: ParityStatus
  notes: string
}

type MockCounters = {
  actionJobPostCount: number
  feedbackFlagPostCount: number
}

const verificationTarget =
  process.env.COCKPIT_E2E_BASE_URL
  || process.env.PLAYWRIGHT_BASE_URL
  || 'http://localhost:3000'

const reportRows: ParityRow[] = []

function addReportRow(row: ParityRow): void {
  reportRows.push(row)
}

function sanitizeCell(value: string): string {
  return value.replace(/\|/g, '\\|').replace(/\s+/g, ' ').trim()
}

function resolveReportPath(): string {
  const requested = process.env.COCKPIT_ROUTE_PARITY_REPORT_PATH
  if (requested) {
    return path.isAbsolute(requested)
      ? requested
      : path.resolve(process.cwd(), '..', requested)
  }

  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')
  return path.resolve(
    process.cwd(),
    '..',
    'reports',
    'cockpit',
    `browser_regression_route_parity_${stamp}.md`,
  )
}

function writeParityReport(): void {
  const reportPath = resolveReportPath()
  fs.mkdirSync(path.dirname(reportPath), { recursive: true })

  const tableRows = reportRows.map((row) => (
    `| ${sanitizeCell(row.route)} | ${sanitizeCell(row.area)} | ${sanitizeCell(row.expected)} | ${sanitizeCell(row.observed)} | ${row.status} | ${sanitizeCell(row.notes)} |`
  ))
  const markdown = [
    '# Cockpit Browser Regression Route Parity',
    '',
    `Generated: ${new Date().toISOString()}`,
    `Verification target: ${verificationTarget}`,
    '',
    '| Page/Route | Control/Area | Expected | Observed | Status | Notes |',
    '| --- | --- | --- | --- | --- | --- |',
    ...tableRows,
    '',
  ].join('\n')

  fs.writeFileSync(reportPath, markdown)
  console.log(`Route/control parity report: ${reportPath}`)
}

function json(body: unknown, status = 200): { status: number; contentType: string; body: string } {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

async function fulfillJson(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill(json(body, status))
}

function sseEvent(type: string, data: Record<string, unknown>): string {
  return `data: ${JSON.stringify({ type, data })}\n\n`
}

function sseStream(events: Array<[string, Record<string, unknown>]>): string {
  return `${events.map(([type, data]) => sseEvent(type, data)).join('')}event: end\ndata: {}\n\n`
}

function analystSources(): Array<Record<string, unknown>> {
  return [
    {
      title: 'BHP FY25 annual report',
      url: 'https://example.test/bhp-fy25',
      score: 0.94,
      snippet: 'Revenue and net debt evidence from the annual report.',
      published_at: '2025-08-19T00:00:00Z',
      document_id: 'doc-bhp-fy25',
      source_id: 'src-bhp-fy25',
      doc_type: 'annual_report',
      kind: 'document',
    },
    {
      title: 'BHP market update',
      url: 'https://example.test/bhp-news',
      score: 0.82,
      snippet: 'Market context source used for the synthesis.',
      published_at: '2026-04-20T00:00:00Z',
      source_id: 'src-bhp-news',
      kind: 'news',
    },
  ]
}

function chatStreamFor(message: string): string {
  const lower = message.toLowerCase()

  if (lower.includes('analyst shell')) {
    return sseStream([
      ['sources', { items: analystSources() }],
      ['done', {
        text: [
          'BHP answer with evidence summary.',
          '',
          'Key facts:',
          '- Revenue is source-backed in the FY25 filing.',
          '- Net debt is source-backed in the FY25 filing.',
        ].join('\n'),
        model: 'model:browser-regression',
        latency_ms: 42,
        source: 'local',
        cost_usd: 0,
        routing_metadata: {
          primary_ticker: 'BHP',
          intent: 'financial_interpretation',
          response_classification: 'evidence_bound_answer',
          source_plan: ['financial_truth', 'news'],
          missing_categories_after_recovery: ['market_context'],
          sufficient_for_analysis: false,
          data_freshness: '2026-04-20',
        },
      }],
    ])
  }

  if (lower.includes('action proposal')) {
    return sseStream([
      ['action_preview', {
        id: 'run_company_analysis',
        name: 'Run company analysis',
        description: 'The answer needs a fuller company analysis.',
        args: { ticker: 'BHP' },
        requires_confirmation: true,
        timeout_seconds: 120,
        is_mutating: false,
        impact: 'Queue a read-only analysis job after confirmation.',
      }],
      ['done', {
        text: 'Action ready: Run company analysis.',
        model: 'model:browser-regression',
        latency_ms: 35,
        source: 'local',
        cost_usd: 0,
        routing_metadata: {
          primary_ticker: 'BHP',
          intent: 'action_confirmation',
        },
      }],
    ])
  }

  if (lower.includes('thesis note')) {
    return sseStream([
      ['action_preview', {
        id: 'create_thesis',
        name: 'Save thesis note',
        description: 'Save this thesis note after confirmation.',
        args: { ticker: 'BHP', thesis: 'BHP copper growth note' },
        requires_confirmation: true,
        timeout_seconds: 10,
        is_mutating: true,
      }],
      ['done', {
        text: 'Thesis note proposal ready.',
        model: 'model:browser-regression',
        latency_ms: 31,
        source: 'local',
        cost_usd: 0,
        routing_metadata: {
          primary_ticker: 'BHP',
          intent: 'memory_write_proposal',
        },
      }],
    ])
  }

  if (lower.includes('diagnostic flag')) {
    return sseStream([
      ['done', {
        text: 'Potential issue detected.',
        model: 'model:browser-regression',
        latency_ms: 28,
        source: 'local',
        cost_usd: 0,
        routing_metadata: {},
        auto_flag: {
          report_id: 'auto_browser_regression',
          feedback_type: 'poor',
          capture_kind: 'auto_diagnostic',
          report_dir: 'reports/cockpit/flagged_sessions/auto_browser_regression',
          read_api_path: '/api/cockpit/feedback/flags/auto_browser_regression',
          codex_prompt_path: 'reports/cockpit/flagged_sessions/auto_browser_regression/codex_prompt.md',
          codex_prompt: 'CODEX PROMPT raw repair text should stay hidden.',
          codex_cli_command: 'codex exec --dangerously-run-raw-prompt',
          investigation_status: 'queued',
        },
      }],
    ])
  }

  if (lower.includes('unsupported financial claim')) {
    return sseStream([
      ['done', {
        text: 'I cannot verify that financial claim from visible evidence.',
        model: 'model:browser-regression',
        latency_ms: 25,
        source: 'local',
        cost_usd: 0,
        routing_metadata: {
          primary_ticker: 'BHP',
          intent: 'financial_claim_guard',
          grounding_guard: 'unsupported_financial_claim',
          response_classification: 'refusal_missing_visible_sources',
          sufficient_for_analysis: false,
        },
      }],
    ])
  }

  return sseStream([
    ['done', {
      text: 'Sure, I can help narrow that down.',
      model: 'model:browser-regression',
      latency_ms: 18,
      source: 'local',
      cost_usd: 0,
      routing_metadata: {},
    }],
  ])
}

async function mockCockpitApis(page: Page, counters: MockCounters): Promise<void> {
  const preferences = {
    api_default_enabled: false,
    marketplace_prefer_cloud_routing: false,
    chat_routing_policy_override: 'config_default',
  }

  await page.route('**/api/cockpit/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const url = new URL(request.url())
    const { pathname } = url

    if (pathname === '/api/cockpit/chat' && method === 'POST') {
      const payload = request.postDataJSON() as { message?: string } | null
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        headers: {
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
        body: chatStreamFor(String(payload?.message || '')),
      })
      return
    }

    if (pathname === '/api/cockpit/feedback/flag' && method === 'POST') {
      counters.feedbackFlagPostCount += 1
      await fulfillJson(route, {
        report_id: 'flag_browser_regression',
        feedback_type: 'poor',
        capture_kind: 'chat_feedback',
        report_dir: 'reports/cockpit/flagged_sessions/flag_browser_regression',
        read_api_path: '/api/cockpit/feedback/flags/flag_browser_regression',
        codex_prompt_path: 'reports/cockpit/flagged_sessions/flag_browser_regression/codex_prompt.md',
        codex_prompt: 'CODEX PROMPT raw repair text should stay hidden.',
        codex_cli_command: 'codex exec --dangerously-run-raw-prompt',
        investigation_status: 'queued',
        analysis_summary: 'mock flag stored',
      })
      return
    }

    if (pathname === '/api/cockpit/action/jobs' && method === 'POST') {
      counters.actionJobPostCount += 1
      await fulfillJson(route, {
        action_id: 'run_company_analysis',
        job_id: 'job-browser-regression',
        status: 'queued',
        queued: true,
      })
      return
    }

    if (pathname.startsWith('/api/cockpit/action/jobs/')) {
      await fulfillJson(route, {
        job_id: 'job-browser-regression',
        action_id: 'run_company_analysis',
        status: 'completed',
        result: 'mock action complete',
      })
      return
    }

    if (pathname === '/api/cockpit/health') {
      await fulfillJson(route, {
        status: 'healthy',
        services: [
          { name: 'backend', status: 'healthy' },
          { name: 'gpu', status: 'healthy', details: { utilization_pct: 0, memory_used_mb: 0 } },
          { name: 'host', status: 'healthy', details: { load_avg_1m: 0.2 } },
        ],
      })
      return
    }

    if (pathname === '/api/cockpit/preferences') {
      if (method === 'PATCH') {
        const patch = request.postDataJSON() as Record<string, unknown>
        Object.assign(preferences, patch)
      }
      await fulfillJson(route, preferences)
      return
    }

    if (pathname === '/api/cockpit/config') {
      await fulfillJson(route, {
        llm_model: 'model:browser-regression',
        active_model: 'model:browser-regression',
        routing_policy: 'local_preferred',
        max_tokens: 2048,
        temperature: 0.2,
      })
      return
    }

    if (pathname === '/api/cockpit/models') {
      await fulfillJson(route, { models: [] })
      return
    }

    if (pathname === '/api/cockpit/chat/sessions') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as { session_id?: string } | null
        await fulfillJson(route, { ok: true, session_id: payload?.session_id || 'chat-test', created: true })
        return
      }
      await fulfillJson(route, { items: [] })
      return
    }

    if (pathname.startsWith('/api/cockpit/chat/sessions/')) {
      if (method === 'DELETE') {
        await fulfillJson(route, { ok: true, deleted_count: 1 })
        return
      }
      await fulfillJson(route, { session_id: 'chat-test', message_count: 0, items: [] })
      return
    }

    if (pathname === '/api/cockpit/commentary/recent') {
      await fulfillJson(route, {
        items: [
          {
            source_id: 'recent-source-1',
            source_name: 'Browser regression source',
            source_type: 'youtube',
            approved_at: '2026-05-04T00:00:00Z',
          },
        ],
      })
      return
    }

    if (pathname === '/api/cockpit/claims/verify') {
      await fulfillJson(route, {
        ok: true,
        status: 'DATA_MISSING',
        confidence_label: 'Speculative',
        rationale: 'Mocked browser regression verifier.',
      })
      return
    }

    if (pathname === '/api/cockpit/holdings') {
      await fulfillJson(route, { items: [] })
      return
    }

    if (pathname === '/api/cockpit/watchlist') {
      await fulfillJson(route, { items: [] })
      return
    }

    if (pathname === '/api/cockpit/memory/index' || pathname === '/api/cockpit/memory') {
      await fulfillJson(route, {
        ticker: null,
        summary: {
          company_memory_entry_count: 0,
          company_memory_change_count: 0,
          market_memory_item_count: 0,
          user_thesis_entry_count: 0,
          user_thesis_proposal_count: 0,
          company_memory_ticker_count: 0,
          user_thesis_ticker_count: 0,
        },
        company_memory: { entries: [], change_log: [] },
        market_memory: { sector_items: [], macro_items: [] },
        user_thesis_memory: { entries: [], proposals: [] },
        errors: [],
      })
      return
    }

    if (pathname === '/api/cockpit/memory/company-dump') {
      await fulfillJson(route, {
        ticker: url.searchParams.get('ticker') || null,
        documents: [],
        financials: [],
        announcements: [],
        risk_notes: [],
        errors: [],
      })
      return
    }

    if (pathname.startsWith('/api/cockpit/memory/')) {
      await fulfillJson(route, { ok: true, proposal: { proposal_id: 'proposal-browser-regression' } })
      return
    }

    if (pathname === '/api/cockpit/marketplace/browser-health') {
      await fulfillJson(route, {
        status: 'ready',
        browser_family: 'chrome',
        challenge_detected: false,
        last_checked_at: '2026-05-04T00:00:00Z',
      })
      return
    }

    if (pathname.startsWith('/api/cockpit/marketplace/')) {
      await fulfillJson(route, { items: [], total: 0 })
      return
    }

    if (pathname === '/api/cockpit/thesis-audit/coverage') {
      await fulfillJson(route, {
        ticker: url.searchParams.get('ticker') || 'BHP',
        generated_at: '2026-05-04T00:00:00Z',
        evidence_summary: {
          evidence_span_count: 0,
          memory_read_only: true,
          sufficient_for_analysis: false,
          missing_categories_after_recovery: ['financial_truth'],
          coverage_status: 'DATA_MISSING',
          coverage_message: 'No mocked thesis evidence loaded.',
        },
        guardrails: {},
      })
      return
    }

    if (pathname.startsWith('/api/cockpit/metrics/')) {
      await fulfillJson(route, { status: 'healthy', items: [] })
      return
    }

    await fulfillJson(route, { items: [], ok: true })
  })

  await page.route('**/api/ops/jobs**', async (route) => {
    await fulfillJson(route, { items: [] })
  })

  await page.route('**/api/context/**', async (route) => {
    await fulfillJson(route, { items: [], documents: [], financials: [], announcements: [], errors: [] })
  })

  await page.route('**/api/extraction-review/**', async (route) => {
    await fulfillJson(route, { items: [], sessions: [], runs: [], errors: [], summary: { total: 0 } })
  })

  await page.route('**/api/extraction-eval/**', async (route) => {
    await fulfillJson(route, {
      summary: {
        total_documents: 0,
        total_accuracy: 0,
        metric_status_counts: {},
        trust_distribution: {},
      },
      documents: [],
    })
  })

  await page.route('**/api/process/**', async (route) => {
    await fulfillJson(route, { ok: true })
  })

  await page.route('**/api/health', async (route) => {
    await fulfillJson(route, { status: 'healthy' })
  })

  await page.route('**/rag/query', async (route) => {
    await fulfillJson(route, {
      answer: 'No mocked news query has been submitted.',
      sources: [],
      metadata: { mocked: true },
    })
  })
}

async function sendChat(page: Page, prompt: string, expectedText: string | RegExp): Promise<void> {
  const input = page.getByPlaceholder('Enter command or query...')
  await expect(input).toBeVisible()
  await input.fill(prompt)
  await input.press('Enter')
  await expect(page.getByText(expectedText).first()).toBeVisible({ timeout: 15_000 })
}

test.describe.configure({ mode: 'serial' })

test.afterAll(() => {
  writeParityReport()
})

test.describe('Cockpit browser chat regression and route parity', () => {
  test('server and chat shell are reachable on the configured verification target', async ({ page }) => {
    const counters = { actionJobPostCount: 0, feedbackFlagPostCount: 0 }
    await mockCockpitApis(page, counters)

    const response = await page.goto('/')
    await expect(page).toHaveTitle(/Financial Cockpit/)
    await expect(page.getByPlaceholder('Enter command or query...')).toBeVisible()
    const status = response?.status() ?? 0
    expect(status).toBe(200)

    addReportRow({
      route: '/',
      area: 'Server and chat shell',
      expected: ':8081 or configured base URL returns 200 and renders chat input',
      observed: `HTTP ${status}; title "${await page.title()}"; chat input visible`,
      status: 'PASS',
      notes: verificationTarget,
    })
  })

  test('normal follow-up is independent while action proposal is pending (#120)', async ({ page }) => {
    const counters = { actionJobPostCount: 0, feedbackFlagPostCount: 0 }
    await mockCockpitApis(page, counters)
    await page.goto('/full-chat')
    await expect(page.getByPlaceholder('Enter command or query...')).toBeVisible()

    await sendChat(page, 'action proposal response', 'Action ready: Run company analysis.')
    await expect(page.getByText('Action proposal').first()).toBeVisible()
    await expect(page.getByText('Run company analysis').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Confirm' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Cancel' }).first()).toBeVisible()
    expect(counters.actionJobPostCount).toBe(0)

    await sendChat(page, 'Pick one current holding or watchlist item for review.', 'Sure, I can help narrow that down.')
    await expect(page.getByText('Sure, I can help narrow that down.').last()).toBeVisible()
    expect(counters.actionJobPostCount).toBe(0)

    await page.getByRole('button', { name: 'Cancel' }).first().click()
    await expect(page.getByText('Action cancelled: Run company analysis').first()).toBeVisible()
    expect(counters.actionJobPostCount).toBe(0)
    addReportRow({
      route: '/full-chat',
      area: 'Pending action follow-up',
      expected: 'A normal prompt submitted while Confirm/Cancel is visible completes as an independent chat turn without running the action',
      observed: `Independent plain answer rendered after action proposal; backend action POST count remained ${counters.actionJobPostCount}`,
      status: 'PASS',
      notes: 'Regression coverage for issue #120; confirmation gate stayed intact',
    })
  })

  test('mocked chat states preserve analyst shell, action, diagnostic, source, feedback, and guard behavior', async ({ page }) => {
    const counters = { actionJobPostCount: 0, feedbackFlagPostCount: 0 }
    await mockCockpitApis(page, counters)
    await page.goto('/')
    await expect(page.getByPlaceholder('Enter command or query...')).toBeVisible()

    await sendChat(page, 'plain conversational response', 'Sure, I can help narrow that down.')
    await expect(page.getByText(/Sources:/)).toHaveCount(0)
    await expect(page.getByText(/Trust:/)).toHaveCount(0)
    await expect(page.getByText(/^Error:/)).toHaveCount(0)
    await expect(page.getByText(/CODEX PROMPT|codex exec/i)).toHaveCount(0)
    addReportRow({
      route: '/',
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
    addReportRow({
      route: '/',
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
    addReportRow({
      route: '/',
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
    addReportRow({
      route: '/',
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
    addReportRow({
      route: '/',
      area: 'Thesis-note proposal',
      expected: 'NOTE is not treated as ticker; referenced entity and memory/write confirmation are visible',
      observed: 'Entity BHP rendered, Entity NOTE absent, Memory write and confirmation labels visible',
      status: 'PASS',
      notes: 'create_thesis action preview mocked',
    })

    await sendChat(page, 'unsupported financial claim guard response', 'I cannot verify that financial claim from visible evidence.')
    await expect(page.getByText('Unsupported claim blocked').first()).toBeVisible()
    await expect(page.getByText('Data missing').first()).toBeVisible()
    addReportRow({
      route: '/',
      area: 'Unsupported financial claim guard',
      expected: 'Unsupported claim guard remains represented in UI when routing metadata requires it',
      observed: 'Unsupported claim blocked trust label and Data missing answer type rendered',
      status: 'PASS',
      notes: 'No financial truth, extraction, or prompt behavior changed',
    })

    await sendChat(page, 'diagnostic flag response', 'Potential issue detected.')
    await expect(page.getByText('report: auto_browser_regression').first()).toBeVisible()
    await expect(page.getByText('View diagnostic').first()).toBeVisible()
    await expect(page.getByText('Draft repair prompt').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Deploy Codex' }).first()).toBeVisible()
    await expect(page.getByText(/CODEX PROMPT|codex exec/i)).toHaveCount(0)
    addReportRow({
      route: '/',
      area: 'Diagnostic/flag card hygiene',
      expected: 'Compact diagnostic card visible; raw Codex CLI and repair prompt hidden by default',
      observed: 'Diagnostic controls rendered while raw CODEX PROMPT and codex exec strings remained hidden',
      status: 'PASS',
      notes: 'Auto-flag payload mocked in SSE done event',
    })

    await page.getByRole('button', { name: '[flag response]' }).last().click()
    await expect(page.getByRole('dialog', { name: 'Flag response' })).toBeVisible()
    await page.getByPlaceholder(/Optional note/).fill('browser regression flag flow')
    await page.getByRole('button', { name: 'Save flag' }).click()
    await expect(page.getByText('report: flag_browser_regression').first()).toBeVisible()
    expect(counters.feedbackFlagPostCount).toBe(1)
    await expect(page.getByText(/CODEX PROMPT|codex exec/i)).toHaveCount(0)
    addReportRow({
      route: '/',
      area: 'Feedback flag flow',
      expected: 'Flag dialog opens and safe mocked flag result renders without raw prompt dump',
      observed: `Flag saved through mocked route; feedback POST count ${counters.feedbackFlagPostCount}; raw prompt/CLI hidden`,
      status: 'PASS',
      notes: 'No destructive backend action required',
    })
  })

  test('visible primary routes load without browser 404 or 500 pages', async ({ page }) => {
    const counters = { actionJobPostCount: 0, feedbackFlagPostCount: 0 }
    await mockCockpitApis(page, counters)

    const routes = [
      { route: '/', area: 'Chat' },
      { route: '/operations', area: 'Operations' },
      { route: '/verification', area: 'Verification' },
      { route: '/news', area: 'News' },
      { route: '/memory', area: 'Memory' },
      { route: '/watchlist', area: 'Watchlist' },
      { route: '/holdings', area: 'Holdings' },
      { route: '/marketplace', area: 'Marketplace' },
      { route: '/marketplace/matches', area: 'Marketplace matches' },
      { route: '/marketplace/alerts', area: 'Marketplace alerts' },
      { route: '/thesis-audit', area: 'Thesis audit' },
      { route: '/settings', area: 'Settings' },
      { route: '/history', area: 'History' },
      { route: '/intel-ops', area: 'Intel Pulse' },
      { route: '/updater', area: 'Updater' },
    ]

    const brokenRoutes: string[] = []
    for (const item of routes) {
      const response = await page.goto(item.route, { waitUntil: 'domcontentloaded' })
      await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => undefined)
      const statusCode = response?.status() ?? 0
      const bodyText = await page.locator('body').innerText({ timeout: 10_000 }).catch(() => '')
      const notFound = statusCode === 404 || /404|This page could not be found/i.test(bodyText)
      const serverError = statusCode >= 500 || /500|Internal Server Error|Application error/i.test(bodyText)
      const notConnected = /not connected|not configured|Cockpit Offline|NO_DATA_AVAILABLE|disabled/i.test(bodyText)
      const status: ParityStatus = notFound || serverError
        ? 'FAIL'
        : notConnected
          ? 'NOT_CONNECTED'
          : 'PASS'

      if (status === 'FAIL') {
        brokenRoutes.push(`${item.route} HTTP ${statusCode}`)
      }

      addReportRow({
        route: item.route,
        area: item.area,
        expected: 'Route loads in browser without Next.js 404 or 500 page',
        observed: `HTTP ${statusCode}${notConnected ? '; visible not-connected/disabled state detected' : ''}`,
        status,
        notes: notFound || serverError
          ? bodyText.slice(0, 180)
          : 'Primary route smoke with mocked non-destructive API responses',
      })
    }

    expect(brokenRoutes, brokenRoutes.join(', ')).toEqual([])
  })
})
