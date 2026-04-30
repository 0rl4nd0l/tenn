import { afterEach, describe, expect, it, vi } from 'vitest'

import { GET as getMarketplaceMissionsRoute } from '@/app/api/cockpit/marketplace/missions/route'
import {
  DELETE as deleteMarketplaceMissionLinkProductRoute,
  POST as postMarketplaceMissionLinkProductRoute,
} from '@/app/api/cockpit/marketplace/missions/[missionId]/link-product/route'
import {
  GET as getMarketplaceMatchRoute,
  PATCH as patchMarketplaceMatchRoute,
} from '@/app/api/cockpit/marketplace/matches/[matchId]/route'
import { GET as getMarketplaceTrackedProductsRoute } from '@/app/api/cockpit/marketplace/price-intelligence/tracked-products/route'

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

  it('proxies tracked product list requests through the price-intelligence backend path', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getMarketplaceTrackedProductsRoute(
      new Request(
        'http://localhost/api/cockpit/marketplace/price-intelligence/tracked-products?category=gpu',
        {
          headers: { 'X-API-Key': 'test-key' },
        },
      ),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/marketplace/price-intelligence/tracked-products?category=gpu',
      expect.objectContaining({
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(await response.json()).toEqual({ items: [] })
  })

  it('proxies mission tracked-product link and unlink requests', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ mission_id: 'mp_mission_1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ mission_id: 'mp_mission_1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const postResponse = await postMarketplaceMissionLinkProductRoute(
      new Request(
        'http://localhost/api/cockpit/marketplace/missions/mp_mission_1/link-product',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'test-key',
          },
          body: JSON.stringify({ tracked_product_id: 'tp_1' }),
        },
      ),
      { params: Promise.resolve({ missionId: 'mp_mission_1' }) },
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://backend.internal:8000/api/cockpit/marketplace/missions/mp_mission_1/link-product',
      expect.objectContaining({
        method: 'POST',
        headers: expect.any(Headers),
        body: JSON.stringify({ tracked_product_id: 'tp_1' }),
        cache: 'no-store',
      }),
    )
    expect(await postResponse.json()).toEqual({ mission_id: 'mp_mission_1' })

    const deleteResponse = await deleteMarketplaceMissionLinkProductRoute(
      new Request(
        'http://localhost/api/cockpit/marketplace/missions/mp_mission_1/link-product',
        {
          method: 'DELETE',
          headers: { 'X-API-Key': 'test-key' },
        },
      ),
      { params: Promise.resolve({ missionId: 'mp_mission_1' }) },
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://backend.internal:8000/api/cockpit/marketplace/missions/mp_mission_1/link-product',
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    expect(await deleteResponse.json()).toEqual({ mission_id: 'mp_mission_1' })
  })
})
