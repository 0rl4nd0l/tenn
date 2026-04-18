import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function PATCH(
  request: Request,
  context: { params: Promise<{ alertId: string }> },
): Promise<NextResponse> {
  const { alertId } = await context.params
  const body = await request.text()
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/alerts/${encodeURIComponent(alertId)}`,
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
