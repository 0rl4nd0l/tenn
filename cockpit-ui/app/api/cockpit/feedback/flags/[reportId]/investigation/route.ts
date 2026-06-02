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
const remoteInvestigationReadTokenHeader = 'x-cockpit-control-token'

type InvestigationReadGuardResult =
  | { ok: true }
  | { ok: false; status: number; code: string; message: string }

function denyInvestigationRead(status: number, code: string, message: string): InvestigationReadGuardResult {
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

function hasRemoteInvestigationReadToken(request: Request): boolean {
  const allowRemote = String(process.env.COCKPIT_CODEX_INVESTIGATION_ALLOW_REMOTE || '').trim() === '1'
  const configuredToken = String(process.env.COCKPIT_CODEX_INVESTIGATION_TOKEN || '').trim()
  if (!allowRemote || !configuredToken) return false
  return request.headers.get(remoteInvestigationReadTokenHeader)?.trim() === configuredToken
}

function validateInvestigationReadRequest(request: Request): InvestigationReadGuardResult {
  const headerIntent = String(request.headers.get(investigationReadIntentHeader) || '').trim()
  if (headerIntent !== investigationReadIntent) {
    return denyInvestigationRead(
      403,
      'codex_investigation_read_intent_required',
      'Codex investigation reads require an explicit operator read intent header.',
    )
  }

  const hostname = requestHostname(request)
  if (!isLoopbackHostname(hostname) && !hasRemoteInvestigationReadToken(request)) {
    return denyInvestigationRead(
      403,
      'non_loopback_codex_investigation_read_denied',
      'Codex investigation reads are only allowed from loopback by default.',
    )
  }

  if (!sameOriginIfPresent(request)) {
    return denyInvestigationRead(
      403,
      'cross_origin_codex_investigation_read_denied',
      'Codex investigation reads must be same-origin.',
    )
  }

  const fetchSite = String(request.headers.get('sec-fetch-site') || '').trim().toLowerCase()
  if (fetchSite === 'cross-site') {
    return denyInvestigationRead(
      403,
      'cross_site_codex_investigation_read_denied',
      'Cross-site Codex investigation reads are not allowed.',
    )
  }

  return { ok: true }
}

export async function GET(
  request: Request,
  context: { params: Promise<{ reportId: string }> },
): Promise<Response> {
  const guard = validateInvestigationReadRequest(request)
  if (!guard.ok) {
    return Response.json(
      {
        ok: false,
        error: 'Codex investigation read denied',
        code: guard.code,
        detail: guard.message,
      },
      { status: guard.status },
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
