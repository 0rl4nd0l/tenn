import path from 'node:path'

import {
  readInvestigation,
  readTail,
  resolveInvestigationPaths,
  validateReportId,
} from '@/lib/codex-investigation'

export const runtime = 'nodejs'
export const maxDuration = 30

const investigationReadIntent = 'read-codex-investigation'
const investigationReadIntentHeader = 'x-cockpit-control-intent'

export async function GET(
  request: Request,
  context: { params: Promise<{ reportId: string }> },
): Promise<Response> {
  const headerIntent = String(request.headers.get(investigationReadIntentHeader) || '').trim()
  if (headerIntent !== investigationReadIntent) {
    return Response.json(
      {
        ok: false,
        error: 'Codex investigation read denied',
        code: 'codex_investigation_read_intent_required',
        detail: 'Codex investigation reads require an explicit operator read intent header.',
      },
      { status: 403 },
    )
  }

  try {
    const { reportId } = await context.params
    const normalizedReportId = validateReportId(reportId)
    const paths = resolveInvestigationPaths(normalizedReportId)
    const investigation = readInvestigation(paths.reportDir)
    const outputPath = String(investigation.codex_output_path || path.resolve(paths.reportDir, 'codex-last-message.md'))
    const stderrPath = String(investigation.codex_stderr_path || path.resolve(paths.reportDir, 'codex-stderr.log'))
    const launcherLogPath = path.resolve(paths.reportDir, 'codex-launcher.log')

    return Response.json({
      ok: true,
      report_id: normalizedReportId,
      status: String(investigation.status || 'unknown'),
      investigation_path: paths.investigationPath,
      prompt_path: paths.promptPath,
      output_path: outputPath,
      stderr_path: stderrPath,
      launcher_log_path: launcherLogPath,
      returncode: investigation.returncode ?? null,
      started_at: investigation.started_at ?? null,
      completed_at: investigation.completed_at ?? null,
      updated_at: investigation.updated_at ?? null,
      output_tail: readTail(outputPath),
      stderr_tail: readTail(stderrPath),
      launcher_log_tail: readTail(launcherLogPath),
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    const status = /Invalid report_id/.test(message) ? 400 : /not found|Missing/i.test(message) ? 404 : 500
    return Response.json(
      {
        ok: false,
        error: message,
      },
      { status },
    )
  }
}
