import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  access: vi.fn(),
  execFile: vi.fn(),
  fetch: vi.fn(),
  spawn: vi.fn(),
  unref: vi.fn(),
}))

vi.mock('node:fs/promises', () => ({
  default: {
    access: mocks.access,
  },
  access: mocks.access,
}))

vi.mock('node:child_process', () => ({
  default: {
    execFile: mocks.execFile,
    spawn: mocks.spawn,
  },
  execFile: mocks.execFile,
  spawn: mocks.spawn,
}))

import { POST as postRestartRoute } from '@/app/api/cockpit/restart/route'

function restartRequest(
  url = 'http://localhost/api/cockpit/restart',
  headers: Record<string, string> = {},
  body: Record<string, string> = {
    intent: 'restart-backend',
    confirmation: 'RESTART BACKEND',
  },
): Request {
  return new Request(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Cockpit-Restart-Intent': 'restart-backend',
      ...headers,
    },
    body: JSON.stringify(body),
  })
}

describe('Cockpit restart route guard', () => {
  afterEach(() => {
    delete process.env.COCKPIT_RESTART_ALLOW_REMOTE
    delete process.env.COCKPIT_RESTART_TOKEN
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('rejects missing explicit restart intent before process operations', async () => {
    const response = await postRestartRoute(
      restartRequest('http://localhost/api/cockpit/restart', {
        'X-Cockpit-Restart-Intent': '',
      }),
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'restart_intent_header_required',
    })
    expect(mocks.access).not.toHaveBeenCalled()
    expect(mocks.execFile).not.toHaveBeenCalled()
    expect(mocks.spawn).not.toHaveBeenCalled()
  })

  it('rejects non-loopback requests by default before process operations', async () => {
    const response = await postRestartRoute(
      restartRequest('http://192.168.1.10/api/cockpit/restart', {
        host: '192.168.1.10',
      }),
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'non_loopback_restart_denied',
    })
    expect(mocks.access).not.toHaveBeenCalled()
    expect(mocks.execFile).not.toHaveBeenCalled()
    expect(mocks.spawn).not.toHaveBeenCalled()
  })

  it('rejects cross-origin browser requests before process operations', async () => {
    const response = await postRestartRoute(
      restartRequest('http://localhost/api/cockpit/restart', {
        origin: 'https://example.invalid',
        'sec-fetch-site': 'cross-site',
      }),
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'cross_origin_restart_denied',
    })
    expect(mocks.access).not.toHaveBeenCalled()
    expect(mocks.execFile).not.toHaveBeenCalled()
    expect(mocks.spawn).not.toHaveBeenCalled()
  })

  it('allows an explicit same-origin loopback restart request', async () => {
    mocks.access.mockResolvedValue(undefined)
    mocks.execFile
      .mockImplementationOnce((_cmd, _args, callback) => callback(null, { stdout: '12345\n', stderr: '' }))
      .mockImplementationOnce((_cmd, _args, callback) => callback(null, { stdout: '', stderr: '' }))
      .mockImplementationOnce((_cmd, _args, callback) => {
        const error = Object.assign(new Error('no process'), { code: 1 })
        callback(error, '', '')
      })
    mocks.spawn.mockReturnValue({ unref: mocks.unref })
    vi.stubGlobal('fetch', mocks.fetch.mockResolvedValue(new Response('{}', { status: 200 })))

    const response = await postRestartRoute(
      restartRequest('http://localhost/api/cockpit/restart', {
        origin: 'http://localhost',
        'sec-fetch-site': 'same-origin',
      }),
    )

    const payload = await response.json()
    expect({ status: response.status, payload }).toMatchObject({
      status: 200,
      payload: {
      ok: true,
      stopped: true,
      pid: '12345',
      },
    })
    expect(mocks.execFile).toHaveBeenCalledWith('kill', ['12345'], expect.any(Function))
    expect(mocks.spawn).toHaveBeenCalled()
  })

  it('allows non-loopback only with explicit remote opt-in token', async () => {
    process.env.COCKPIT_RESTART_ALLOW_REMOTE = '1'
    process.env.COCKPIT_RESTART_TOKEN = 'operator-token'
    mocks.access.mockResolvedValue(undefined)
    mocks.execFile.mockImplementationOnce((_cmd, _args, callback) => {
      const error = Object.assign(new Error('no process'), { code: 1 })
      callback(error, '', '')
    })
    mocks.spawn.mockReturnValue({ unref: mocks.unref })
    vi.stubGlobal('fetch', mocks.fetch.mockResolvedValue(new Response('{}', { status: 200 })))

    const response = await postRestartRoute(
      restartRequest('http://192.168.1.10/api/cockpit/restart', {
        host: '192.168.1.10',
        origin: 'http://192.168.1.10',
        'X-Cockpit-Restart-Token': 'operator-token',
      }),
    )

    const payload = await response.json()
    expect({ status: response.status, payload }).toMatchObject({
      status: 200,
      payload: {
      ok: true,
      stopped: false,
      },
    })
    expect(mocks.spawn).toHaveBeenCalled()
  })
})
