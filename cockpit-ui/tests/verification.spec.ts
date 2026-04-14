import { expect, test, type Page } from '@playwright/test'

const PNG_1X1_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0L8AAAAASUVORK5CYII='

function buildMockState() {
  const docs = [
    {
      document_id: 'doc-1234567890abcdef',
      ticker: 'BHP',
      doc_class: '4D',
      published_at: '2026-04-01T00:00:00Z',
      title: 'BHP Quarterly Report',
    },
  ]

  const recentRuns = [
    {
      run_id: 'run-1234567890abcdef',
      document_id: 'doc-1234567890abcdef',
      ticker: 'BHP',
      title: 'BHP Quarterly Report',
      status: 'succeeded',
      created_at: '2026-04-01T12:00:00Z',
      requested_method: 'docling',
      actual_method: 'docling',
      strict_method: true,
      metrics_count: 2,
    },
  ]

  const session = {
    session_id: 'session-1234567890abcdef',
    created_at: '2026-04-01T12:00:00Z',
    document_ids: ['doc-1234567890abcdef'],
    run_ids: ['run-1234567890abcdef'],
    items: [
      {
        item_id: 'item-1',
        run_id: 'run-1234567890abcdef',
        document_id: 'doc-1234567890abcdef',
        ticker: 'BHP',
        title: 'BHP Quarterly Report',
        metric_name: 'revenue_total',
        metric_value: '1000000',
        extracted_value: '1000000',
        period_type: 'annual',
        period_end: '2025-06-30',
        page_number: 7,
        evidence_quality: 'precise',
        evidence_summary: 'Revenue line matched from the quarterly cash flow table.',
        evidence_reference: 'Page 7 / table 2 / row revenue_total',
        matched_text: 'Revenue 1,000,000',
        image_url: '/api/extraction-review/snippets/revenue.png',
        image_path: 'snippets/revenue.png',
        requested_method: 'docling',
        actual_method: 'docling',
        strict_method: true,
        parser_id: 'docling_v1',
        fallback_used: false,
        method_warnings: [],
        provenance_status: 'verified',
        row_refs: { revenue_total: 'row-1' },
        snippet: {
          kind: 'line_crop',
          status: 'ready',
          image_url: '/api/extraction-review/snippets/revenue.png',
          image_path: 'snippets/revenue.png',
          matched_text: 'Revenue 1,000,000',
        },
        review_status: 'pending',
      },
      {
        item_id: 'item-2',
        run_id: 'run-1234567890abcdef',
        document_id: 'doc-1234567890abcdef',
        ticker: 'BHP',
        title: 'BHP Quarterly Report',
        metric_name: 'net_debt',
        metric_value: '250000',
        extracted_value: '250000',
        period_type: 'annual',
        period_end: '2025-06-30',
        page_number: 9,
        evidence_quality: 'approximate',
        evidence_summary: 'Net debt preview came from the balance sheet page.',
        evidence_reference: 'Page 9 / balance sheet / net debt',
        matched_text: 'Net debt 250,000',
        image_url: '/api/extraction-review/snippets/netdebt.png',
        image_path: 'snippets/netdebt.png',
        requested_method: 'docling',
        actual_method: 'docling',
        strict_method: true,
        parser_id: 'docling_v1',
        fallback_used: false,
        method_warnings: ['preview_only'],
        provenance_status: 'preview',
        source_label: 'balance_sheet',
        snippet: {
          kind: 'page_crop',
          status: 'ready',
          image_url: '/api/extraction-review/snippets/netdebt.png',
          image_path: 'snippets/netdebt.png',
          matched_text: 'Net debt 250,000',
        },
        review_status: 'pending',
      },
    ],
    summary: {
      total: 2,
      approved: 0,
      wrong: 0,
      abstain: 0,
      pending: 2,
    },
  }

  let wrongQueue = {
    updated_at: '2026-04-01T12:00:00Z',
    count: 0,
    items: [] as Array<Record<string, unknown>>,
  }

  let decisionCalls = 0

  const runStatus = {
    summary: {
      run_id: 'run-1234567890abcdef',
      document_id: 'doc-1234567890abcdef',
      requested_method: 'docling',
      actual_method: 'docling',
      strict_method: true,
      stage: 'persist',
      status: 'succeeded',
      queued_at: '2026-04-01T12:00:00Z',
      worker_started_at: '2026-04-01T12:00:02Z',
      updated_at: '2026-04-01T12:00:04Z',
      completed_at: '2026-04-01T12:00:04Z',
      elapsed_ms: 4000,
      queue_wait_ms: 2000,
      last_message: 'Extraction run completed successfully.',
      warning_codes: [],
      error_codes: [],
      warnings: [],
      errors: [],
      stage_timings_ms: {
        parse: 1000,
        extract: 1800,
        persist: 1200,
      },
    },
    events: [
      {
        run_id: 'run-1234567890abcdef',
        document_id: 'doc-1234567890abcdef',
        stage: 'parse',
        status: 'running',
        timestamp: '2026-04-01T12:00:02Z',
        elapsed_ms: 1000,
        message: 'Parsing document',
        details: { step: 'parse' },
      },
      {
        run_id: 'run-1234567890abcdef',
        document_id: 'doc-1234567890abcdef',
        stage: 'extract',
        status: 'running',
        timestamp: '2026-04-01T12:00:03Z',
        elapsed_ms: 2800,
        message: 'Extracting metrics',
        details: { step: 'extract' },
      },
      {
        run_id: 'run-1234567890abcdef',
        document_id: 'doc-1234567890abcdef',
        stage: 'persist',
        status: 'succeeded',
        timestamp: '2026-04-01T12:00:04Z',
        elapsed_ms: 4000,
        message: 'Persisted extraction output',
        details: { step: 'persist' },
      },
    ],
  }

  const goldEval = {
    dataset_dir: 'financial-engine_v2/data/extraction_gold_real',
    requested_method: 'docling',
    strict_method: true,
    summary: {
      total_documents: 2,
      total_accuracy: 0.75,
      context_accuracy: 1,
      trust_matches_expected: 2,
      metric_status_counts: { exact: 3, mismatch: 1 },
      trust_distribution: { trusted: 2, abstain: 0, quarantine: 0 },
    },
    documents: [
      {
        document_id: 'doc-1234567890abcdef',
        ticker: 'BHP',
        extraction_status: 'ok',
        context_correct: true,
        trust_outcome: 'trusted',
        expected_trust: 'trusted',
        mismatch_reasons: [],
        review_session_id: null,
        review_item_count: 0,
        review_reason: null,
        metric_results: {
          revenue_total: { status: 'exact', expected: 1000000, actual: 1000000, reason: '' },
        },
        method_provenance: {
          requested_method: 'docling',
          actual_method: 'docling',
          strict_method: true,
        },
      },
      {
        document_id: 'doc-9876543210fedcba',
        ticker: 'BHP',
        extraction_status: 'ok_low_confidence',
        context_correct: true,
        trust_outcome: 'trusted',
        expected_trust: 'trusted',
        mismatch_reasons: ['net_debt mismatch'],
        review_session_id: 'session-1234567890abcdef',
        review_item_count: 2,
        review_reason: 'reviewable',
        metric_results: {
          net_debt: { status: 'mismatch', expected: 300000, actual: 250000, reason: 'source mismatch' },
        },
        method_provenance: {
          requested_method: 'docling',
          actual_method: 'docling',
          strict_method: true,
        },
      },
    ],
  }

  const verificationResults = {
    metrics: [
      { metric: 'revenue_total', expected: 1000000, actual: 1000000, passed: true, details: 'Exact match' },
      { metric: 'net_debt', expected: 300000, actual: 250000, passed: false, details: 'Mismatch' },
    ],
  }

  return {
    docs,
    recentRuns,
    session,
    get wrongQueue() {
      return wrongQueue
    },
    setWrongQueue(value: typeof wrongQueue) {
      wrongQueue = value
    },
    runStatus,
    goldEval,
    verificationResults,
    get decisionCalls() {
      return decisionCalls
    },
    incrementDecisionCalls() {
      decisionCalls += 1
    },
  }
}

