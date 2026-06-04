import fs from 'node:fs'
import path from 'node:path'

import type { Page, Route } from '@playwright/test'

export type ParityStatus =
  | 'PASS'
  | 'FAIL'
  | 'PARTIAL'
  | 'UNVERIFIED'
  | 'NOT_CONNECTED'
  | 'BLOCKED'

export type ParityRow = {
  route: string
  area: string
  expected: string
  observed: string
  status: ParityStatus
  notes: string
}

export type MockCounters = {
  actionJobPostCount: number
  feedbackFlagPostCount: number
}

export type RouteSmokeTarget = {
  route: string
  area: string
}

export type RouteSmokeResult = {
  statusCode: number
  status: ParityStatus
  bodyText: string
  notConnected: boolean
  errors: string[]
}

type SseEvent = [string, Record<string, unknown>]

type ChatStreamScenario = {
  matches: RegExp
  events: SseEvent[]
}

export const CHAT_ENTRY_ROUTE = '/full-chat'
export const CHAT_INPUT_PLACEHOLDER = 'Enter command or query...'

export const VISIBLE_PRIMARY_ROUTES: RouteSmokeTarget[] = [
  { route: '/', area: 'Overview' },
  { route: CHAT_ENTRY_ROUTE, area: 'Chat' },
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

export function resolveVerificationTarget(): string {
  return (
    process.env.COCKPIT_E2E_BASE_URL
    || process.env.PLAYWRIGHT_BASE_URL
    || 'http://localhost:3000'
  )
}

export function createMockCounters(): MockCounters {
  return {
    actionJobPostCount: 0,
    feedbackFlagPostCount: 0,
  }
}

export function sanitizeParityCell(value: string): string {
  return value.replace(/\|/g, '\\|').replace(/\s+/g, ' ').trim()
}

export function buildParityReportMarkdown(input: {
  generatedAt: string
  verificationTarget: string
  rows: ParityRow[]
}): string {
  const tableRows = input.rows.map((row) => (
    `| ${sanitizeParityCell(row.route)} | ${sanitizeParityCell(row.area)} | ${sanitizeParityCell(row.expected)} | ${sanitizeParityCell(row.observed)} | ${row.status} | ${sanitizeParityCell(row.notes)} |`
  ))

  return [
    '# Cockpit Browser Regression Route Parity',
    '',
    `Generated: ${input.generatedAt}`,
    `Verification target: ${input.verificationTarget}`,
    '',
    '| Page/Route | Control/Area | Expected | Observed | Status | Notes |',
    '| --- | --- | --- | --- | --- | --- |',
    ...tableRows,
    '',
  ].join('\n')
}

export function resolveParityReportPath(requested = process.env.COCKPIT_ROUTE_PARITY_REPORT_PATH): string {
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

export function createRouteParityReporter(verificationTarget = resolveVerificationTarget()): {
  add: (row: ParityRow) => void
  rows: () => ParityRow[]
  write: () => string
} {
  const rows: ParityRow[] = []
  return {
    add(row: ParityRow): void {
      rows.push(row)
    },
    rows(): ParityRow[] {
      return [...rows]
    },
    write(): string {
      const reportPath = resolveParityReportPath()
      fs.mkdirSync(path.dirname(reportPath), { recursive: true })
      const markdown = buildParityReportMarkdown({
        generatedAt: new Date().toISOString(),
        verificationTarget,
        rows,
      })
      fs.writeFileSync(reportPath, markdown)
      console.log(`Route/control parity report: ${reportPath}`)
      return reportPath
    },
  }
}

export function createSseEvent(type: string, data: Record<string, unknown>): string {
  return `data: ${JSON.stringify({ type, data })}\n\n`
}

export function createSseStream(events: SseEvent[]): string {
  return `${events.map(([type, data]) => createSseEvent(type, data)).join('')}event: end\ndata: {}\n\n`
}

function jsonResponse(body: unknown, status = 200): { status: number; contentType: string; body: string } {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

async function fulfillJson(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill(jsonResponse(body, status))
}

const MOCK_NOW = '2026-06-04T00:00:00.000Z'

function mockMissingSignal(section: string, code: string, message: string): Record<string, unknown> {
  return {
    section,
    code,
    message,
    source_id: null,
    evidence_id: null,
    source_label: 'missing_required_evidence',
  }
}

function mockMissingEvidence(): Record<string, unknown> {
  return {
    source_id: null,
    source_kind: null,
    source_label: 'missing_required_evidence',
    evidence_labels: ['missing_required_evidence'],
    resolvable: false,
    resolver: 'none',
    evidence_id: null,
    document_id: null,
    chunk_id: null,
    url: null,
    title: null,
    published_at: null,
  }
}

function mockHomeResponse(): Record<string, unknown> {
  const marketMissing = mockMissingSignal(
    'market_session',
    'BROWSER_REGRESSION_MARKET_SESSION_MOCK',
    'Browser regression mock does not provide live market-session data.',
  )
  const portfolioMissing = mockMissingSignal(
    'portfolio',
    'BROWSER_REGRESSION_PORTFOLIO_MOCK',
    'Browser regression mock does not provide live portfolio data.',
  )
  const moversMissing = mockMissingSignal(
    'market_movers',
    'BROWSER_REGRESSION_MARKET_MOVERS_MOCK',
    'Browser regression mock does not provide live market movers.',
  )
  const attentionMissing = mockMissingSignal(
    'attention_queue',
    'BROWSER_REGRESSION_ATTENTION_MOCK',
    'Browser regression mock does not provide live attention queue data.',
  )
  const narrativeMissing = mockMissingSignal(
    'session_summary',
    'BROWSER_REGRESSION_NARRATIVE_MOCK',
    'Browser regression mock does not provide live narrative data.',
  )

  return {
    ok: true,
    generated_at: MOCK_NOW,
    source_label_taxonomy_version: 'source_label_semantics_v1',
    data_state: 'DATA_MISSING',
    degraded: true,
    data_missing: [marketMissing, portfolioMissing, moversMissing, attentionMissing, narrativeMissing],
    as_of: MOCK_NOW,
    market_session: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [marketMissing],
      as_of: null,
      session: 'DEGRADED',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
      session_date: '2026-06-04',
      next_event_label: null,
      next_event_at: null,
    },
    portfolio: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [portfolioMissing],
      as_of: null,
      source_label: 'missing_required_evidence',
      total_value: null,
      currency: 'AUD',
      day_change: null,
      day_change_percent: null,
      coverage_percent: 0,
      holdings_count: 0,
      priced_holdings_count: 0,
      day_change_priced_holdings_count: 0,
    },
    market_movers: [
      {
        id: 'browser-regression-market-movers-missing',
        section: 'market_movers',
        title: 'Market movers unavailable in browser regression mock',
        ticker: '',
        observed_at: MOCK_NOW,
        state: {
          data_state: 'DATA_MISSING',
          degraded: true,
          data_missing: [moversMissing],
          as_of: MOCK_NOW,
        },
        evidence: mockMissingEvidence(),
        price: null,
        change: null,
        change_percent: null,
        reason: null,
      },
    ],
    news: [],
    attention_queue_state: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [attentionMissing],
      as_of: MOCK_NOW,
    },
    attention_queue: [],
    data_health: [
      {
        data_state: 'DATA_MISSING',
        degraded: true,
        data_missing: [marketMissing],
        as_of: MOCK_NOW,
        section: 'market_session',
        label: 'Market session',
        value: 'DATA_MISSING',
      },
      {
        data_state: 'DATA_MISSING',
        degraded: true,
        data_missing: [portfolioMissing],
        as_of: MOCK_NOW,
        section: 'portfolio',
        label: 'Portfolio',
        value: 'DATA_MISSING',
      },
    ],
    narrative: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [narrativeMissing],
      as_of: MOCK_NOW,
      session_summary: null,
      theme_candidates: [],
      tomorrow_prep: [],
    },
  }
}

