import type { NextRequest } from 'next/server'

import { proxyBackendRequest } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(request: NextRequest): Promise<Response> {
  return proxyBackendRequest(request, {
    path: '/api/cockpit/watchlist',
    method: 'POST',
    forwardBody: true,
  })
}

export async function GET(request: NextRequest): Promise<Response> {
  return proxyBackendRequest(request, {
    path: '/api/cockpit/watchlist',
  })
}
