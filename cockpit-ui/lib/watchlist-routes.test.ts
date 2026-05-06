import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

import {
  GET as getWatchlistRoute,
  POST as postWatchlistRoute,
} from '@/app/api/cockpit/watchlist/route'
import { DELETE as deleteWatchlistRoute } from '@/app/api/cockpit/watchlist/[ticker]/route'

describe('watchlist BFF routes', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('proxies GET requests to the backend Cockpit watchlist route', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getWatchlistRoute(
      new NextRequest('http://localhost/api/cockpit/watchlist', {
        headers: { 'X-API-Key': 'test-key' },
      }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/watchlist',
      expect.objectContaining({
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(await response.json()).toEqual({ ok: true, items: [] })
  })

  it('proxies POST requests with the original body', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, item: { ticker: 'BHP' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const body = JSON.stringify({ ticker: 'BHP', note: 'watch' })

    const response = await postWatchlistRoute(
      new NextRequest('http://localhost/api/cockpit/watchlist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'test-key',
        },
        body,
      }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/watchlist',
      expect.objectContaining({
        method: 'POST',
        headers: expect.any(Headers),
        body,
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json')
    expect(await response.json()).toEqual({ ok: true, item: { ticker: 'BHP' } })
  })

  it('proxies DELETE requests to the backend ticker path', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, removed: true, ticker: 'BHP' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await deleteWatchlistRoute(
      new NextRequest('http://localhost/api/cockpit/watchlist/BHP', {
        method: 'DELETE',
        headers: { 'X-API-Key': 'test-key' },
      }),
      { params: Promise.resolve({ ticker: 'BHP' }) },
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/watchlist/BHP',
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    expect(await response.json()).toEqual({ ok: true, removed: true, ticker: 'BHP' })
  })

  it('surfaces backend errors without frontend fallback state', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'store unavailable' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getWatchlistRoute(
      new NextRequest('http://localhost/api/cockpit/watchlist'),
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(response.status).toBe(500)
    expect(await response.json()).toEqual({ detail: 'store unavailable' })
  })
})
