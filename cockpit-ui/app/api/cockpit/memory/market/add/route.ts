import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'
import { marketAddIntent, requireMemoryWriteIntent } from '@/app/api/cockpit/memory/_write-intent'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(request: NextRequest): Promise<NextResponse> {
  const confirmed = await requireMemoryWriteIntent(request, marketAddIntent)
  if (!confirmed.ok) return confirmed.response

  const backend = await fetch(`${resolveBackendUrl()}/api/context/memory/market/add`, {
    method: 'POST',
    headers: copyRequestHeaders(request),
    body: confirmed.body,
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
