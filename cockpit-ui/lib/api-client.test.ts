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

describe('patchCockpitPreferences', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('sends the configured API key when patching preferences', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          api_default_enabled: true,
          marketplace_prefer_cloud_routing: false,
          chat_routing_policy_override: 'config_default',
          chat_runtime_target: 'local',
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { patchCockpitPreferences } = await import('./api-client')

    await patchCockpitPreferences({ api_default_enabled: true })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/preferences',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ api_default_enabled: true }),
        headers: expect.objectContaining({
          'X-API-Key': 'local-secret',
        }),
      }),
    )
  })
})
