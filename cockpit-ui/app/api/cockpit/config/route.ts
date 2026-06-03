import { NextResponse } from 'next/server'
import { getCockpitConfig } from '@/lib/config'

export async function GET() {
  return NextResponse.json(getCockpitConfig())
}
