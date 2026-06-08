import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(request: NextRequest): Promise<NextResponse> {
  const url = new URL(request.url)
  const query = url.searchParams.toString()
  const upstream = await fetch(
    `${resolveBackendUrl()}/api/cockpit/chat/readiness${query ? `?${query}` : ''}`,
    {
      cache: 'no-store',
      headers: copyRequestHeaders(request),
    },
  )
  const body = await upstream.text()
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      'Cache-Control': 'no-store',
      'Content-Type': upstream.headers.get('content-type') || 'application/json',
    },
  })
}
