import { afterEach, describe, expect, it, vi } from 'vitest'

import { POST as submitMarketplaceCapture } from '@/app/api/cockpit/commentary/marketplace-capture/submit/route'
import {
  consumeMarketplaceCaptureToken,
  issueMarketplaceCaptureToken,
} from '@/lib/marketplace-capture-tokens'

function marketplaceSubmitRequest(token: string): Request {
  const formData = new FormData()
  formData.set('token', token)
  formData.set('url', 'https://www.facebook.com/marketplace/item/123')
  formData.set('captured_at', '2026-06-02T04:00:00.000Z')
  formData.set('title', 'Workbench')
  formData.set('price', 'A$80')
  formData.set('seller_name', 'Local Seller')
  formData.set('location', 'Melbourne VIC')
  formData.set('description', 'A solid workbench')
  formData.set('raw_text_lines', JSON.stringify(['Workbench', 'A$80']))

  return new Request('http://localhost/api/cockpit/commentary/marketplace-capture/submit', {
    method: 'POST',
    body: formData,
  })
}

function successfulIngestResponse(): Response {
  return new Response(
    JSON.stringify({
      source_id: 'marketplace-source-1',
      listing_title: 'Workbench',
      source_kind: 'concat',
      staged: true,
    }),
    { status: 200 },
  )
}

describe('Marketplace capture tokens', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('consumes a valid token once', () => {
    const { token } = issueMarketplaceCaptureToken('operator-key')

    expect(consumeMarketplaceCaptureToken(token)).toMatchObject({
      apiKey: 'operator-key',
    })
    expect(consumeMarketplaceCaptureToken(token)).toBeNull()
  })

  it('keeps expired tokens invalid', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-02T04:00:00.000Z'))
    const { token } = issueMarketplaceCaptureToken('operator-key')

    vi.setSystemTime(new Date('2026-06-02T04:16:00.000Z'))

    expect(consumeMarketplaceCaptureToken(token)).toBeNull()
    expect(consumeMarketplaceCaptureToken(token)).toBeNull()
  })

  it('relays the first submit and rejects replay before backend ingest', async () => {
    const fetchMock = vi.fn<(input: string | URL | Request, init?: RequestInit) => Promise<Response>>()
    fetchMock.mockResolvedValue(successfulIngestResponse())
    vi.stubGlobal('fetch', fetchMock)
    const { token } = issueMarketplaceCaptureToken('operator-key')

    const firstResponse = await submitMarketplaceCapture(marketplaceSubmitRequest(token))
    const replayResponse = await submitMarketplaceCapture(marketplaceSubmitRequest(token))

    expect(firstResponse.status).toBe(200)
    expect(replayResponse.status).toBe(410)
    expect(await replayResponse.text()).toContain('Marketplace helper expired')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const headers = fetchMock.mock.calls[0]?.[1]?.headers
    expect(headers).toBeInstanceOf(Headers)
    expect((headers as Headers).get('X-API-Key')).toBe('operator-key')
  })

  it('consumes the token even when the backend relay fails', async () => {
    const fetchMock = vi.fn<(input: string | URL | Request, init?: RequestInit) => Promise<Response>>()
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: 'relay rejected' }), { status: 502 }))
    vi.stubGlobal('fetch', fetchMock)
    const { token } = issueMarketplaceCaptureToken('operator-key')

    const failedResponse = await submitMarketplaceCapture(marketplaceSubmitRequest(token))
    const replayResponse = await submitMarketplaceCapture(marketplaceSubmitRequest(token))

    expect(failedResponse.status).toBe(502)
    expect(replayResponse.status).toBe(410)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
