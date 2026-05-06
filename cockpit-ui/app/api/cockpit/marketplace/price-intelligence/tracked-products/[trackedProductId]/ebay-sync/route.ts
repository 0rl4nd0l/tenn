import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(
  request: Request,
  context: { params: Promise<{ trackedProductId: string }> },
): Promise<NextResponse> {
  const { trackedProductId } = await context.params
  const body = await request.text()
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/price-intelligence/tracked-products/${encodeURIComponent(trackedProductId)}/ebay-sync`,
    {
      method: 'POST',
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
