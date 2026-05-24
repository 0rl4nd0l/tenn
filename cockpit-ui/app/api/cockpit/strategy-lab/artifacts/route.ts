import { NextResponse } from 'next/server';

import { readStrategyLabArtifacts } from '@/lib/strategy-lab-artifacts-server';

export const runtime = 'nodejs';
export const maxDuration = 10;

export async function GET(): Promise<NextResponse> {
  return NextResponse.json(readStrategyLabArtifacts(), {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
