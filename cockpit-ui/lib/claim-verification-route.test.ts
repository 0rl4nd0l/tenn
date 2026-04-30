import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

import { POST as postClaimVerificationRoute } from '@/app/api/cockpit/claims/verify/route'
import { POST as postFeedbackRoute } from '@/app/api/cockpit/feedback/route'

describe('claim verification BFF route', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('proxies verification requests to the backend with headers and body', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, verdicts: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const body = JSON.stringify({ assistant_text: 'BHP revenue was $10m.' })
    const response = await postClaimVerificationRoute(
      new NextRequest('http://localhost/api/cockpit/claims/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'test-key',
        },
        body,
      }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/claims/verify',
      expect.objectContaining({
        method: 'POST',
        headers: expect.any(Headers),
        body,
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(await response.json()).toEqual({ ok: true, verdicts: [] })
  })
})

describe('response feedback BFF route', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('proxies response feedback requests to the backend with headers and body', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, feedback_id: 'fb-1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const body = JSON.stringify({
      reason_code: 'unsupported_claim',
      final_answer_text: 'BHP revenue was $10m.',
    })
    const response = await postFeedbackRoute(
      new NextRequest('http://localhost/api/cockpit/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'test-key',
        },
        body,
      }),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/cockpit/feedback',
      expect.objectContaining({
        method: 'POST',
        headers: expect.any(Headers),
        body,
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(await response.json()).toEqual({ ok: true, feedback_id: 'fb-1' })
  })
})
