import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

import { GET as getCommentaryRecentRoute } from '@/app/api/cockpit/commentary/recent/route'

describe('commentary BFF routes', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('proxies recent commentary requests with query strings and API headers', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], count: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getCommentaryRecentRoute(
      new NextRequest('http://localhost/api/cockpit/commentary/recent?limit=5', {
        headers: { 'X-API-Key': 'test-key' },
      }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/commentary/recent?limit=5',
      expect.objectContaining({
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(await response.json()).toEqual({ items: [], count: 0 })
  })

  it('surfaces backend recent commentary errors without frontend fallback state', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'source registry unavailable' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getCommentaryRecentRoute(
      new NextRequest('http://localhost/api/cockpit/commentary/recent'),
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ detail: 'source registry unavailable' })
  })
})
