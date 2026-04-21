import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(request: NextRequest): Promise<NextResponse> {
  const backend = await fetch(`${resolveBackendUrl()}/api/cockpit/holdings`, {
    headers: copyRequestHeaders(request),
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

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text()
  const backend = await fetch(`${resolveBackendUrl()}/api/cockpit/holdings`, {
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

