import { describe, expect, it } from 'vitest'

import {
  buildCodexDeployMetadata,
  formatFeedbackSuccessToast,
  formatFlagHandoffMessage,
  isOperatorDiagnosticsVisible,
  type FeedbackCaptureResponse,
} from './chat-operator-diagnostics'

const flaggedResponse: FeedbackCaptureResponse = {
  report_id: 'auto_20260526_065445_0015bf53',
  feedback_type: 'poor',
  capture_kind: 'auto_diagnostic',
  report_dir: '/home/l4nd0/tenn/reports/cockpit/flagged_sessions/auto_20260526_065445_0015bf53',
  read_api_path: '/api/cockpit/feedback/flags/auto_20260526_065445_0015bf53',
  codex_prompt: 'Investigate this flag.',
  codex_prompt_path: '/home/l4nd0/tenn/reports/cockpit/flagged_sessions/auto_20260526_065445_0015bf53/codex_prompt.md',
  investigation_path: '/home/l4nd0/tenn/reports/cockpit/flagged_sessions/auto_20260526_065445_0015bf53/investigation.json',
  investigation_status: 'queued',
  analysis_summary: 'Unsupported answer surfaced.',
}

describe('chat operator diagnostics visibility', () => {
  it('hides internal diagnostic paths and Codex deploy metadata in normal chat mode', () => {
    const message = formatFlagHandoffMessage(flaggedResponse, true, false)

    expect(message).toContain('Potential issue captured for operator review.')
    expect(message).toContain('Evidence state: DATA_MISSING')
    expect(message).not.toContain(flaggedResponse.report_id)
    expect(message).not.toContain('reports/cockpit/flagged_sessions')
    expect(message).not.toContain('/api/cockpit/feedback/flags')
    expect(message).not.toContain('Draft repair prompt')
    expect(message).not.toContain('Investigation packet')
    expect(message).not.toContain('View diagnostic')
    expect(buildCodexDeployMetadata(flaggedResponse, false)).toBeNull()
  })

  it('preserves operator diagnostic handoff details when operator mode is explicit', () => {
    const message = formatFlagHandoffMessage(flaggedResponse, true, true)
    const metadata = buildCodexDeployMetadata(flaggedResponse, true)

    expect(message).toContain('Potential issue detected.')
    expect(message).toContain('Report id: `auto_20260526_065445_0015bf53`')
    expect(message).toContain('Draft repair prompt:')
    expect(message).toContain('Investigation packet:')
    expect(message).toContain('View diagnostic:')
    expect(metadata).toMatchObject({
      reportId: 'auto_20260526_065445_0015bf53',
      readApiPath: '/api/cockpit/feedback/flags/auto_20260526_065445_0015bf53',
    })
  })

  it('defaults operator diagnostics to hidden unless the explicit env flag is set', () => {
    expect(isOperatorDiagnosticsVisible(undefined)).toBe(false)
    expect(isOperatorDiagnosticsVisible('0')).toBe(false)
    expect(isOperatorDiagnosticsVisible('1')).toBe(true)
  })

  it('keeps normal feedback success toasts free of internal report paths', () => {
    const goodToast = formatFeedbackSuccessToast(flaggedResponse, 'good', false, false)
    const flagToast = formatFeedbackSuccessToast(flaggedResponse, 'poor', false, false)

    expect(goodToast).toContain('Good response saved for review')
    expect(flagToast).toContain('Flag saved for operator review')
    expect(goodToast).not.toContain(flaggedResponse.report_id)
    expect(goodToast).not.toContain('reports/cockpit/flagged_sessions')
    expect(flagToast).not.toContain(flaggedResponse.report_id)
    expect(flagToast).not.toContain('reports/cockpit/flagged_sessions')
  })

  it('preserves operator feedback artifact paths when operator mode is explicit', () => {
    const responseWithoutSummary = {
      ...flaggedResponse,
      analysis_summary: null,
    }

    expect(formatFeedbackSuccessToast(responseWithoutSummary, 'good', false, true))
      .toContain('reports/cockpit/flagged_sessions/auto_20260526_065445_0015bf53')
    expect(formatFeedbackSuccessToast(responseWithoutSummary, 'poor', true, true))
      .toContain('Flag saved and Codex prompt copied: reports/cockpit/flagged_sessions/auto_20260526_065445_0015bf53')
  })
})
