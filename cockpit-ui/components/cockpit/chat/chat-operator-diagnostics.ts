import type { ChatMessage } from '@/lib/cockpit-types'
import { toReportDisplayPath } from '@/lib/report-path'

export type FeedbackKind = 'good' | 'poor'

export type FeedbackCaptureResponse = {
  report_id: string
  feedback_type: FeedbackKind
  capture_kind?: 'chat_feedback' | 'ui_issue' | 'auto_diagnostic'
  report_dir: string
  read_api_path?: string | null
  codex_prompt?: string | null
  codex_prompt_path?: string | null
  investigation_path?: string | null
  investigation_status?: string | null
  codex_cli_command?: string | null
  analysis_summary?: string | null
}

type CodexDeployMetadata = NonNullable<NonNullable<ChatMessage['metadata']>['codexDeploy']>

export function isOperatorDiagnosticsVisible(value = process.env.NEXT_PUBLIC_COCKPIT_OPERATOR_DIAGNOSTICS): boolean {
  return value === '1'
}

export function formatFlagHandoffMessage(
  result: FeedbackCaptureResponse,
  copiedPrompt: boolean,
  operatorDiagnosticsVisible = isOperatorDiagnosticsVisible(),
): string {
  if (!operatorDiagnosticsVisible) {
    return [
      'Potential issue captured for operator review.',
      '',
      'Evidence state: DATA_MISSING',
      'The last response could not be fully verified. Continue with a source-grounded follow-up or ask an operator to review diagnostics.',
    ].join('\n')
  }

  const reportPath = toReportDisplayPath(result.report_dir) || result.report_dir
  const promptPath = result.codex_prompt_path
    ? (toReportDisplayPath(result.codex_prompt_path) || result.codex_prompt_path)
    : null
  const investigationPath = result.investigation_path
    ? (toReportDisplayPath(result.investigation_path) || result.investigation_path)
    : null
  const status = result.investigation_status || 'queued'
  const lines = [
    'Potential issue detected.',
    '',
    `Report id: \`${result.report_id}\``,
    `Report: \`${reportPath}\``,
    `Status: \`${status}\``,
  ]
  if (promptPath) {
    lines.push(`Draft repair prompt: \`${promptPath}\``)
  }
  if (investigationPath) {
    lines.push(`Investigation packet: \`${investigationPath}\``)
  }
  if (result.read_api_path) {
    lines.push(`View diagnostic: \`${result.read_api_path}\``)
  }
  if (result.report_id) {
    lines.push('', 'Use the diagnostic controls below for operator-scoped repair work.')
  }
  const prompt = result.codex_prompt?.trim()
  if (prompt) {
    lines.push('', copiedPrompt ? 'Draft repair prompt copied to clipboard.' : 'Draft repair prompt saved to file.')
  }
  return lines.join('\n')
}

export function formatFeedbackSuccessToast(
  result: FeedbackCaptureResponse,
  feedbackType: FeedbackKind,
  copiedPrompt: boolean,
  operatorDiagnosticsVisible = isOperatorDiagnosticsVisible(),
): string {
  const summary = result.analysis_summary?.trim()

  if (!operatorDiagnosticsVisible) {
    if (feedbackType === 'good') {
      return summary
        ? `Good response saved for review: ${summary}`
        : 'Good response saved for review'
    }
    return summary
      ? `Flag saved for operator review: ${summary}`
      : 'Flag saved for operator review'
  }

  const reportPath = toReportDisplayPath(result.report_dir) || result.report_dir
  if (feedbackType === 'good') {
    return summary
      ? `Good response saved: ${summary}`
      : `Good response saved to ${reportPath}`
  }
  if (summary) {
    return copiedPrompt
      ? `Flag saved and Codex prompt copied: ${summary}`
      : `Flag saved: ${summary}`
  }
  return copiedPrompt
    ? `Flag saved and Codex prompt copied: ${reportPath}`
    : `Flag saved to ${reportPath}`
}

export function buildCodexDeployMetadata(
  result: FeedbackCaptureResponse,
  operatorDiagnosticsVisible = isOperatorDiagnosticsVisible(),
): CodexDeployMetadata | null {
  if (!operatorDiagnosticsVisible) {
    return null
  }

  return {
    reportId: result.report_id,
    reportPath: result.report_dir,
    readApiPath: result.read_api_path ?? null,
    promptPath: result.codex_prompt_path ?? null,
    investigationPath: result.investigation_path ?? null,
  }
}
