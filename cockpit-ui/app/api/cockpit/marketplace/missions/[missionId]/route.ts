import { proxyBackendRequest } from '@/lib/proxy'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function GET(
  request: Request,
  context: { params: Promise<{ missionId: string }> },
): Promise<Response> {
  const { missionId } = await context.params
  return proxyBackendRequest(request, {
    path: `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`,
  })
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ missionId: string }> },
): Promise<Response> {
  const { missionId } = await context.params
  return proxyBackendRequest(request, {
    path: `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`,
    method: 'PATCH',
    forwardBody: true,
  })
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ missionId: string }> },
): Promise<Response> {
  const { missionId } = await context.params
  return proxyBackendRequest(request, {
    path: `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`,
    method: 'DELETE',
  })
}
