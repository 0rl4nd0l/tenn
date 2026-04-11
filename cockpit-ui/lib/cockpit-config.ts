export interface CockpitConfigSnapshot {
  activeRuns: Array<{
    runId: string | null
    documentId: string | null
    title: string | null
  }>
  model: string | null
  maxTokens: number | null
  temperature: number | null
  profile: string | null
  anthropicKeyConfigured: boolean
  extractionActive: boolean | null
  extractionSource: string | null
  extractionActivityExpiresInSeconds: number | null
}

function readNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function readString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function readBoolean(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value
  return null
}

export function parseCockpitConfig(payload: Record<string, unknown> | undefined): CockpitConfigSnapshot {
  const activeRuns = Array.isArray(payload?.extraction_active_runs)
    ? payload.extraction_active_runs.flatMap((entry) => {
      if (!entry || typeof entry !== 'object') return []
      const run = entry as Record<string, unknown>
      return [{
        runId: readString(run.run_id),
        documentId: readString(run.document_id),
        title: readString(run.title),
      }]
    })
    : []

  return {
    activeRuns,
    model: readString(payload?.llm_model) ?? readString(payload?.model),
    maxTokens: readNumber(payload?.max_tokens),
    temperature: readNumber(payload?.temperature),
    profile: readString(payload?.profile),
    anthropicKeyConfigured: payload?.anthropic_key_configured === true,
    extractionActive: readBoolean(payload?.extraction_active),
    extractionSource: readString(payload?.extraction_activity_source),
    extractionActivityExpiresInSeconds: readNumber(payload?.extraction_activity_expires_in_seconds),
  }
}

function canonicalizeModelIdentity(model: string | null | undefined): string {
  const trimmed = String(model || '').trim().toLowerCase()
  if (!trimmed) return ''
  const withoutPrefix = trimmed.startsWith('model:') ? trimmed.slice('model:'.length) : trimmed
  return withoutPrefix.replace(/[^a-z0-9]+/g, '')
}

export function modelsLikelyMatch(left: string | null | undefined, right: string | null | undefined): boolean {
  const leftKey = canonicalizeModelIdentity(left)
  const rightKey = canonicalizeModelIdentity(right)
  if (!leftKey || !rightKey) return false
  if (leftKey === rightKey) return true
  const minPrefixLength = 10
  return (
    (leftKey.length >= minPrefixLength && rightKey.startsWith(leftKey))
    || (rightKey.length >= minPrefixLength && leftKey.startsWith(rightKey))
  )
}

export function resolveRuntimeModel(
  sessionModel: string | null | undefined,
  configModel: string | null | undefined,
): string {
  const persistedModel = String(sessionModel || '').trim()
  if (persistedModel && persistedModel !== 'local') {
    return persistedModel
  }
  return String(configModel || '').trim()
}
