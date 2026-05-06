import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ComponentProps } from 'react'
import { beforeAll, describe, expect, it, vi } from 'vitest'

import type { ConfirmedMetricCoveragePacket } from '../types'
import { MetricCoverageTabPanel } from './metric-coverage-tab-panel'

beforeAll(() => {
  if (!HTMLElement.prototype.hasPointerCapture) {
    HTMLElement.prototype.hasPointerCapture = () => false
  }
  if (!HTMLElement.prototype.setPointerCapture) {
    HTMLElement.prototype.setPointerCapture = () => undefined
  }
  if (!HTMLElement.prototype.releasePointerCapture) {
    HTMLElement.prototype.releasePointerCapture = () => undefined
  }
})

function packet(): ConfirmedMetricCoveragePacket {
  return {
    status: 'ready_with_warnings',
    profile: 'confirmed_metric_coverage',
    generated_at: '2026-05-05T00:00:00Z',
    head: 'adb76fac485e',
    branch: 'preserve/dirty-work-20260430T065748Z',
    git_available: true,
    git_head: 'adb76fac485e0000000000000000000000000000',
    git_head_short: 'adb76fac485e',
    git_branch: 'preserve/dirty-work-20260430T065748Z',
    git_dirty: false,
    git_status_short_summary: {
      line_count: 0,
      entries: [],
      truncated: false,
    },
    git_unavailable_reason: null,
    fixture_dir: 'financial-engine_v2/backend/tests/eval_fixtures',
    artifact_path: 'reports/extraction_eval/confirmed_metric_coverage_review_20260505T000000Z/review_packet.json',
    summary: {
      profile: 'confirmed_metric_coverage',
      fixture_count: 15,
      total_expectations: 146,
      scored_count: 73,
      candidate_review_required_count: 70,
      ambiguous_count: 3,
      unsupported_count: 0,
      missing_source_evidence_count: 0,
      missing_source_pdf_count: 0,
      classification_counts: {
        CONFIRMED_SOURCE_EVIDENCED: 1,
        CANDIDATE_REVIEW_REQUIRED: 1,
        AMBIGUOUS_OR_DERIVED: 1,
      },
      review_status_counts: {
        review_only_confirmed: 1,
        needs_human_review: 1,
        blocked_ambiguous: 1,
      },
      generated_at: '2026-05-05T00:00:00Z',
      head: 'adb76fac485e',
      branch: 'preserve/dirty-work-20260430T065748Z',
      git_available: true,
      git_head: 'adb76fac485e0000000000000000000000000000',
      git_head_short: 'adb76fac485e',
      git_branch: 'preserve/dirty-work-20260430T065748Z',
      git_dirty: false,
      git_status_short_summary: {
        line_count: 0,
        entries: [],
        truncated: false,
      },
      git_unavailable_reason: null,
      fixture_dir: 'financial-engine_v2/backend/tests/eval_fixtures',
      artifact_path: 'reports/extraction_eval/confirmed_metric_coverage_review_20260505T000000Z/review_packet.json',
      canonical_core_unchanged: true,
      expanded_required_unchanged: true,
      canonical_labels_mutated: false,
    },
    artifacts: {
      artifact_dir: 'reports/extraction_eval/confirmed_metric_coverage_review_20260505T000000Z',
      json_path: 'reports/extraction_eval/confirmed_metric_coverage_review_20260505T000000Z/review_packet.json',
      markdown_path: 'reports/extraction_eval/confirmed_metric_coverage_review_20260505T000000Z/review_packet.md',
    },
    warnings: ['Candidate rows require human source-evidence review.'],
    errors: [],
    rows: [
      {
        fixture_id: 'bhp_fy2021_preliminary_final',
        document_id: 'bhp_fy2021_preliminary_final',
        fixture: 'BHP_A_2021-06-30.json',
        ticker: 'BHP',
        period: { period_type: 'A', period_end: '2021-06-30' },
        metric_name: 'revenue',
        canonical_field: 'revenue',
        expectation_type: 'value',
        expected_value: 60817000000,
        expected_null: false,
        currency: 'USD',
        scale: 'millions',
        source_pdf_path: 'data/asx/docs/BHP/report.pdf',
        source_pdf_exists: true,
        source_pdf_status: 'present',
        source_pdf_present: true,
        source_page: 44,
        source_page_present: true,
        source_table: '43',
        source_table_present: true,
        source_row: 'Revenue 60,817',
        source_row_present: true,
        precise_source_evidence: true,
        broad_or_suspect_source_evidence: false,
        human_review_required: false,
        blocked_ambiguous: false,
        source_evidence_status: 'CONFIRMED_SOURCE_EVIDENCED',
        classification: 'CONFIRMED_SOURCE_EVIDENCED',
        schema_support: {
          schema_supported: true,
          extractor_output_supported: true,
          evaluator_supported: true,
        },
        ambiguity_reason: null,
        recommended_action: 'score_in_confirmed_metric_coverage',
        production_metric_tier: 'core',
        review_status: 'review_only_confirmed',
      },
      {
        fixture_id: 'anz_20250331_h',
        document_id: 'anz_20250331_h',
        fixture: 'ANZ_H_2025-03-31.json',
        ticker: 'ANZ',
        period: { period_type: 'H', period_end: '2025-03-31' },
        metric_name: 'shares_outstanding',
        canonical_field: 'shares_outstanding',
        expectation_type: 'value',
        expected_value: 3003366782,
        expected_null: false,
        currency: 'AUD',
        scale: 'millions',
        source_pdf_path: 'data/asx/docs/ANZ/report.pdf',
        source_pdf_exists: true,
        source_pdf_status: 'present',
        source_pdf_present: true,
        source_page: 44,
        source_page_present: true,
        source_table: null,
        source_table_present: false,
        source_row: 'The Company share capital comprises 3,003,366,782 fully paid shares',
        source_row_present: true,
        precise_source_evidence: true,
        broad_or_suspect_source_evidence: true,
        human_review_required: true,
        blocked_ambiguous: false,
        source_evidence_status: 'CANDIDATE_REVIEW_REQUIRED',
        classification: 'CANDIDATE_REVIEW_REQUIRED',
        schema_support: {
          schema_supported: true,
          extractor_output_supported: true,
          evaluator_supported: true,
        },
        ambiguity_reason: null,
        recommended_action: 'request_human_source_evidence_review',
        production_metric_tier: 'capital_structure',
        review_status: 'needs_human_review',
      },
      {
        fixture_id: 'dxs_20251231_h',
        document_id: 'dxs_20251231_h',
        fixture: 'DXS_H_2025-12-31.json',
        ticker: 'DXS',
        period: { period_type: 'H', period_end: '2025-12-31' },
        metric_name: 'net_debt',
        canonical_field: 'net_debt',
        expectation_type: 'value',
        expected_value: 4516700000,
        expected_null: false,
        currency: 'AUD',
        scale: 'millions',
        source_pdf_path: 'data/asx/docs/DXS/report.pdf',
        source_pdf_exists: true,
        source_pdf_status: 'present',
        source_pdf_present: true,
        source_page: 13,
        source_page_present: true,
        source_table: null,
        source_table_present: false,
        source_row: null,
        source_row_present: false,
        precise_source_evidence: false,
        broad_or_suspect_source_evidence: true,
        human_review_required: true,
        blocked_ambiguous: true,
        source_evidence_status: 'CONFIRMED_SOURCE_EVIDENCED',
        classification: 'AMBIGUOUS_OR_DERIVED',
        schema_support: {
          schema_supported: true,
          extractor_output_supported: true,
          evaluator_supported: true,
        },
        ambiguity_reason: 'net_debt_derivation_risk',
        recommended_action: 'exclude_or_mark_ambiguous_until_resolved',
        production_metric_tier: 'core',
        review_status: 'blocked_ambiguous',
      },
    ],
  }
}

