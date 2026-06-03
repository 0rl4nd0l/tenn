import { NextResponse } from 'next/server'
import { backendHeaders } from '@/lib/backend'

export async function GET() {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  try {
    const res = await fetch(`${backendUrl}/api/health`, { headers: backendHeaders(), cache: 'no-store' })
    const payload = await res.json().catch(() => ({}))
    return NextResponse.json({ status: res.ok ? 'ok' : 'degraded', backend: payload }, { status: res.ok ? 200 : 502 })
  } catch (error) {
    return NextResponse.json({ status: 'degraded', error: String(error) }, { status: 502 })
  }
}
