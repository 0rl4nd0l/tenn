import { NextResponse } from 'next/server'

import { copyRequestHeaders, resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(
  request: Request,
  context: { params: Promise<{ jobId: string }> },
): Promise<NextResponse> {
  const { jobId } = await context.params
  const url = new URL(request.url)
  const backend = await fetch(
    `${resolveBackendUrl()}/api/cockpit/marketplace/scans/${encodeURIComponent(jobId)}?${url.searchParams.toString()}`,
    {
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
