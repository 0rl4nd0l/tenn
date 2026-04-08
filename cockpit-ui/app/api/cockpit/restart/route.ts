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

export const runtime = 'nodejs'

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

export async function POST(): Promise<Response> {
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
