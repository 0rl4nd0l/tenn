import { expect, test, type Page } from '@playwright/test'

async function mockWorkspaceMemoryRoutes(page: Page) {
  await page.route(/\/api\/cockpit\/chat\/sessions(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            session_id: 'global-main',
            updated_at: '2026-04-30T05:44:33Z',
            message_count: 24,
            title: 'Show me all data we have on BHP',
            last_message: 'Loaded BHP context.',
          },
        ],
      }),
    })
  })

  await page.route(/\/api\/ops\/jobs(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            job_id: 'job-1',
            job_family: 'cockpit_action',
            job_type: 'single_ticker_announcement_backfill',
            status: 'running',
            title: 'Single ticker backfill',
            phase: 'backfill',
            current_item_label: 'ticker=BHP',
            ticker: 'BHP',
            updated_at: '2026-04-30T05:44:00Z',
          },
        ],
      }),
    })
  })

  await page.route(/\/api\/cockpit\/feedback\/flags(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            report_id: 'auto-1',
            feedback_type: 'poor',
            capture_kind: 'auto_diagnostic',
            session_id: 'global-main',
            saved_at: '2026-04-30T05:43:00Z',
            note: 'Auto diagnostic flag',
            flagged_response_excerpt: 'Missing sources.',
            resolution_status: 'open',
          },
        ],
      }),
    })
  })

  await page.route(/\/api\/cockpit\/marketplace\/alerts(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            alert_id: 'alert-1',
            mission_name: 'GPU workstation',
            match_title: 'Used GPU listing',
            trigger_reason: 'Strong match',
            price: '$400',
            location: 'Melbourne',
            decision_band: 'strong_match',
            status: 'new',
            updated_at: '2026-04-30T05:42:00Z',
          },
        ],
      }),
    })
  })
}

