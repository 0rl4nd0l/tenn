import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ ticker: string }> },
): Promise<NextResponse> {
  const { ticker } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/watchlist/${encodeURIComponent(ticker)}`,
    {
      method: 'DELETE',
      headers: copyRequestHeaders(request),
      cache: 'no-store',
    },
  )
  return new NextResponse(null, { status: backend.status })
}
