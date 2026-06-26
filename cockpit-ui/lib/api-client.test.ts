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

  it('sends the configured API key for streaming chat', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    eventOrder.length = 0
    instances.length = 0
    const { streamChat: streamChatWithKey } = await import('./api-client')

    await streamChatWithKey({
      message: 'hello',
      mode: 'analysis',
      onMessage: vi.fn(),
      onError: vi.fn(),
      onEnd: vi.fn(),
    })

    expect(instances[0]?.options.headers).toMatchObject({
      'Content-Type': 'application/json',
      'X-API-Key': 'local-secret',
    })
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

describe('chat/session API key forwarding', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('sends the configured API key for chat session CRUD and blocking chat', async () => {
    vi.resetModules()
    vi.stubEnv('NEXT_PUBLIC_API_KEY', 'local-secret')
    const fetchMock = vi.fn(async (path: string) => {
      if (path.includes('/chat/sessions?')) {
        return new Response(JSON.stringify({ items: [] }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        })
      }
      if (path.endsWith('/chat/sessions')) {
        return new Response(
          JSON.stringify({ ok: true, session_id: 'session-1', created: true }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        )
      }
      if (path.includes('/chat/sessions/session-1')) {
        return new Response(JSON.stringify({ items: [], session_id: 'session-1' }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        })
      }
      if (path.endsWith('/chat')) {
        return new Response(JSON.stringify({ type: 'done', data: { text: 'ok' } }), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        })
      }
      return new Response(JSON.stringify({ ok: true, deleted_count: 0 }), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const {
      listChatSessions,
      getChatSessionMessages,
      createChatSessionRemote,
      deleteChatSessionRemote,
      sendChatMessage,
    } = await import('./api-client')

    await listChatSessions()
    await createChatSessionRemote('session-1')
    await getChatSessionMessages('session-1')
    await deleteChatSessionRemote('session-1')
    await sendChatMessage({ message: 'hello', mode: 'analysis' })

    expect(fetchMock).toHaveBeenCalledTimes(5)
    for (const call of fetchMock.mock.calls) {
      expect(call[1]).toEqual(
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'local-secret',
          }),
        }),
      )
    }
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
