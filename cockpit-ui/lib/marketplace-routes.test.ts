import { afterEach, describe, expect, it, vi } from 'vitest'

import { GET as getMarketplaceMissionsRoute } from '@/app/api/cockpit/marketplace/missions/route'
import {
  GET as getMarketplaceMatchRoute,
  PATCH as patchMarketplaceMatchRoute,
} from '@/app/api/cockpit/marketplace/matches/[matchId]/route'

describe('marketplace BFF routes', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('proxies mission list requests with query strings and API headers', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getMarketplaceMissionsRoute(
      new Request('http://localhost/api/cockpit/marketplace/missions?status=active', {
        headers: { 'X-API-Key': 'test-key' },
      }),
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      'http://backend.internal:8000/api/cockpit/marketplace/missions?status=active',
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(await response.json()).toEqual({ items: [] })
  })

  it('proxies single-match reads to the backend detail endpoint', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ match_id: 'mp_match_1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getMarketplaceMatchRoute(
      new Request('http://localhost/api/cockpit/marketplace/matches/mp_match_1', {
        headers: { 'X-API-Key': 'test-key' },
      }),
      { params: Promise.resolve({ matchId: 'mp_match_1' }) },
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/marketplace/matches/mp_match_1',
      expect.objectContaining({
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    expect(await response.json()).toEqual({ match_id: 'mp_match_1' })
  })

  it('proxies match status updates with the original request body', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ match_id: 'mp_match_1', status: 'reviewed' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await patchMarketplaceMatchRoute(
      new Request('http://localhost/api/cockpit/marketplace/matches/mp_match_1', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'test-key',
        },
        body: JSON.stringify({ status: 'reviewed' }),
      }),
      { params: Promise.resolve({ matchId: 'mp_match_1' }) },
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/marketplace/matches/mp_match_1',
      expect.objectContaining({
        method: 'PATCH',
        headers: expect.any(Headers),
        body: JSON.stringify({ status: 'reviewed' }),
        cache: 'no-store',
      }),
    )
    expect(await response.json()).toEqual({ match_id: 'mp_match_1', status: 'reviewed' })
  })
})
