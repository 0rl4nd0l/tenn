import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

type Listener = (event: { data?: string }) => void

const eventOrder: string[] = []
const instances: MockSSE[] = []

class MockSSE {
  url: string
  options: Record<string, unknown>
  listeners = new Map<string, Listener[]>()
  stream = vi.fn(() => {
    eventOrder.push('stream')
  })
  close = vi.fn()

  constructor(url: string, options: Record<string, unknown>) {
    this.url = url
    this.options = options
    instances.push(this)
  }

  addEventListener(type: string, listener: Listener) {
    eventOrder.push(`listen:${type}`)
    const listeners = this.listeners.get(type) ?? []
    listeners.push(listener)
    this.listeners.set(type, listeners)
  }

  emit(type: string, event: { data?: string }) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event)
    }
  }
}

vi.mock('sse.js', () => ({
  SSE: MockSSE,
}))

import { streamChat } from './api-client'

describe('streamChat', () => {
  beforeEach(() => {
    eventOrder.length = 0
    instances.length = 0
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('disables auto-start so listeners are attached before streaming begins', async () => {
    const onMessage = vi.fn()
    const onError = vi.fn()
    const onEnd = vi.fn()

    const source = await streamChat({
      message: 'hello',
      mode: 'analysis',
      onMessage,
      onError,
      onEnd,
    })

    const instance = instances.at(0)
    expect(instance).toBeDefined()
    expect(instance?.options.start).toBe(false)
    expect(instance?.url).toBe('/api/cockpit/chat')
    expect(eventOrder).toEqual([
      'listen:message',
      'listen:error',
      'listen:end',
      'stream',
    ])
    expect(instance?.stream).toHaveBeenCalledTimes(1)
    expect(source).toBe(instance)
  })

  it('parses message payloads and forwards end/error events', async () => {
    const onMessage = vi.fn()
    const onError = vi.fn()
    const onEnd = vi.fn()

    await streamChat({
      message: 'hello',
      mode: 'analysis',
      onMessage,
      onError,
      onEnd,
    })

    const instance = instances[0]
    instance.emit('message', {
      data: JSON.stringify({ type: 'status', data: { stage: 'Request accepted' } }),
    })
    instance.emit('end', {})
    instance.emit('error', { data: 'Connection lost' })

    expect(onMessage).toHaveBeenCalledWith({
      type: 'status',
      data: { stage: 'Request accepted' },
    })
    expect(onEnd).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith({ data: 'Connection lost' })
    expect(instance.close).toHaveBeenCalledTimes(2)
  })
})

describe('listDocuments', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('sends the configured API key when listing documents', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { listDocuments } = await import('./api-client')

    await listDocuments()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/docs',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-API-Key': 'local-secret',
        }),
      }),
    )
  })
})

describe('Intel Ops API client', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('sends the configured API key when fetching Intel Pulse', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ stats: {}, pipeline: [], failures: [] }), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { getIntelPulse } = await import('./api-client')

    await getIntelPulse('bhp')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/pulse?ticker=BHP',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-API-Key': 'local-secret',
        }),
      }),
    )
  })

  it('sends the configured API key when fetching the diagnostic matrix', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ stage: 'extraction', entities: [] }), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { getDiagnosticMatrix } = await import('./api-client')

    await getDiagnosticMatrix('extraction', 'bhp')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/matrix?stage=extraction&ticker=BHP',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-API-Key': 'local-secret',
        }),
      }),
    )
  })

  it('prefers the browser-stored cockpit API key over the env key', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'env-secret')
    window.localStorage.setItem('cockpit.apiKey', 'stored-secret')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ stats: {}, pipeline: [], failures: [] }), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { getIntelPulse } = await import('./api-client')

    await getIntelPulse('bhp')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/pulse?ticker=BHP',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-API-Key': 'stored-secret',
        }),
      }),
    )
  })
})

describe('extraction review API client', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.resetModules()
  })

  it('sends the API key for guarded extraction review read routes', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    vi.resetModules()
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      items: [],
      session_id: 'session-1',
      run_id: 'run-1',
      events: [],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    const {
      getExtractionReviewErrors,
      getExtractionReviewRuns,
      getExtractionReviewRunStatus,
      getExtractionReviewSessions,
      getExtractionReviewSession,
    } = await import('./api-client')

    await getExtractionReviewRuns('bhp', 20)
    await getExtractionReviewSessions('bhp', 20)
    await getExtractionReviewSession('session-1')
    await getExtractionReviewErrors(25)
    await getExtractionReviewRunStatus('run-1', 30)

    expect(fetchMock).toHaveBeenCalledTimes(5)
    const expectedPaths = [
      '/api/extraction-review/runs?limit=20&ticker=BHP',
      '/api/extraction-review/sessions?limit=20&ticker=BHP',
      '/api/extraction-review/session/session-1',
      '/api/extraction-review/errors?limit=25',
      '/api/extraction-review/run/run-1?limit=30',
    ]
    expectedPaths.forEach((path, index) => {
      expect(fetchMock.mock.calls[index][0]).toBe(path)
      expect(fetchMock.mock.calls[index][1]?.headers).toMatchObject({
        'X-API-Key': 'local-secret',
      })
    })
  })

  it('fetches extraction review snippet blobs with the API key', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    vi.resetModules()
    const createObjectURL = vi.fn(() => 'blob:snippet')
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL: vi.fn() })
    const fetchMock = vi.fn(async () => new Response(new Blob(['png'], { type: 'image/png' }), {
      status: 200,
      statusText: 'OK',
    }))
    vi.stubGlobal('fetch', fetchMock)

    const { getExtractionReviewSnippetObjectUrl } = await import('./api-client')

    await expect(getExtractionReviewSnippetObjectUrl('/api/extraction-review/snippets/revenue.png')).resolves.toBe('blob:snippet')
    expect(fetchMock).toHaveBeenCalledWith('/api/extraction-review/snippets/revenue.png', {
      headers: { 'X-API-Key': 'local-secret' },
    })
    expect(createObjectURL).toHaveBeenCalledTimes(1)
  })

  it('does not send the API key to invalid extraction review snippet URLs', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    vi.resetModules()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const { getExtractionReviewSnippetObjectUrl } = await import('./api-client')

    await expect(getExtractionReviewSnippetObjectUrl('https://example.invalid/snippet.png')).rejects.toThrow(
      'Invalid extraction review snippet URL',
    )
    await expect(getExtractionReviewSnippetObjectUrl('/api/extraction-review/snippets/../secret.png')).rejects.toThrow(
      'Invalid extraction review snippet URL',
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
