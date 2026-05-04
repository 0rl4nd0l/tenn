import { expect, test, type Page } from '@playwright/test'

async function mockShellRoutes(page: Page) {
  await page.route(/\/api\/cockpit\/health(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'healthy', services: [{ name: 'backend', status: 'healthy' }] }),
    })
  })
  await page.route(/\/api\/cockpit\/preferences(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ api_default_enabled: false, marketplace_prefer_cloud_routing: false }),
    })
  })
  await page.route(/\/api\/cockpit\/config(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ model: 'test-model', max_tokens: 4096, temperature: 0 }),
    })
  })
  await page.route(/\/api\/cockpit\/chat\/sessions(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [] }),
    })
  })
}

async function mockThesisCoverage(
  page: Page,
  evidenceSummary: Record<string, unknown> = {
    evidence_span_count: 1,
    memory_read_only: true,
    sufficient_for_analysis: true,
    missing_categories_after_recovery: [],
    coverage_status: 'ready',
    coverage_message: 'Backend evidence coverage is sufficient for a thesis audit.',
    proposal_gate: {
      allowed: true,
      reason: 'evidence_sufficient',
      message: 'Backend evidence is sufficient for staged thesis memory proposals.',
    },
  },
) {
  await page.route(/\/api\/cockpit\/thesis-audit\/coverage(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticker: 'BHP',
        generated_at: '2026-04-30T05:00:00Z',
        evidence_summary: evidenceSummary,
        guardrails: {
          memory_read_only: true,
          user_thesis_memory_proposals_allowed: true,
          qdrant_written: false,
        },
      }),
    })
  })
}

