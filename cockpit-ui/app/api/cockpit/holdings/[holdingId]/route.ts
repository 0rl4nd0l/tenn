import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ holdingId: string }> },
): Promise<NextResponse> {
  const { holdingId } = await context.params
  const body = await request.text()
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/holdings/${encodeURIComponent(holdingId)}`,
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

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ holdingId: string }> },
): Promise<NextResponse> {
  const { holdingId } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/holdings/${encodeURIComponent(holdingId)}`,
    {
      method: 'DELETE',
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

