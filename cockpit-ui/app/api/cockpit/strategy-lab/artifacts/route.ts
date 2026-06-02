import { NextResponse } from 'next/server';

import { requireCockpitBffApiKey } from '@/lib/cockpit-bff-auth';
import { readStrategyLabArtifacts } from '@/lib/strategy-lab-artifacts-server';

export const runtime = 'nodejs';
export const maxDuration = 10;

export async function GET(request: Request): Promise<Response> {
  const auth = requireCockpitBffApiKey(request);
  if (!auth.ok) return auth.response;

  return NextResponse.json(readStrategyLabArtifacts(), {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