function mockIntelPulseResponse(): Record<string, unknown> {
  return {
    generated_at: MOCK_NOW,
    stats: {
      document_count: 0,
      extraction_count: 0,
      recent_financial_rows_sampled: 0,
      periodic_financial_rows_total: 0,
      extraction_runs_total: 0,
      signal_count: 0,
      memory_count: 0,
      population_index: 0,
      trust_score_avg: 0,
      quarantine_rate: 0,
      extraction_failure_rate_pct: 0,
    },
    pipeline: [],
    failures: [],
  }
}

function strategyLabBoundaryFlags(): Record<string, boolean> {
  return {
    pending_review: true,
    read_only: true,
    real_transport: false,
    live_trading: false,
    paper_trading: false,
    canonical_financial_truth: false,
    store_writes: false,
    production_data_access: false,
  }
}

function mockStrategyLabStatusResponse(): Record<string, unknown> {
  const dataMissing = [
    'Browser regression mock does not prove current Strategy Lab sidecar availability.',
  ]
  return {
    ok: true,
    schema_version: 'cockpit_strategy_lab_status_v1',
    generated_at: MOCK_NOW,
    overall_state: 'pending_review_read_only',
    cockpit_ui_entrypoint: 'home_status_and_artifact_review_cards',
    status_route: '/api/cockpit/strategy-lab/status',
    artifact_review_route: '/api/cockpit/strategy-lab/artifacts',
    headline: 'Browser regression mock: Strategy Lab is offline and read-only.',
    quantdinger_status: {
      review_status: 'PENDING_REVIEW',
      read_only: true,
      real_transport: 'not_integrated',
      current_sidecar_available: false,
      live_trading: false,
      paper_order_placement: false,
      canonical_financial_truth: false,
      store_writes: false,
      last_readonly_sidecar_smoke: 'SMOKE_PASSED',
      last_readonly_sidecar_smoke_review_status: 'PENDING_REVIEW',
      last_readonly_sidecar_smoke_commit: 'DATA_MISSING',
      last_readonly_sidecar_smoke_report_path: 'DATA_MISSING',
      last_readonly_sidecar_smoke_report_available: false,
      sidecar_runtime_state: 'stopped_after_cleanup',
      verified_readonly_sandbox: {
        verdict: 'VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY',
        review_status: 'PENDING_REVIEW',
        current_sidecar_available: false,
        sidecar_runtime_state: 'stopped_after_cleanup',
        report_path: 'DATA_MISSING',
        report_available: 'missing',
        evidence_artifacts: [],
      },
      data_missing: dataMissing,
    },
    artifact_refs: [],
    capability_status: [
      {
        id: 'browser_regression_offline',
        label: 'Browser regression offline mock',
        state: 'data_missing',
        summary: 'No live Strategy Lab runtime or sidecar transport is represented by this mock.',
      },
    ],
    boundary_flags: strategyLabBoundaryFlags(),
    data_missing: dataMissing,
    next_safe_actions: ['Keep Strategy Lab browser regression fixtures read-only and offline.'],
  }
}

