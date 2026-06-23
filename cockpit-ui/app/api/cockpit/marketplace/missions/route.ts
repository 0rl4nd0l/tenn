import { proxyBackendRequest } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url)
  const query = url.searchParams.toString()
  return proxyBackendRequest(request, {
    path: `/api/cockpit/marketplace/missions${query ? `?${query}` : ''}`,
  })
}

export async function POST(request: Request): Promise<Response> {
  return proxyBackendRequest(request, {
    path: '/api/cockpit/marketplace/missions',
    method: 'POST',
    forwardBody: true,
  })
}
