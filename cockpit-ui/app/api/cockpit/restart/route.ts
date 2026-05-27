import { execFile, spawn } from 'node:child_process'
import { access } from 'node:fs/promises'
import path from 'node:path'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)
const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const healthUrl = `${backendUrl}/api/health`
const repoRoot = path.resolve(process.cwd(), '..')
const backendRoot = path.join(repoRoot, 'financial-engine_v2')
const restartScript = path.join(backendRoot, 'scripts', 'run_local_backend.sh')
const localVenvBin = path.join(backendRoot, '.venv', 'bin')
const restartTimeoutMs = 30_000
const restartIntent = 'restart-backend'
const restartConfirmation = 'RESTART BACKEND'
const restartIntentHeader = 'x-cockpit-restart-intent'
const remoteRestartTokenHeader = 'x-cockpit-restart-token'

export const runtime = 'nodejs'

type RestartGuardResult =
  | { ok: true }
  | { ok: false; status: number; code: string; message: string }

function denyRestart(status: number, code: string, message: string): RestartGuardResult {
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

function hasRemoteRestartToken(request: Request): boolean {
  const allowRemote = String(process.env.COCKPIT_RESTART_ALLOW_REMOTE || '').trim() === '1'
  const configuredToken = String(process.env.COCKPIT_RESTART_TOKEN || '').trim()
  if (!allowRemote || !configuredToken) return false
  return request.headers.get(remoteRestartTokenHeader)?.trim() === configuredToken
}

async function validateRestartRequest(request: Request): Promise<RestartGuardResult> {
  const hostname = requestHostname(request)
  if (!isLoopbackHostname(hostname) && !hasRemoteRestartToken(request)) {
    return denyRestart(
      403,
      'non_loopback_restart_denied',
      'Backend restart is only allowed from loopback by default.',
    )
  }

  if (!sameOriginIfPresent(request)) {
    return denyRestart(
      403,
      'cross_origin_restart_denied',
      'Backend restart requests must be same-origin.',
    )
  }

  const fetchSite = String(request.headers.get('sec-fetch-site') || '').trim().toLowerCase()
  if (fetchSite === 'cross-site') {
    return denyRestart(
      403,
      'cross_site_restart_denied',
      'Cross-site backend restart requests are not allowed.',
    )
  }

  const contentType = String(request.headers.get('content-type') || '').toLowerCase()
  if (!contentType.includes('application/json')) {
    return denyRestart(
      415,
      'restart_json_required',
      'Backend restart requests must use application/json.',
    )
  }

  const headerIntent = String(request.headers.get(restartIntentHeader) || '').trim()
  if (headerIntent !== restartIntent) {
    return denyRestart(
      403,
      'restart_intent_header_required',
      'Backend restart requests must include an explicit restart intent header.',
    )
  }

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return denyRestart(
      400,
      'restart_json_invalid',
      'Backend restart request body must be valid JSON.',
    )
  }

  const payload = body && typeof body === 'object' ? (body as Record<string, unknown>) : {}
  if (payload.intent !== restartIntent || payload.confirmation !== restartConfirmation) {
    return denyRestart(
      403,
      'restart_confirmation_required',
      'Backend restart requests must include the explicit restart confirmation.',
    )
  }

  return { ok: true }
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForHealth(timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const response = await fetch(healthUrl, { cache: 'no-store' })
      if (response.ok) return true
    } catch {
      // Expected while backend is restarting.
    }
    await sleep(1000)
  }
  return false
}

async function listBackendPids(): Promise<string[]> {
  try {
    const { stdout } = await execFileAsync('pgrep', ['-f', 'uvicorn app.main:app'])
    return stdout
      .split(/\s+/)
      .map((value) => value.trim())
      .filter(Boolean)
  } catch (error: unknown) {
    const code = typeof error === 'object' && error !== null && 'code' in error ? error.code : undefined
    if (code === 1) return []
    throw error
  }
}

async function stopBackend(): Promise<{ stopped: boolean; pid?: string }> {
  const pids = await listBackendPids()
  if (pids.length === 0) return { stopped: false }

  const pid = pids[0]
  await execFileAsync('kill', [pid])

  const deadline = Date.now() + 10_000
  while (Date.now() < deadline) {
    const remaining = await listBackendPids()
    if (!remaining.includes(pid)) {
      return { stopped: true, pid }
    }
    await sleep(300)
  }

  throw new Error(`backend pid ${pid} did not exit within 10s`)
}

function startBackend(): void {
  const env = { ...process.env }
  env.LOCAL_BACKEND_PROFILE = env.LOCAL_BACKEND_PROFILE || 'isolated'
  env.PATH = `${localVenvBin}:${env.PATH || ''}`

  const child = spawn('bash', [restartScript], {
    cwd: backendRoot,
    detached: true,
    env,
    stdio: 'ignore',
  })
  child.unref()
}

export async function POST(request: Request): Promise<Response> {
  const guard = await validateRestartRequest(request)
  if (!guard.ok) {
    return Response.json(
      {
        ok: false,
        error: 'Backend restart denied',
        code: guard.code,
        detail: guard.message,
      },
      { status: guard.status },
    )
  }

  try {
    await access(restartScript)
  } catch {
    return Response.json(
      { ok: false, error: `restart script not found: ${restartScript}` },
      { status: 500 },
    )
  }

  try {
    const stopResult = await stopBackend()
    startBackend()
    const healthy = await waitForHealth(restartTimeoutMs)
    if (!healthy) {
      return Response.json(
        {
          ok: false,
          message: 'Backend restart launched but health check did not recover within 30s.',
          stopped: stopResult.stopped,
          pid: stopResult.pid || null,
        },
        { status: 504 },
      )
    }

    return Response.json({
      ok: true,
      message: stopResult.stopped
        ? `Backend restarted successfully (previous pid ${stopResult.pid}).`
        : 'Backend started successfully.',
      stopped: stopResult.stopped,
      pid: stopResult.pid || null,
    })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Backend restart failed'
    return Response.json({ ok: false, error: message }, { status: 500 })
  }
}
