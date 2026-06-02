import { timingSafeEqual } from 'node:crypto'

type CockpitBffAuthResult =
  | { ok: true }
  | { ok: false; response: Response }

function configuredApiKey(): string {
  return String(process.env.COCKPIT_API_KEY || process.env.NEXT_PUBLIC_API_KEY || '').trim()
}

function constantTimeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left)
  const rightBuffer = Buffer.from(right)
  if (leftBuffer.length !== rightBuffer.length) return false
  return timingSafeEqual(leftBuffer, rightBuffer)
}

function deny(status: number, code: string, message: string): CockpitBffAuthResult {
  return {
    ok: false,
    response: Response.json({ ok: false, code, message }, { status }),
  }
}

export function requireCockpitBffApiKey(request: Request): CockpitBffAuthResult {
  const expected = configuredApiKey()
  if (!expected) {
    return deny(
      503,
      'cockpit_api_key_not_configured',
      'Cockpit telemetry routes require a configured API key.',
    )
  }

  const provided = String(request.headers.get('x-api-key') || '').trim()
  if (!provided || !constantTimeEqual(provided, expected)) {
    return deny(
      403,
      'cockpit_api_key_required',
      'Cockpit telemetry routes require a valid API key.',
    )
  }

  return { ok: true }
}