async function mockVerificationApi(page: Page) {
  const state = buildMockState()

  await page.route('**/api/cockpit/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'healthy', services: [] }),
    })
  })

  await page.route('**/api/cockpit/config', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ extraction_active_runs: [] }),
    })
  })

  await page.route('**/api/context/ticker**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ docs: state.docs }),
    })
  })

  await page.route('**/api/extraction-review/runs**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: state.recentRuns.length, items: state.recentRuns }),
    })
  })

  await page.route('**/api/process/document/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        mode: 'inline',
        document_id: state.docs[0].document_id,
        run_id: state.recentRuns[0].run_id,
        extraction_status: 'ok',
        method_provenance: {
          requested_method: 'docling',
          actual_method: 'docling',
          strict_method: true,
          parser_id: 'docling_v1',
          fallback_used: false,
        },
      }),
    })
  })

  await page.route('**/api/extraction-review/session', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state.session),
    })
  })

  await page.route('**/api/extraction-review/session/*', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state.session),
      })
      return
    }
    await route.fallback()
  })

  await page.route('**/api/extraction-review/session/*/decision', async (route) => {
    state.incrementDecisionCalls()
    const body = JSON.parse(route.request().postData() || '{}') as { item_id: string; status: 'approved' | 'wrong' | 'abstain' }
    const item = state.session.items.find((entry) => entry.item_id === body.item_id)
    if (!item) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'missing item' }) })
      return
    }

    item.review_status = body.status
    const summary = {
      total: state.session.items.length,
      approved: state.session.items.filter((entry) => entry.review_status === 'approved').length,
      wrong: state.session.items.filter((entry) => entry.review_status === 'wrong').length,
      abstain: state.session.items.filter((entry) => entry.review_status === 'abstain').length,
      pending: state.session.items.filter((entry) => entry.review_status === 'pending').length,
    }
    state.session.summary = summary

    if (body.status === 'wrong') {
      state.setWrongQueue({
        updated_at: '2026-04-01T12:05:00Z',
        count: 1,
        items: [
          {
            ...item,
            expected_value: '1200000',
            reviewer_note: 'Manual correction required',
          },
        ],
      })
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        session_id: state.session.session_id,
        item,
        summary,
      }),
    })
  })

  await page.route('**/api/extraction-review/errors**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state.wrongQueue),
    })
  })

  await page.route('**/api/extraction-review/run/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state.runStatus),
    })
  })

  await page.route('**/api/context/verification**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state.verificationResults),
    })
  })

  await page.route('**/api/extraction-eval/real-gold', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state.goldEval),
    })
  })

  await page.route('**/api/extraction-review/snippets/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'image/png',
      body: Buffer.from(PNG_1X1_BASE64, 'base64'),
    })
  })

  return state
}

