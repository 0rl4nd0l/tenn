import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

import { GET as getVerificationSourceRoute } from '@/app/api/extraction-eval/confirmed-metric-coverage/source/route'

describe('verification source PDF BFF route', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_KEY
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('forwards the configured API key to the protected backend source route', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    process.env.NEXT_PUBLIC_API_KEY = 'test-key'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('%PDF-1.7', {
        status: 200,
        headers: {
          'Content-Disposition': 'inline; filename="report.pdf"',
          'Content-Type': 'application/pdf',
        },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getVerificationSourceRoute(
      new NextRequest(
        'http://localhost/api/extraction-eval/confirmed-metric-coverage/source?path=data%2Fasx%2Fdocs%2FBHP%2Freport.pdf&page=44',
      ),
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend.internal:8000/api/extraction-eval/confirmed-metric-coverage/source?path=data%2Fasx%2Fdocs%2FBHP%2Freport.pdf&page=44',
      expect.objectContaining({
        headers: expect.any(Headers),
        cache: 'no-store',
      }),
    )
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('test-key')
    expect(response.status).toBe(200)
    expect(response.headers.get('Content-Type')).toBe('application/pdf')
    expect(response.headers.get('Content-Disposition')).toBe('inline; filename="report.pdf"')
    expect(response.headers.get('Cache-Control')).toBe('no-store')
    expect(await response.text()).toBe('%PDF-1.7')
  })

  it('prefers an explicit request API key when one is present', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    process.env.NEXT_PUBLIC_API_KEY = 'env-key'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('%PDF-1.7', {
        status: 200,
        headers: { 'Content-Type': 'application/pdf' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await getVerificationSourceRoute(
      new NextRequest(
        'http://localhost/api/extraction-eval/confirmed-metric-coverage/source?path=data%2Fasx%2Fdocs%2FBHP%2Freport.pdf',
        { headers: { 'X-API-Key': 'request-key' } },
      ),
    )

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect((init.headers as Headers).get('X-API-Key')).toBe('request-key')
  })

  it('fails closed with DATA_MISSING when no API key can be forwarded', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const response = await getVerificationSourceRoute(
      new NextRequest(
        'http://localhost/api/extraction-eval/confirmed-metric-coverage/source?path=data%2Fasx%2Fdocs%2FBHP%2Freport.pdf',
      ),
    )

    expect(fetchMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(await response.json()).toEqual({
      detail: 'DATA_MISSING: Cockpit API key is not configured for authenticated source PDF opening.',
    })
  })
})
