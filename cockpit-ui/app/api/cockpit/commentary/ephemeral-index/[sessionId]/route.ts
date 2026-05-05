import { NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const maxDuration = 30

export async function DELETE(): Promise<NextResponse> {
  return NextResponse.json(
    {
      ok: false,
      status: 'unavailable',
      detail: 'Ephemeral commentary indexing is not available in this Cockpit build.',
    },
    { status: 501 },
  )
}
