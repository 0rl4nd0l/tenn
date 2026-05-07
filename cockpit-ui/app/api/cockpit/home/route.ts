import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { buildCockpitHomeBffResponse } from '@/lib/cockpit-home-api';
import { copyRequestHeaders } from '@/lib/proxy';

export const runtime = 'nodejs';
export const maxDuration = 30;

export async function GET(request: NextRequest): Promise<NextResponse> {
  const payload = await buildCockpitHomeBffResponse({
    headers: copyRequestHeaders(request),
  });

  return NextResponse.json(payload, {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
