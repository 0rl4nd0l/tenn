import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 900

const TAKEAWAYS_TIMEOUT_MS = 15 * 60 * 1000

export async function POST(request: NextRequest): Promise<NextResponse> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TAKEAWAYS_TIMEOUT_MS)

  try {
    const body = await request.text()
    const backend = await fetch(`${resolveBackendUrl()}/api/commentary/takeaways`, {
      method: 'POST',
      headers: copyRequestHeaders(request),
      body,
      signal: controller.signal,
      cache: 'no-store',
    })
    const payload = await backend.text()
    return new NextResponse(payload, {
      status: backend.status,
      headers: {
        'Content-Type': backend.headers.get('Content-Type') ?? 'application/json',
      },
    })
  } finally {
    clearTimeout(timer)
  }
}
