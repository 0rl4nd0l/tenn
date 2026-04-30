import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text()
  const backend = await fetch(`${resolveBackendUrl()}/api/cockpit/feedback`, {
    method: 'POST',
    headers: copyRequestHeaders(request),
    body,
    cache: 'no-store',
  })
  const payload = await backend.text()
  return new NextResponse(payload, {
    status: backend.status,
    headers: {
      'Content-Type': backend.headers.get('Content-Type') ?? 'application/json',
    },
  })
}
