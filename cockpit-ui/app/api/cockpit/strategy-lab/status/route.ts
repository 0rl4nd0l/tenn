import { NextResponse } from 'next/server';

import { requireCockpitBffApiKey } from '@/lib/cockpit-bff-auth';
import { readStrategyLabStatus } from '@/lib/strategy-lab-status-server';

export const runtime = 'nodejs';
export const maxDuration = 10;

export async function GET(request: Request): Promise<Response> {
  const auth = requireCockpitBffApiKey(request);
  if (!auth.ok) return auth.response;

  return NextResponse.json(readStrategyLabStatus(), {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
