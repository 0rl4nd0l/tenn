import { proxyBackendRequest } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function POST(
  request: Request,
  context: { params: Promise<{ missionId: string }> },
): Promise<Response> {
  const { missionId } = await context.params
  return proxyBackendRequest(request, {
    path: `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}/link-product`,
    method: 'POST',
    forwardBody: true,
  })
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ missionId: string }> },
): Promise<Response> {
  const { missionId } = await context.params
  return proxyBackendRequest(request, {
    path: `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}/link-product`,
    method: 'DELETE',
  })
}
