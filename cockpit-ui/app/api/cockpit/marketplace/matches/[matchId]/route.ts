import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(
  request: Request,
  context: { params: Promise<{ matchId: string }> },
): Promise<NextResponse> {
  const { matchId } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/matches/${encodeURIComponent(matchId)}`,
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

export async function PATCH(
  request: Request,
  context: { params: Promise<{ matchId: string }> },
): Promise<NextResponse> {
  const { matchId } = await context.params
  const body = await request.text()
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/matches/${encodeURIComponent(matchId)}`,
    {
      method: 'PATCH',
      headers: copyRequestHeaders(request),
      body,
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