async function loadReviewSession(page: Page) {
  await page.goto('/verification')
  await page.getByPlaceholder('e.g. BHP').fill('BHP')
  await page.getByRole('button', { name: 'Load Docs' }).click()
  await expect(page.getByText('BHP Quarterly Report')).toBeVisible()
  await page.getByRole('button', { name: 'Latest + Review' }).click()
  await expect(page.getByText('Review 1 of 2')).toBeVisible()
}

test.describe('Verification screen', () => {
  test('shows workflow tabs and switches visible panels', async ({ page }) => {
    await mockVerificationApi(page)
    await page.goto('/verification')

    await expect(page.getByRole('tab', { name: /^Review/ })).toBeVisible()
    await expect(page.getByRole('tab', { name: /^Runs/ })).toBeVisible()
    await expect(page.getByRole('tab', { name: /^Real-Gold/ })).toBeVisible()
    await expect(page.getByRole('tab', { name: /^Verify/ })).toBeVisible()
    await expect(page.getByText('Manual Extraction Review')).toBeVisible()

    await page.getByRole('tab', { name: /^Runs/ }).click()
    await expect(page).toHaveURL(/tab=runs/)
    await expect(page.getByText('Run Timeline', { exact: true })).toBeVisible()

    await page.getByRole('tab', { name: /^Real-Gold/ }).click()
    await expect(page).toHaveURL(/tab=gold-eval/)
    await expect(page.getByText('Real Gold Set Evaluation')).toBeVisible()

    await page.getByRole('tab', { name: /^Verify/ }).click()
    await expect(page).toHaveURL(/tab=verify/)
    await expect(page.getByText('Data Verification')).toBeVisible()

    await page.getByRole('tab', { name: /^Review/ }).click()
    await expect(page).not.toHaveURL(/tab=/)
    await expect(page.getByText('Manual Extraction Review')).toBeVisible()
  })

  test('renders the core review flow and trust decision updates', async ({ page }) => {
    await mockVerificationApi(page)
    await loadReviewSession(page)

    await expect(page.getByRole('button', { name: /Mark revenue_total as wrong/i })).toBeVisible()
    await page.getByRole('button', { name: /Mark revenue_total as wrong/i }).click()

    await expect(page.getByText('Review 2 of 2')).toBeVisible()
    await expect(page.getByText('wrong 1', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('pending review 1')).toBeVisible()
    await expect(page.getByText('Extraction Wrong Queue')).toBeVisible()
    await expect(page.getByText('Manual correction required')).toBeVisible()
  })

  test('keeps keyboard shortcuts guarded and exposes runs, verify, and real-gold state', async ({ page }) => {
    const state = await mockVerificationApi(page)
    await loadReviewSession(page)

    await page.getByPlaceholder('e.g. BHP').focus()
    await page.keyboard.press('c')
    await expect.poll(() => state.decisionCalls).toBe(0)
    await expect(page.getByText('correct 0', { exact: true }).first()).toBeVisible()

    await page.locator('body').click()
    await page.keyboard.press('c')
    await expect.poll(() => state.decisionCalls).toBe(1)
    await expect(page.getByText('Review 2 of 2')).toBeVisible()
    await expect(page.getByText('correct 1', { exact: true }).first()).toBeVisible()

    await page.getByRole('tab', { name: /^Runs/ }).click()
    await expect(page.getByText('Run Timeline', { exact: true })).toBeVisible()
    await expect(page.getByText('Extraction run completed successfully.')).toBeVisible()
    await page.keyboard.press('w')
    await expect.poll(() => state.decisionCalls).toBe(1)

    await page.getByRole('tab', { name: /^Verify/ }).click()
    await page.getByRole('button', { name: 'Verify Ticker' }).click()
    await expect(page.getByText('Verification Results')).toBeVisible()
    await expect(page.getByText('50%')).toBeVisible()

    await page.getByRole('tab', { name: /^Real-Gold/ }).click()
    await page.getByRole('button', { name: 'Run Gold Set' }).click()
    await expect(page.getByText('Metric Accuracy')).toBeVisible()
    await expect(page.getByText('75.0%')).toBeVisible()
    await page.getByRole('button', { name: /Open Review/ }).click()
    await expect(page.getByText('Manual Extraction Review')).toBeVisible()
    await expect(page.getByText('Review 1 of 2')).toBeVisible()
  })
})
