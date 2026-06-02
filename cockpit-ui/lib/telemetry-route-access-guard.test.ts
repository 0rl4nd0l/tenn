import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  execFile: vi.fn(),
  fetch: vi.fn(),
}))

vi.mock('node:child_process', () => ({
  default: {
    execFile: mocks.execFile,
  },
  execFile: mocks.execFile,
}))

function request(path: string, apiKey?: string): Request {
  return new Request(`http://localhost${path}`, {
    method: 'GET',
    headers: apiKey ? { 'X-API-Key': apiKey } : {},
  })
}

function mockExecFileSuccess(): void {
  mocks.execFile.mockImplementation((command, args, options, callback) => {
    const cb = typeof options === 'function' ? options : callback
    const argList = Array.isArray(args) ? args : []
    if (command === 'df') {
      cb(null, { stdout: 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/root 10485760 5242880 5242880 50% /\n', stderr: '' })
      return
    }
    if (command === 'ps' && argList.includes('-eo')) {
      cb(null, { stdout: '123 python 1.0 2.0 2048 python worker.py --api-key secret\n', stderr: '' })
      return
    }
    if (command === 'ps' && argList.includes('-o')) {
      cb(null, { stdout: '123 llama-server --port 8001 --api-key secret\n', stderr: '' })
      return
    }
    if (command === 'nvidia-smi' && argList.some((arg) => String(arg).includes('--query-gpu='))) {
      cb(null, { stdout: 'GPU-1, Tesla M40, 42, 15, 1024, 24576, 120, 250, 30, 4, 900, 1500, P0\n', stderr: '' })
      return
    }
    if (command === 'nvidia-smi' && argList.some((arg) => String(arg).includes('--query-compute-apps='))) {
      cb(null, { stdout: 'GPU-1, 123, llama-server, 2048\n', stderr: '' })
      return
    }
    cb(null, { stdout: '', stderr: '' })
  })
}

describe('Cockpit telemetry route access guard', () => {
  afterEach(() => {
    delete process.env.COCKPIT_API_KEY
    delete process.env.NEXT_PUBLIC_API_KEY
    vi.unstubAllGlobals()
    vi.clearAllMocks()
    vi.resetModules()
  })

  it('rejects host telemetry without API key before process probes', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    const { GET } = await import('@/app/api/cockpit/metrics/host/route')

    const response = await GET(request('/api/cockpit/metrics/host'))

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'cockpit_api_key_required',
    })
    expect(mocks.execFile).not.toHaveBeenCalled()
  })

  it('rejects GPU telemetry with wrong API key before nvidia-smi probes', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    const { GET } = await import('@/app/api/cockpit/metrics/gpu/route')

    const response = await GET(request('/api/cockpit/metrics/gpu', 'wrong-key'))

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'cockpit_api_key_required',
    })
    expect(mocks.execFile).not.toHaveBeenCalled()
  })

  it('rejects health telemetry before backend health reads or local probes', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    vi.stubGlobal('fetch', mocks.fetch)
    const { GET } = await import('@/app/api/cockpit/health/route')

    const response = await GET(request('/api/cockpit/health'))

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'cockpit_api_key_required',
    })
    expect(mocks.fetch).not.toHaveBeenCalled()
    expect(mocks.execFile).not.toHaveBeenCalled()
  })

  it('allows authenticated host telemetry and keeps commands redacted', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    mockExecFileSuccess()
    const { GET } = await import('@/app/api/cockpit/metrics/host/route')

    const response = await GET(request('/api/cockpit/metrics/host', 'operator-key'))
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.details.top_processes[0]).toMatchObject({
      pid: 123,
      command: 'python worker.py --api-key <redacted>',
    })
  })

  it('allows authenticated health telemetry and merges local diagnostics', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    mockExecFileSuccess()
    vi.stubGlobal('fetch', mocks.fetch)
    mocks.fetch
      .mockResolvedValueOnce(new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response('{"status":"healthy","services":[]}', { status: 200, headers: { 'content-type': 'application/json' } }))
    const { GET } = await import('@/app/api/cockpit/health/route')

    const response = await GET(request('/api/cockpit/health', 'operator-key'))
    const payload = await response.json()

    expect(response.status).toBe(200)
    expect(payload.services.map((service: { name: string }) => service.name)).toEqual(['gpu', 'host'])
  })
})
