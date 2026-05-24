import { NextResponse } from 'next/server';

import { readStrategyLabStatus } from '@/lib/strategy-lab-status-server';

export const runtime = 'nodejs';
export const maxDuration = 10;

export async function GET(): Promise<NextResponse> {
  return NextResponse.json(readStrategyLabStatus(), {
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}
