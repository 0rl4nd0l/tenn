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

test.describe('thesis audit', () => {
  test('runs a report audit and stages a thesis proposal', async ({ page }) => {
    await mockShellRoutes(page)

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
          evidence_summary: { evidence_span_count: 1, memory_read_only: true },
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

    await page.goto('/thesis-audit')
    await page.getByPlaceholder('Ticker').fill('BHP')
    await page.getByPlaceholder('Paste report text').fill('BHP revenue was 100 in FY2025. The setup is stronger.')
    await page.getByRole('button', { name: /audit/i }).click()

    await expect(page.getByTestId('thesis-audit-claim-text')).toContainText(
      'BHP revenue was 100 in FY2025.',
    )
    await expect(page.getByText('non_canonical_thesis_source')).toBeVisible()

    await page.getByRole('tab', { name: 'Proposals' }).click()
    await page.getByRole('button', { name: 'Stage' }).click()
    await expect(page.getByRole('button', { name: 'Staged' })).toBeVisible()
  })
})
