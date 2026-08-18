import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  buildBackendResponse,
  copyRequestHeaders,
  proxyBackendRequest,
  resolveBackendPath,
  resolveBackendUrl,
} from './proxy'

describe('Cockpit BFF proxy helper', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
  })

  it('resolves the backend base URL without a trailing slash', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000/'

    expect(resolveBackendUrl()).toBe('http://backend.internal:8000')
    expect(resolveBackendPath('/api/cockpit/watchlist')).toBe(
      'http://backend.internal:8000/api/cockpit/watchlist',
    )
    expect(resolveBackendPath('api/cockpit/watchlist')).toBe(
      'http://backend.internal:8000/api/cockpit/watchlist',
    )
  })

  it('copies client headers without hop-specific request headers', () => {
    const headers = copyRequestHeaders(
      new Headers({
        'Content-Length': '123',
        'Content-Type': 'application/json',
        Host: 'localhost:3000',
        'X-API-Key': 'test-key',
      }),
    )

    expect(headers.get('Content-Length')).toBeNull()
    expect(headers.get('Host')).toBeNull()
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.get('X-API-Key')).toBe('test-key')
  })

  it('forwards method, headers, body, and no-store cache to the backend', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const body = JSON.stringify({ ticker: 'BHP' })
    const request = new Request('http://localhost/api/cockpit/watchlist', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'test-key',
      },
      body,
    })

    const response = await proxyBackendRequest(request, {
      path: '/api/cockpit/watchlist',
      method: 'POST',
      forwardBody: true,
      fetcher,
    })

    expect(fetcher).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/watchlist',
      expect.objectContaining({
        method: 'POST',
        body,
        cache: 'no-store',
        headers: expect.any(Headers),
      }),
    )
    const init = fetcher.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json')
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(response.status).toBe(202)
    expect(await response.json()).toEqual({ ok: true })
  })

  it('preserves backend status and content type when building route responses', async () => {
    const response = await buildBackendResponse(
      new Response('backend unavailable', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' },
      }),
    )

    expect(response.status).toBe(503)
    expect(response.headers.get('Content-Type')).toBe('text/plain')
    expect(await response.text()).toBe('backend unavailable')
  })

  it('does not attach a body to bodyless upstream statuses', async () => {
    const response = await buildBackendResponse(new Response(null, { status: 204 }))

    expect(response.status).toBe(204)
    expect(await response.text()).toBe('')
  })
})
