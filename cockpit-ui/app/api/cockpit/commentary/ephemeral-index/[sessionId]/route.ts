import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 60

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
): Promise<NextResponse> {
  const { sessionId } = await context.params
  const backend = await fetch(
    `${resolveBackendUrl()}/api/commentary/ephemeral-index/${encodeURIComponent(sessionId)}`,
    {
      method: 'DELETE',
      headers: copyRequestHeaders(request),
      cache: 'no-store',
    },
  )
  return new NextResponse(null, { status: backend.status })
}
