import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

export const MEMORY_WRITE_CONFIRMATION = 'reviewed-memory-write'
export const MEMORY_WRITE_INTENT_HEADER = 'X-Cockpit-Memory-Write-Intent'

export type MemoryWriteIntent =
  | 'company-memory-add'
  | 'company-memory-expire'
  | 'sector-memory-add'
  | 'sector-memory-expire'
  | 'macro-memory-add'
  | 'macro-memory-expire'
  | 'thesis-proposal-create'
  | 'thesis-proposal-confirm'
  | 'thesis-proposal-reject'
  | 'thesis-proposal-apply'

interface ConfirmedMemoryWrite {
  ok: true
  body: string
  payload: Record<string, unknown>
  intent: MemoryWriteIntent
}

interface DeniedMemoryWrite {
  ok: false
  response: NextResponse
}

function deny(status: number, code: string, detail: string): DeniedMemoryWrite {
  return {
    ok: false,
    response: NextResponse.json({ ok: false, code, detail }, { status }),
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export async function requireMemoryWriteIntent(
  request: NextRequest,
  expectedIntent: MemoryWriteIntent | ((payload: Record<string, unknown>) => MemoryWriteIntent | null),
): Promise<ConfirmedMemoryWrite | DeniedMemoryWrite> {
  let payload: unknown
  try {
    payload = await request.json()
  } catch {
    return deny(400, 'memory_write_json_required', 'Memory write requests must include a JSON body.')
  }

  if (!isRecord(payload)) {
    return deny(400, 'memory_write_body_required', 'Memory write requests must include a JSON object body.')
  }

  const resolvedIntent = typeof expectedIntent === 'function' ? expectedIntent(payload) : expectedIntent
  if (!resolvedIntent) {
    return deny(400, 'memory_write_scope_invalid', 'Memory write request scope is not supported by this route.')
  }

  const headerIntent = request.headers.get(MEMORY_WRITE_INTENT_HEADER)
  if (headerIntent !== resolvedIntent) {
    return deny(403, 'memory_write_intent_header_required', 'Memory write intent header is missing or incorrect.')
  }
  if (payload.intent !== resolvedIntent) {
    return deny(403, 'memory_write_intent_body_required', 'Memory write intent body field is missing or incorrect.')
  }
  if (payload.confirmation !== MEMORY_WRITE_CONFIRMATION) {
    return deny(403, 'memory_write_confirmation_required', 'Memory write confirmation is missing or incorrect.')
  }

  return {
    ok: true,
    body: JSON.stringify(payload),
    payload,
    intent: resolvedIntent,
  }
}

export function marketAddIntent(payload: Record<string, unknown>): MemoryWriteIntent | null {
  if (payload.scope === 'sector') return 'sector-memory-add'
  if (payload.scope === 'macro') return 'macro-memory-add'
  return null
}

export function marketExpireIntent(payload: Record<string, unknown>): MemoryWriteIntent | null {
  if (payload.scope === 'sector') return 'sector-memory-expire'
  if (payload.scope === 'macro') return 'macro-memory-expire'
  return null
}