test.describe('memory tab browser UX', () => {
  test('loads full memory index without ticker search and supports strategy/company navigation', async ({ page }) => {
    await mockWorkspaceMemoryRoutes(page)

    await page.route(/\/api\/cockpit\/memory\/index(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ticker: null,
          summary: {
            company_memory_entry_count: 3,
            company_memory_change_count: 0,
            market_memory_item_count: 2,
            user_thesis_entry_count: 1,
            user_thesis_proposal_count: 1,
            company_memory_ticker_count: 2,
            user_thesis_ticker_count: 1,
          },
          company_memory: {
            entries: [
              {
                entry_id: 101,
                company_id: 'BHP',
                type: 'observed_fact',
                statement: 'Iron ore unit costs improved in Q3.',
                status: 'active',
                updated_at: '2026-04-21T05:04:03Z',
                confidence: 0.88,
              },
              {
                entry_id: 102,
                company_id: 'BHP',
                type: 'risk',
                statement: 'Rail disruption risk remains elevated.',
                status: 'archived',
                updated_at: '2026-04-19T01:02:03Z',
                confidence: 0.63,
              },
              {
                entry_id: 103,
                company_id: 'RIO',
                type: 'observed_fact',
                statement: 'Pilbara shipment reliability improved versus last quarter.',
                status: 'active',
                updated_at: '2026-04-22T03:02:01Z',
                confidence: 0.79,
              },
            ],
            change_log: [],
          },
          market_memory: {
            sector_items: [
              {
                entry_id: 201,
                sector: 'Materials',
                type: 'sector_trend',
                statement: 'Bulk commodity margin compression stabilising.',
                status: 'active',
                updated_at: '2026-04-20T02:03:04Z',
              },
            ],
            macro_items: [
              {
                entry_id: 301,
                macro_topic: 'china_policy',
                type: 'macro_theme',
                statement: 'China policy easing may support steel demand.',
                status: 'active',
                updated_at: '2026-04-20T08:09:10Z',
              },
            ],
          },
          user_thesis_memory: {
            entries: [
              {
                entry_id: 401,
                ticker: 'BHP',
                entry_type: 'thesis',
                statement: 'Base case remains HOLD pending capex clarity.',
                status: 'active',
                signal: 'HOLD',
                updated_at: '2026-04-18T03:04:05Z',
              },
            ],
            proposals: [
              {
                proposal_id: 'prop-1',
                ticker: 'BHP',
                proposal_type: 'add_evidence',
                statement: 'Add evidence on Pilbara grade differentials.',
                status: 'pending',
                signal: 'HOLD',
                created_at: '2026-04-22T01:02:03Z',
              },
            ],
          },
          errors: [],
        }),
      })
    })

    await page.goto('/memory')
    await expect(page.getByText('Memory Level Directory')).toBeVisible()
    await expect(page.getByText('Financial Truth').first()).toBeVisible()
    await expect(page.getByText('Session Memory').first()).toBeVisible()
    await expect(page.getByText('Operational State').first()).toBeVisible()
    await expect(page.getByText('Iron ore unit costs improved in Q3.').first()).toBeVisible()

    await expect(page.getByRole('tab', { name: 'Session' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Operational' })).toBeVisible()

    await page.getByRole('tab', { name: 'Session' }).click()
    await expect(page.getByText('Show me all data we have on BHP').first()).toBeVisible()

    await page.getByRole('tab', { name: 'Operational' }).click()
    await expect(page.getByText('Single ticker backfill').first()).toBeVisible()
    await expect(page.getByText('Auto diagnostic flag').first()).toBeVisible()

    await page.getByRole('tab', { name: 'Strategy' }).click()
    await expect(page.getByText('Strategy / Thesis Memory').first()).toBeVisible()
    await page.getByRole('button').filter({ hasText: 'Add evidence on Pilbara grade differentials.' }).first().click()
    await expect(page.getByRole('button', { name: 'Confirm' })).toBeVisible()

    await page.getByRole('tab', { name: 'Company' }).click()
    await expect(page.getByText('Iron ore unit costs improved in Q3.').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Edit' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Expire' })).toBeVisible()
  })

  test('shows ticker-scoped Financial Truth entries as browseable read-only context', async ({ page }) => {
    await mockWorkspaceMemoryRoutes(page)

    await page.route(/\/api\/cockpit\/memory\/index(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
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
        }),
      })
    })

    await page.route(/\/api\/cockpit\/memory\?.*ticker=BHP.*$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ticker: 'BHP',
          summary: {
            company_memory_entry_count: 1,
            company_memory_change_count: 0,
            market_memory_item_count: 0,
            user_thesis_entry_count: 0,
            user_thesis_proposal_count: 0,
          },
          company_memory: {
            entries: [
              {
                entry_id: 777,
                company_id: 'BHP',
                type: 'observed_fact',
                statement: 'Persistent memory note.',
                status: 'active',
                updated_at: '2026-04-22T01:02:03Z',
              },
            ],
            change_log: [],
          },
          market_memory: { sector_items: [], macro_items: [] },
          user_thesis_memory: { entries: [], proposals: [] },
          errors: [],
        }),
      })
    })

    await page.route(/\/api\/cockpit\/memory\/company-dump\?.*ticker=BHP.*$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ticker: 'BHP',
          summary: {
            doc_count: 1,
            financial_period_count: 1,
            announcement_context_count: 1,
            risk_note_count: 1,
            extraction_failure_count: 1,
            low_confidence_financial_count: 1,
          },
          docs: [
            {
              document_id: 'doc-101',
              ticker: 'BHP',
              doc_class: 'results',
              doc_subtype: 'quarterly',
              published_at: '2026-04-20T00:00:00Z',
              title: 'Q3 FY26 Quarterly Production Report',
            },
          ],
          financials: [
            {
              ticker: 'BHP',
              period_end: '2025-12-31',
              period_type: 'H1',
              revenue: 10200000000,
              ebit: 3980000000,
              np_attributable: 2200000000,
            },
          ],
          announcement_context: [
            {
              document_id: 'ann-77',
              ticker: 'BHP',
              published_at: '2026-04-19T00:00:00Z',
              title: 'Operational update',
              excerpt: 'Copper production improved versus prior quarter.',
            },
          ],
          risk_notes: [
            {
              document_id: 'risk-10',
              ticker: 'BHP',
              published_at: '2026-04-18T00:00:00Z',
              risk_summary: 'Cost inflation remains elevated.',
            },
          ],
          extraction_failures: [
            {
              run_id: 'run-fail-1',
              document_id: 'doc-fail-9',
              status: 'failed',
              error: 'table parse failed',
              created_at: '2026-04-17T00:00:00Z',
              ticker: 'BHP',
              title: 'Appendix financial tables',
            },
          ],
          low_confidence_financials: [
            {
              ticker: 'BHP',
              period_end: '2025-06-30',
              period_type: 'FY',
              revenue: 19800000000,
            },
          ],
          errors: [],
        }),
      })
    })

    await page.goto('/memory')
    await expect(page.getByText('Loaded full persistent memory index.')).toBeVisible()
    await page.getByPlaceholder('Ticker filter (optional, e.g. BHP)').fill('BHP')
    await page.getByRole('button', { name: 'Load Ticker' }).click()

    await page.getByRole('tab', { name: 'Financial Truth' }).click()
    await expect(page.getByText('/documents')).toBeVisible()
    await expect(page.getByText('/financial_periods')).toBeVisible()
    await expect(page.getByRole('button').filter({ hasText: 'Q3 FY26 Quarterly Production Report' }).first()).toBeVisible()
    await expect(page.getByText('Copper production improved versus prior quarter.')).toBeVisible()

    await page.getByRole('button').filter({ hasText: 'Q3 FY26 Quarterly Production Report' }).first().click()
    await expect(page.getByText('Type: results/quarterly')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Expire' })).toHaveCount(0)
  })
})