function mockStrategyLabArtifactsResponse(): Record<string, unknown> {
  const dataMissing = [
    'Browser regression mock does not provide repo artifact review evidence.',
  ]
  return {
    ok: true,
    schema_version: 'cockpit_strategy_lab_artifacts_v1',
    generated_at: MOCK_NOW,
    artifact_review_route: '/api/cockpit/strategy-lab/artifacts',
    source_mode: 'repo_artifacts_only',
    artifacts: [],
    review_workflow: {
      schema_version: 'cockpit_strategy_lab_review_workflow_v1',
      generated_at: MOCK_NOW,
      source_mode: 'repo_artifacts_only',
      review_status: 'PENDING_REVIEW',
      current_sidecar_available: false,
      execution_allowed: false,
      canonical_financial_truth: false,
      real_transport: false,
      sort_options: [],
      filter_facets: [],
      group_summaries: [],
      review_queue: [],
      experiment_sessions: [],
      export_packets: [],
      data_missing: dataMissing,
    },
    boundary_flags: strategyLabBoundaryFlags(),
    data_missing: dataMissing,
  }
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

const CHAT_STREAM_SCENARIOS: ChatStreamScenario[] = [
  {
    matches: /analyst shell/i,
    events: [
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
    ],
  },
  {
    matches: /action proposal/i,
    events: [
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
    ],
  },
  {
    matches: /thesis note/i,
    events: [
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
    ],
  },
  {
    matches: /diagnostic flag/i,
    events: [
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
    ],
  },
  {
    matches: /unsupported financial claim/i,
    events: [
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
          evidence_labels: ['missing_required_evidence'],
          source_coverage_status: 'missing_required_evidence',
          claim_verified_source_count: 0,
          sufficient_for_analysis: false,
        },
      }],
    ],
  },
]

