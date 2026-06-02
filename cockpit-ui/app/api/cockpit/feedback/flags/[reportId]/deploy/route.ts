import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import path from 'node:path'

import {
  readInvestigation,
  resolveInvestigationPaths,
  validateReportId,
} from '@/lib/codex-investigation'
import { resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

const investigationDeployIntent = 'deploy-codex-investigation'
const investigationDeployIntentHeader = 'x-cockpit-control-intent'

type InvestigationDeployGuardResult =
  | { ok: true }
  | { ok: false; status: number; code: string; message: string }

function denyInvestigationDeploy(status: number, code: string, message: string): InvestigationDeployGuardResult {
  return { ok: false, status, code, message }
}

function normalizeHostname(value: string | null): string {
  const raw = String(value || '').trim().toLowerCase()
  if (!raw) return ''
  if (raw.startsWith('[')) {
    const end = raw.indexOf(']')
    return end > 0 ? raw.slice(1, end) : raw
  }
  if (raw === '::1' || raw.includes('::')) return raw
  return raw.split(':')[0] || raw
}

function requestHostname(request: Request): string {
  const hostHeader = request.headers.get('host')
  if (hostHeader) return normalizeHostname(hostHeader)
  try {
    return normalizeHostname(new URL(request.url).hostname)
  } catch {
    return ''
  }
}

function isLoopbackHostname(hostname: string): boolean {
  const normalized = normalizeHostname(hostname)
  return normalized === 'localhost' || normalized === '::1' || normalized.startsWith('127.')
}

function requestOrigin(request: Request): string | null {
  try {
    return new URL(request.url).origin
  } catch {
    return null
  }
}

function sameOriginIfPresent(request: Request): boolean {
  const origin = request.headers.get('origin')
  if (!origin) return true
  const expectedOrigin = requestOrigin(request)
  if (!expectedOrigin) return false
  try {
    return new URL(origin).origin === expectedOrigin
  } catch {
    return false
  }
}

function validateInvestigationDeployRequest(request: Request): InvestigationDeployGuardResult {
  const headerIntent = String(request.headers.get(investigationDeployIntentHeader) || '').trim()
  if (headerIntent !== investigationDeployIntent) {
    return denyInvestigationDeploy(
      403,
      'codex_investigation_deploy_intent_required',
      'Codex investigation deploys require an explicit operator deploy intent header.',
    )
  }

  if (!isLoopbackHostname(requestHostname(request))) {
    return denyInvestigationDeploy(
      403,
      'non_loopback_codex_investigation_deploy_denied',
      'Codex investigation deploys are only allowed from loopback.',
    )
  }

  if (!sameOriginIfPresent(request)) {
    return denyInvestigationDeploy(
      403,
      'cross_origin_codex_investigation_deploy_denied',
      'Codex investigation deploys must be same-origin.',
    )
  }

  const fetchSite = String(request.headers.get('sec-fetch-site') || '').trim().toLowerCase()
  if (fetchSite === 'cross-site') {
    return denyInvestigationDeploy(
      403,
      'cross_site_codex_investigation_deploy_denied',
      'Cross-site Codex investigation deploys are not allowed.',
    )
  }

  return { ok: true }
}

async function refreshBackendFlagPacket(reportId: string): Promise<void> {
  try {
    await fetch(`${resolveBackendUrl()}/api/cockpit/feedback/flags/${encodeURIComponent(reportId)}`, {
      cache: 'no-store',
    })
  } catch {
    // The local report packet is still the source for launching; this refresh
    // only lets the backend repair root-owned packets when it is available.
  }
}

export async function POST(
  request: Request,
  context: { params: Promise<{ reportId: string }> },
): Promise<Response> {
  const guard = validateInvestigationDeployRequest(request)
  if (!guard.ok) {
    return Response.json(
      {
        ok: false,
        error: 'Codex investigation deploy denied',
        code: guard.code,
        detail: guard.message,
      },
      { status: guard.status },
    )
  }

  try {
    const { reportId } = await context.params
    const normalizedReportId = validateReportId(reportId)
    await refreshBackendFlagPacket(normalizedReportId)
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
    const retryFailed = status === 'failed' || status === 'error'
    if (status !== 'queued' && !retryFailed) {
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
    const runnerScriptPath = path.resolve(paths.repoRoot, 'scripts', 'cockpit_flag_investigator.py')
    const args = [
      runnerScriptPath,
      '--root',
      paths.reportsRoot,
      '--report-id',
      normalizedReportId,
      '--once',
      '--apply',
    ]
    if (retryFailed) {
      args.push('--force')
    }
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
    const errorMessage = /EACCES|permission denied/i.test(message)
      ? `${message}. The flagged report packet is not writable by the Cockpit UI process; open the flag read API after the backend permission fix is deployed, or repair ownership with chown.`
      : message
    return Response.json(
      {
        ok: false,
        error: errorMessage,
      },
      { status },
    )
  }
}