async function gotoThesisAudit(page: Page) {
  const preferencesLoaded = page.waitForResponse(
    (response) =>
      response.url().includes('/api/cockpit/preferences') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  const healthLoaded = page.waitForResponse(
    (response) => response.url().includes('/api/cockpit/health') && response.status() === 200,
  )

  await page.goto('/thesis-audit')
  await Promise.all([preferencesLoaded, healthLoaded])
}

async function fillAuditInputs(page: Page, ticker: string, reportText: string) {
  const tickerInput = page.getByPlaceholder('Ticker')
  const reportInput = page.getByPlaceholder('Paste report text')

  await expect(page.getByText('No audit loaded.')).toBeVisible()

  await tickerInput.fill('')
  await tickerInput.pressSequentially(ticker.toLowerCase())
  await expect(tickerInput).toHaveValue(ticker.toUpperCase())

  await reportInput.fill(reportText)
  await expect(reportInput).toHaveValue(reportText)
  await expect(page.getByRole('button', { name: /audit/i })).toBeEnabled()
}

test.describe('thesis audit', () => {
  test('runs a report audit and stages a thesis proposal', async ({ page }) => {
    await mockShellRoutes(page)
    await mockThesisCoverage(page)

    await page.route(/\/api\/cockpit\/thesis-audit$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          audit_id: 'audit-1',
          ticker: 'BHP',
          generated_at: '2026-04-30T05:00:00Z',
          report_source: {
            source_role: 'non_canonical_thesis_source',
            span_count: 1,
            text_chars: 200,
          },
          thesis_summary: 'The report thesis is that BHP revenue supports a stronger setup.',
          claims: [
            {
              claim_id: 'claim_1',
              text: 'BHP revenue was 100 in FY2025.',
              claim_type: 'numeric_fact',
              report_span: {
                span_id: 'report_span_1',
                start: 0,
                end: 32,
                text: 'BHP revenue was 100 in FY2025.',
              },
              confidence_label: 'Inferred',
              load_bearing_score: 0.8,
              load_bearing_rank: 1,
            },
          ],
          hidden_assumptions: [],
          verification_matrix: [
            {
              claim_id: 'claim_1',
              status: 'supported',
              confidence_label: 'Confirmed',
              rationale: 'Canonical financial truth supports the number.',
              report_span: {
                span_id: 'report_span_1',
                start: 0,
                end: 32,
                text: 'BHP revenue was 100 in FY2025.',
              },
              independent_evidence_spans: [
                {
                  evidence_id: 'evidence_1',
                  source_layer: 'financial_truth',
                  source_type: 'financial_period',
                  text: 'annual 2025-06-30; revenue=100',
                  url: 'https://example.test/bhp-annual-report',
                },
              ],
              contradicting_evidence_spans: [],
              evidence_gap: null,
            },
          ],
          contrarian_findings: [],
          strongest_disconfirming_evidence: [],
          change_my_mind_triggers: [],
          next_diligence_questions: ['Which canonical filing line verifies the revenue?'],
          user_thesis_memory_proposals: [
            {
              proposal_type: 'create_thesis',
              statement: 'The report thesis is that BHP revenue supports a stronger setup.',
              signal: null,
              confidence: 0.55,
              metadata: {
                source: 'research_report_thesis_audit',
                requires_confirmation: true,
                non_canonical_report_source: true,
              },
            },
          ],
          evidence_summary: {
            evidence_span_count: 1,
            memory_read_only: true,
            sufficient_for_analysis: true,
            missing_categories_after_recovery: [],
          },
          guardrails: { user_thesis_memory_auto_saved: false },
        }),
      })
    })

    await page.route(/\/api\/cockpit\/memory\/thesis\/proposals$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, proposal: { proposal_id: 'prop-1', status: 'pending' } }),
      })
    })

    await gotoThesisAudit(page)
    await fillAuditInputs(page, 'BHP', 'BHP revenue was 100 in FY2025. The setup is stronger.')
    await expect(page.getByTestId('thesis-audit-coverage-preflight')).toContainText('Coverage: ready')
    await page.getByRole('button', { name: /audit/i }).click()

    await expect(page.getByTestId('thesis-audit-claim-text')).toContainText(
      'BHP revenue was 100 in FY2025.',
    )
    await expect(page.getByText('non_canonical_thesis_source')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Open source' })).toHaveAttribute(
      'href',
      'https://example.test/bhp-annual-report',
    )

    await page.getByRole('tab', { name: 'Proposals' }).click()
    await page.getByRole('button', { name: 'Stage' }).click()
    await expect(page.getByRole('link', { name: 'View in Memory' })).toHaveAttribute(
      'href',
      '/memory?tab=thesis',
    )
  })

  test('marks evidence-limited audits and shows empty sections', async ({ page }) => {
    await mockShellRoutes(page)
    await mockThesisCoverage(page, {
      evidence_span_count: 0,
      memory_read_only: true,
      sufficient_for_analysis: false,
      missing_categories_after_recovery: ['financial_truth', 'news'],
      coverage_status: 'no_backend_evidence',
      coverage_message: 'No backend evidence is available for this ticker.',
      proposal_gate: {
        allowed: false,
        reason: 'no_backend_evidence',
        message: 'Thesis memory proposals are blocked until backend evidence exists for this ticker.',
      },
    })

    await page.route(/\/api\/cockpit\/thesis-audit$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          audit_id: 'audit-limited',
          ticker: 'BHP',
          generated_at: '2026-04-30T05:00:00Z',
          report_source: {
            source_role: 'non_canonical_thesis_source',
            span_count: 1,
            text_chars: 80,
          },
          thesis_summary: 'The thesis could not be fully checked against backend evidence.',
          claims: [
            {
              claim_id: 'claim_1',
              text: 'BHP has a materially stronger near-term setup.',
              claim_type: 'company_narrative',
              report_span: {
                span_id: 'report_span_1',
                start: 0,
                end: 48,
                text: 'BHP has a materially stronger near-term setup.',
              },
              confidence_label: 'Inferred',
              load_bearing_score: 0.7,
              load_bearing_rank: 1,
            },
          ],
          hidden_assumptions: [],
          verification_matrix: [
            {
              claim_id: 'claim_1',
              status: 'DATA_MISSING',
              confidence_label: 'Speculative',
              rationale: 'No backend evidence was available.',
              report_span: {
                span_id: 'report_span_1',
                start: 0,
                end: 48,
                text: 'BHP has a materially stronger near-term setup.',
              },
              independent_evidence_spans: [],
              contradicting_evidence_spans: [],
              evidence_gap: 'canonical filings',
            },
          ],
          contrarian_findings: [],
          strongest_disconfirming_evidence: [],
          change_my_mind_triggers: [],
          next_diligence_questions: [],
          user_thesis_memory_proposals: [],
          evidence_summary: {
            evidence_span_count: 0,
            memory_read_only: true,
            sufficient_for_analysis: false,
            missing_categories_after_recovery: ['financial_truth', 'news'],
            coverage_status: 'no_backend_evidence',
            coverage_message: 'No backend evidence is available for this ticker.',
            proposal_gate: {
              allowed: false,
              reason: 'no_backend_evidence',
              message: 'Thesis memory proposals are blocked until backend evidence exists for this ticker.',
            },
          },
          guardrails: { user_thesis_memory_auto_saved: false },
        }),
      })
    })

    await gotoThesisAudit(page)
    await fillAuditInputs(page, 'BHP', 'BHP has a materially stronger near-term setup.')
    await expect(page.getByTestId('thesis-audit-coverage-preflight')).toContainText(
      'Coverage: no backend evidence',
    )
    await page.getByRole('button', { name: /audit/i }).click()

    await expect(page.getByTestId('thesis-audit-evidence-limited')).toContainText('Evidence-limited result')
    await expect(page.getByText('Missing after recovery: financial_truth, news')).toBeVisible()

    await page.getByRole('tab', { name: 'Contrarian' }).click()
    await expect(page.getByText('No contrarian findings were returned for this audit.')).toBeVisible()

    await page.getByRole('tab', { name: 'Proposals' }).click()
    await expect(page.getByText('No thesis memory proposals were generated.')).toBeVisible()
    await expect(
      page.getByText('Thesis memory proposals are blocked until backend evidence exists for this ticker.'),
    ).toBeVisible()

    await page.getByRole('tab', { name: 'Diligence' }).click()
    await expect(page.getByText('No change-my-mind triggers were returned.')).toBeVisible()
    await expect(page.getByText('No next diligence questions were returned.')).toBeVisible()
    await expect(page.getByText('No hidden assumptions were extracted.')).toBeVisible()
  })
})
