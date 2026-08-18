import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  GET as getMarketplaceMissionRoute,
  PATCH as patchMarketplaceMissionRoute,
  DELETE as deleteMarketplaceMissionRoute,
} from '@/app/api/cockpit/marketplace/missions/[missionId]/route'
import {
  DELETE as deleteMarketplaceMissionLinkProductRoute,
  POST as postMarketplaceMissionLinkProductRoute,
} from '@/app/api/cockpit/marketplace/missions/[missionId]/link-product/route'
import {
  GET as getMarketplaceMissionsRoute,
  POST as postMarketplaceMissionsRoute,
} from '@/app/api/cockpit/marketplace/missions/route'
import {
  GET as getMarketplaceMatchRoute,
  PATCH as patchMarketplaceMatchRoute,
} from '@/app/api/cockpit/marketplace/matches/[matchId]/route'
import { POST as postMarketplaceEbaySyncRoute } from '@/app/api/cockpit/marketplace/price-intelligence/tracked-products/[trackedProductId]/ebay-sync/route'
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

  it('proxies mission create requests with the original request body', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ mission_id: 'mp_mission_1' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await postMarketplaceMissionsRoute(
      new Request('http://localhost/api/cockpit/marketplace/missions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'test-key',
        },
        body: JSON.stringify({ query: 'used workstation gpu' }),
      }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/marketplace/missions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.any(Headers),
        body: JSON.stringify({ query: 'used workstation gpu' }),
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json')
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(response.status).toBe(201)
    expect(await response.json()).toEqual({ mission_id: 'mp_mission_1' })
  })

  it('proxies mission detail read, update, and delete requests', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ mission_id: 'mp mission 1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ mission_id: 'mp mission 1', status: 'paused' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ mission_id: 'mp mission 1', deleted: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const params = { params: Promise.resolve({ missionId: 'mp mission 1' }) }
    const getResponse = await getMarketplaceMissionRoute(
      new Request('http://localhost/api/cockpit/marketplace/missions/mp%20mission%201', {
        headers: { 'X-API-Key': 'test-key' },
      }),
      params,
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://backend.internal:8000/api/cockpit/marketplace/missions/mp%20mission%201',
      expect.objectContaining({
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    expect(await getResponse.json()).toEqual({ mission_id: 'mp mission 1' })

    const patchResponse = await patchMarketplaceMissionRoute(
      new Request('http://localhost/api/cockpit/marketplace/missions/mp%20mission%201', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'test-key',
        },
        body: JSON.stringify({ status: 'paused' }),
      }),
      params,
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://backend.internal:8000/api/cockpit/marketplace/missions/mp%20mission%201',
      expect.objectContaining({
        method: 'PATCH',
        headers: expect.any(Headers),
        body: JSON.stringify({ status: 'paused' }),
        cache: 'no-store',
      }),
    )
    expect(await patchResponse.json()).toEqual({ mission_id: 'mp mission 1', status: 'paused' })

    const deleteResponse = await deleteMarketplaceMissionRoute(
      new Request('http://localhost/api/cockpit/marketplace/missions/mp%20mission%201', {
        method: 'DELETE',
        headers: { 'X-API-Key': 'test-key' },
      }),
      params,
    )

    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      'http://backend.internal:8000/api/cockpit/marketplace/missions/mp%20mission%201',
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    expect(await deleteResponse.json()).toEqual({ mission_id: 'mp mission 1', deleted: true })
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

  it('proxies tracked product eBay sync requests through the explicit backend path', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ observations_ingested: 2 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await postMarketplaceEbaySyncRoute(
      new Request(
        'http://localhost/api/cockpit/marketplace/price-intelligence/tracked-products/tp_1/ebay-sync',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'test-key',
          },
          body: JSON.stringify({ query: 'ASUS Pro WS X570-ACE' }),
        },
      ),
      { params: Promise.resolve({ trackedProductId: 'tp_1' }) },
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/marketplace/price-intelligence/tracked-products/tp_1/ebay-sync',
      expect.objectContaining({
        method: 'POST',
        headers: expect.any(Headers),
        body: JSON.stringify({ query: 'ASUS Pro WS X570-ACE' }),
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json')
    expect(await response.json()).toEqual({ observations_ingested: 2 })
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
