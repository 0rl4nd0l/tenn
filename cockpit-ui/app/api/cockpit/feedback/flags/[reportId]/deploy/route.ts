import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import path from 'node:path'

import {
  readInvestigation,
  resolveInvestigationPaths,
  validateReportId,
} from '@/lib/codex-investigation'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(
  _request: Request,
  context: { params: Promise<{ reportId: string }> },
): Promise<Response> {
  try {
    const { reportId } = await context.params
    const normalizedReportId = validateReportId(reportId)
    const paths = resolveInvestigationPaths(normalizedReportId)
    const investigation = readInvestigation(paths.reportDir)
    const status = String(investigation.status || '').trim() || 'unknown'
    const lockPath = path.resolve(paths.reportDir, 'investigation.lock')

    if (status === 'running' || existsSync(lockPath)) {
      return Response.json({
        ok: true,
        report_id: normalizedReportId,
        status: 'running',
        investigation_path: paths.investigationPath,
      })
    }
    if (status === 'completed') {
      return Response.json({
        ok: true,
        report_id: normalizedReportId,
        status,
        investigation_path: paths.investigationPath,
      })
    }
    if (status !== 'queued') {
      return Response.json(
        {
          ok: false,
          report_id: normalizedReportId,
          status,
          error: `Codex investigation is not queued (${status})`,
        },
        { status: 409 },
      )
    }

    const launcherLogPath = path.resolve(paths.reportDir, 'codex-launcher.log')
    const pythonBin = process.env.COCKPIT_CODEX_RUNNER_PYTHON || 'python3'
    const args = [
      'scripts/cockpit_flag_investigator.py',
      '--root',
      paths.reportsRoot,
      '--report-id',
      normalizedReportId,
      '--once',
      '--apply',
    ]
    appendFileSync(
      launcherLogPath,
      `[${new Date().toISOString()}] launching: ${pythonBin} ${args.join(' ')}\n`,
      'utf8',
    )
    const child = spawn(pythonBin, args, {
      cwd: paths.repoRoot,
      detached: true,
      stdio: 'ignore',
      env: {
        ...process.env,
        COCKPIT_WORKSPACE_ROOT: process.env.COCKPIT_WORKSPACE_ROOT || paths.repoRoot,
      },
    })
    child.once('error', (error) => {
      appendFileSync(
        launcherLogPath,
        `[${new Date().toISOString()}] spawn error: ${error.message}\n`,
        'utf8',
      )
      try {
        const current = JSON.parse(readFileSync(paths.investigationPath, 'utf8')) as Record<string, unknown>
        writeFileSync(
          paths.investigationPath,
          JSON.stringify({
            ...current,
            status: 'failed',
            updated_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
            launcher_error: error.message,
          }, null, 2) + '\n',
          'utf8',
        )
      } catch {
        // The launcher log above is the fallback failure record.
      }
    })
    child.unref()

    return Response.json(
      {
        ok: true,
        report_id: normalizedReportId,
        status: 'launching',
        pid: child.pid ?? null,
        investigation_path: paths.investigationPath,
        launcher_log_path: launcherLogPath,
      },
      { status: 202 },
    )
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
