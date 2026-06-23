import type { NextRequest } from 'next/server'

import { proxyBackendRequest } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ ticker: string }> },
): Promise<Response> {
  const { ticker } = await context.params
  return proxyBackendRequest(request, {
    path: `/api/cockpit/watchlist/${encodeURIComponent(ticker)}`,
    method: 'DELETE',
  })
}
