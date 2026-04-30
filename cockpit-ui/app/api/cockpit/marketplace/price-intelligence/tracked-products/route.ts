import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(request: Request): Promise<NextResponse> {
  const url = new URL(request.url)
  const query = url.searchParams.toString()
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/price-intelligence/tracked-products${query ? `?${query}` : ''}`,
    {
      headers: copyRequestHeaders(request),
      cache: 'no-store',
    },
  )
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: {
      'Content-Type': backend.headers.get('Content-Type') ?? 'application/json',
    },
  })
}
