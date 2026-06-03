import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ items: [], status: 'empty', message: 'Holdings source restored; backend persistence not wired in this minimal shell.' })
}