function renderPanel(props: Partial<ComponentProps<typeof MetricCoverageTabPanel>> = {}) {
  return render(
    <MetricCoverageTabPanel
      packet={packet()}
      loading={false}
      running={false}
      error={null}
      onLoadLatest={vi.fn()}
      onRunReview={vi.fn()}
      onExportJson={vi.fn()}
      onExportMarkdown={vi.fn()}
      {...props}
    />,
  )
}

describe('MetricCoverageTabPanel', () => {
  it('renders summary counts, review-only copy, rows, and artifacts', () => {
    const { container } = renderPanel()

    expect(screen.getByText('Confirmed Metric Coverage Review')).toBeInTheDocument()
    expect(screen.getAllByText(/This review does not run extraction/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Candidate metrics require human source-evidence review/)).toBeInTheDocument()
    expect(screen.getAllByText(/Canonical trust semantics are unchanged/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Candidate rows are not confirmed/)).toBeInTheDocument()
    expect(screen.getByText(/git:/).parentElement).toHaveTextContent('adb76fac485e')
    expect(screen.getByText(/artifact_path:/).parentElement).toHaveTextContent('review_packet.json')
    expect(screen.getByText('146')).toBeInTheDocument()
    expect(screen.getByText('73')).toBeInTheDocument()
    expect(screen.getByText('70')).toBeInTheDocument()
    expect(screen.getAllByText(/review_packet\.json/).length).toBeGreaterThan(0)
    expect(screen.getByText('BHP_A_2021-06-30.json')).toBeInTheDocument()
    expect(screen.getByText('score_in_confirmed_metric_coverage')).toBeInTheDocument()
    expect(screen.getByText('Revenue 60,817')).toBeInTheDocument()
    expect(screen.getAllByText('precise evidence')).toHaveLength(2)
    expect(screen.getAllByText('broad/suspect')).toHaveLength(2)
    expect(screen.getAllByText('human review')).toHaveLength(2)
    expect(screen.getByText('blocked ambiguous')).toBeInTheDocument()
    expect(container.querySelectorAll('td.truncate')).toHaveLength(0)
    expect(screen.getByText('BHP_A_2021-06-30.json').closest('td')).toHaveClass('whitespace-normal')
    expect(screen.getAllByText('CONFIRMED_SOURCE_EVIDENCED')[0].closest('[data-slot="badge"]')).toHaveClass('whitespace-normal')
    expect(screen.getByText('score_in_confirmed_metric_coverage').closest('td')).toHaveClass('whitespace-normal')
  })

  it('calls the run and export actions', async () => {
    const user = userEvent.setup()
    const onRunReview = vi.fn()
    const onExportJson = vi.fn()
    const onExportMarkdown = vi.fn()
    renderPanel({ onRunReview, onExportJson, onExportMarkdown })

    await user.click(screen.getByRole('button', { name: /Refresh review/i }))
    await user.click(screen.getByRole('button', { name: /Export JSON/i }))
    await user.click(screen.getByRole('button', { name: /Export MD/i }))

    expect(onRunReview).toHaveBeenCalledTimes(1)
    expect(onExportJson).toHaveBeenCalledTimes(1)
    expect(onExportMarkdown).toHaveBeenCalledTimes(1)
  })

  it('filters rows by classification and search text', async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getAllByRole('combobox')[0])
    await user.click(screen.getByRole('option', { name: 'CANDIDATE_REVIEW_REQUIRED' }))
    await waitFor(() => expect(screen.queryByText('BHP_A_2021-06-30.json')).not.toBeInTheDocument())
    expect(screen.getByText('ANZ_H_2025-03-31.json')).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('BHP revenue page 44'), 'shares')
    expect(screen.getByText('shares_outstanding')).toBeInTheDocument()
    expect(screen.queryByText('net_debt')).not.toBeInTheDocument()
  })

  it('renders no-artifact and error states', () => {
    renderPanel({
      packet: null,
      error: 'backend unavailable',
    })

    expect(screen.getByText('not_generated')).toBeInTheDocument()
    expect(screen.getByText('backend unavailable')).toBeInTheDocument()
    expect(screen.getByText(/No confirmed metric coverage artifact has been generated yet/)).toBeInTheDocument()
  })

  it('renders explicit DATA_MISSING when git provenance is unavailable', () => {
    const missingGitPacket = packet()
    missingGitPacket.git_available = false
    missingGitPacket.git_head = null
    missingGitPacket.git_head_short = null
    missingGitPacket.git_branch = null
    missingGitPacket.git_dirty = null
    missingGitPacket.git_unavailable_reason = 'not a git repository'
    if (missingGitPacket.summary) {
      missingGitPacket.summary.git_available = false
      missingGitPacket.summary.git_head = null
      missingGitPacket.summary.git_head_short = null
      missingGitPacket.summary.git_branch = null
      missingGitPacket.summary.git_dirty = null
      missingGitPacket.summary.git_unavailable_reason = 'not a git repository'
    }

    renderPanel({ packet: missingGitPacket })

    expect(screen.getByText('git DATA_MISSING')).toBeInTheDocument()
    expect(screen.getByText(/DATA_MISSING: not a git repository/)).toBeInTheDocument()
  })
})
