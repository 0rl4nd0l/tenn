import { NextResponse } from 'next/server'

import { issueMarketplaceCaptureToken } from '@/lib/marketplace-capture-tokens'

export const runtime = 'nodejs'

export async function POST(request: Request): Promise<NextResponse> {
  const apiKey = request.headers.get('x-api-key') ?? ''
  const { token, expiresAt } = issueMarketplaceCaptureToken(apiKey)
  return NextResponse.json(
    {
      token,
      expires_at: new Date(expiresAt).toISOString(),
    },
    {
      headers: {
        'Cache-Control': 'no-store',
      },
    },
  )
}