export function chatStreamForMessage(message: string): string {
  const scenario = CHAT_STREAM_SCENARIOS.find((item) => item.matches.test(message))
  if (scenario) {
    return createSseStream(scenario.events)
  }

  return createSseStream([
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

export async function mockCockpitApis(page: Page, counters: MockCounters): Promise<void> {
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
        body: chatStreamForMessage(String(payload?.message || '')),
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

    if (pathname === '/api/cockpit/home') {
      await fulfillJson(route, mockHomeResponse())
      return
    }

    if (pathname === '/api/cockpit/strategy-lab/status') {
      await fulfillJson(route, mockStrategyLabStatusResponse())
      return
    }

    if (pathname === '/api/cockpit/strategy-lab/artifacts') {
      await fulfillJson(route, mockStrategyLabArtifactsResponse())
      return
    }

    if (pathname === '/api/cockpit/pulse') {
      await fulfillJson(route, mockIntelPulseResponse())
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
      await fulfillJson(route, { groups: [], models: [] })
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

export async function sendChat(page: Page, prompt: string, expectedText: string | RegExp): Promise<void> {
  const input = page.getByPlaceholder(CHAT_INPUT_PLACEHOLDER)
  await input.waitFor({ state: 'visible' })
  await input.fill(prompt)
  await input.press('Enter')
  await page.getByText(expectedText).first().waitFor({ state: 'visible', timeout: 15_000 })
}

export async function inspectVisibleRoute(page: Page, route: string): Promise<RouteSmokeResult> {
  const errors: string[] = []
  const onPageError = (error: Error) => {
    errors.push(error.message)
  }
  page.on('pageerror', onPageError)

  let response: Awaited<ReturnType<Page['goto']>> = null
  try {
    response = await page.goto(route, { waitUntil: 'domcontentloaded' })
    await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => undefined)
    await page.waitForTimeout(250)
  } finally {
    page.off('pageerror', onPageError)
  }

  const statusCode = response?.status() ?? 0
  const bodyText = await page.locator('body').innerText({ timeout: 10_000 }).catch(() => '')
  const notFound = statusCode === 404 || /404|This page could not be found/i.test(bodyText)
  const serverError = statusCode >= 500 || /500|Internal Server Error|Application error/i.test(bodyText)
  const notConnected = /not connected|not configured|Cockpit Offline|NO_DATA_AVAILABLE|disabled/i.test(bodyText)
  const status: ParityStatus = notFound || serverError || errors.length > 0
    ? 'FAIL'
    : notConnected
      ? 'NOT_CONNECTED'
      : 'PASS'

  return {
    statusCode,
    status,
    bodyText,
    notConnected,
    errors,
  }
}
