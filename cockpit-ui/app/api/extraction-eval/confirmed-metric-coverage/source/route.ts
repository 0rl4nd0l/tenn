import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

const BACKEND_SOURCE_ROUTE = '/api/extraction-eval/confirmed-metric-coverage/source'

function configuredApiKey(): string {
  return String(process.env.NEXT_PUBLIC_API_KEY || '').trim()
}

function forwardedApiKey(headers: Headers): string | null {
  const requestKey = String(headers.get('X-API-Key') || '').trim()
  if (requestKey) return requestKey
  const envKey = configuredApiKey()
  return envKey || null
}

function proxyResponseHeaders(response: Response): Headers {
  const headers = new Headers()
  const contentType = response.headers.get('Content-Type')
  const contentDisposition = response.headers.get('Content-Disposition')
  if (contentType) headers.set('Content-Type', contentType)
  if (contentDisposition) headers.set('Content-Disposition', contentDisposition)
  headers.set('Cache-Control', 'no-store')
  return headers
}

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : 'unknown error'
}

export async function GET(request: Request): Promise<NextResponse> {
  const url = new URL(request.url)
  const headers = copyRequestHeaders(request)
  const apiKey = forwardedApiKey(headers)

  if (!apiKey) {
    return NextResponse.json(
      {
        detail:
          'DATA_MISSING: Cockpit API key is not configured for authenticated source PDF opening.',
      },
      {
        status: 401,
        headers: { 'Cache-Control': 'no-store' },
      },
    )
  }

  headers.set('X-API-Key', apiKey)
  const query = url.searchParams.toString()
  const backendUrl = `${resolveBackendUrl()}${BACKEND_SOURCE_ROUTE}${query ? `?${query}` : ''}`

  try {
    const backend = await fetch(backendUrl, {
      headers,
      cache: 'no-store',
    })
    return new NextResponse(backend.body, {
      status: backend.status,
      headers: proxyResponseHeaders(backend),
    })
  } catch (error) {
    return NextResponse.json(
      {
        detail: `DATA_MISSING: source PDF proxy failed: ${describeError(error)}`,
      },
      {
        status: 502,
        headers: { 'Cache-Control': 'no-store' },
      },
    )
  }
}
