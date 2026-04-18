import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(
  request: Request,
  context: { params: Promise<{ missionId: string }> },
): Promise<NextResponse> {
  const { missionId } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`,
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
  context: { params: Promise<{ missionId: string }> },
): Promise<NextResponse> {
  const { missionId } = await context.params
  const body = await request.text()
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`,
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
