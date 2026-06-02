import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ThesisAuditScreen } from './thesis-audit-screen'
import {
  createUserThesisProposal,
  getThesisAuditCoverage,
  listThesisWatchdogAlerts,
  runThesisAudit,
  updateThesisWatchdogAlertStatus,
} from '@/lib/api-client'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/lib/api-client', () => ({
  createUserThesisProposal: vi.fn(),
  getThesisAuditCoverage: vi.fn(),
  listThesisWatchdogAlerts: vi.fn(),
  runThesisAudit: vi.fn(),
  updateThesisWatchdogAlertStatus: vi.fn(),
}))

const createUserThesisProposalMock = vi.mocked(createUserThesisProposal)
const getThesisAuditCoverageMock = vi.mocked(getThesisAuditCoverage)
const listThesisWatchdogAlertsMock = vi.mocked(listThesisWatchdogAlerts)
const runThesisAuditMock = vi.mocked(runThesisAudit)
const updateThesisWatchdogAlertStatusMock = vi.mocked(updateThesisWatchdogAlertStatus)

const watchdogAlert = {
  alert_id: 'alert-1',
  entry_id: 1,
  ticker: 'BHP',
  severity: 'contradict' as const,
  status: 'unread' as const,
  finding: 'New filing contradicts the thesis.',
  evidence_source_id: 'source-1',
  created_at: '2026-06-02T07:00:00Z',
  metadata: {
    excerpt: 'New filing excerpt',
  },
}

function renderThesisAudit() {
  return render(<ThesisAuditScreen apiKey="test-key" />)
}

describe('ThesisAuditScreen accessible controls', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    getThesisAuditCoverageMock.mockResolvedValue({
      ticker: 'BHP',
      generated_at: '2026-06-02T07:30:00Z',
      evidence_summary: {
        coverage_status: 'ready',
        coverage_message: 'Backend evidence coverage is sufficient for a thesis audit.',
        sufficient_for_analysis: true,
        evidence_span_count: 2,
        missing_categories_after_recovery: [],
        memory_read_only: true,
        proposal_gate: {
          allowed: true,
          reason: null,
          message: null,
        },
      },
      guardrails: {},
    })
    listThesisWatchdogAlertsMock.mockResolvedValue({
      ok: true,
      alerts: [],
    })
    updateThesisWatchdogAlertStatusMock.mockResolvedValue({ ok: true, alert: watchdogAlert })
    createUserThesisProposalMock.mockResolvedValue({ ok: true, proposal: {} })
  })

  it('labels the primary thesis audit inputs and action controls', async () => {
    renderThesisAudit()

    await userEvent.type(screen.getByRole('textbox', { name: /ticker for thesis audit/i }), 'bhp')
    await userEvent.type(screen.getByRole('textbox', { name: /thesis audit focus/i }), 'moat')
    await userEvent.type(screen.getByRole('textbox', { name: /paste thesis report text/i }), 'Long BHP thesis.')

    expect(screen.getByLabelText(/upload thesis source report/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /refresh thesis coverage/i })).toBeInTheDocument()
    await waitFor(() => {
      expect(getThesisAuditCoverageMock).toHaveBeenCalledWith('BHP', 'test-key')
    })
  })

  it('labels generated proposal stage controls with a durable action name', async () => {
    runThesisAuditMock.mockResolvedValue({
      audit_id: 'audit-1',
      ticker: 'BHP',
      generated_at: '2026-06-02T07:30:00Z',
      thesis_summary: 'BHP has a resilient iron ore thesis.',
      report_source: {
        source_role: 'operator_report',
      },
      claims: [],
      verification_matrix: [],
      strongest_disconfirming_evidence: [],
      contrarian_findings: [],
      hidden_assumptions: [],
      change_my_mind_triggers: [],
      next_diligence_questions: [],
      report_to_reality_delta: null,
      user_thesis_memory_proposals: [
        {
          proposal_type: 'add_evidence',
          statement: 'Iron ore cash generation remains central to the thesis.',
          signal: null,
          confidence: 0.8,
          metadata: {},
        },
      ],
      evidence_summary: {
        coverage_status: 'ready',
        coverage_message: 'Backend evidence coverage is sufficient for a thesis audit.',
        sufficient_for_analysis: true,
        evidence_span_count: 2,
        missing_categories_after_recovery: [],
        memory_read_only: true,
        proposal_gate: {
          allowed: true,
          reason: null,
          message: null,
        },
      },
      guardrails: {
        user_thesis_memory_auto_saved: false,
      },
    })

    renderThesisAudit()

    await userEvent.type(screen.getByRole('textbox', { name: /ticker for thesis audit/i }), 'bhp')
    await userEvent.type(screen.getByRole('textbox', { name: /paste thesis report text/i }), 'Long BHP thesis.')
    await userEvent.click(screen.getByRole('button', { name: /^audit$/i }))
    await userEvent.click(await screen.findByRole('tab', { name: /proposals/i }))
    await userEvent.click(screen.getByRole('button', { name: /stage thesis memory proposal 1/i }))

    expect(createUserThesisProposalMock).toHaveBeenCalledWith(
      expect.objectContaining({
        ticker: 'BHP',
        statement: 'Iron ore cash generation remains central to the thesis.',
      }),
      'test-key',
    )
  })

  it('labels history deletion and watchdog dismissal controls with target context', async () => {
    window.localStorage.setItem(
      'thesis_audit_history',
      JSON.stringify([
        {
          audit_id: 'audit-old-1',
          ticker: 'BHP',
          filename: 'bhp-thesis.md',
          focus: null,
          generated_at: '2026-06-02T07:00:00Z',
          thesis_summary: 'Old thesis.',
          report: {},
          reportText: 'Old thesis.',
          uploadedReport: null,
        },
      ]),
    )
    listThesisWatchdogAlertsMock.mockResolvedValue({
      ok: true,
      alerts: [watchdogAlert],
    })

    renderThesisAudit()

    await userEvent.click(
      await screen.findByRole('button', {
        name: /remove thesis audit history BHP bhp-thesis\.md/i,
      }),
    )
    expect(screen.queryByText('bhp-thesis.md')).not.toBeInTheDocument()

    await userEvent.type(screen.getByRole('textbox', { name: /ticker for thesis audit/i }), 'bhp')
    await userEvent.click(
      await screen.findByRole('button', {
        name: /dismiss thesis watchdog alert alert-1/i,
      }),
    )

    expect(updateThesisWatchdogAlertStatusMock).toHaveBeenCalledWith('alert-1', 'dismissed', 'test-key')
  })
})
