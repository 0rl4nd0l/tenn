type MarketplaceCaptureTokenEntry = {
  apiKey: string
  expiresAt: number
}

const MARKETPLACE_CAPTURE_TOKEN_TTL_MS = 15 * 60 * 1000
const marketplaceCaptureTokens = new Map<string, MarketplaceCaptureTokenEntry>()

function pruneExpiredTokens(now: number) {
  for (const [token, entry] of marketplaceCaptureTokens.entries()) {
    if (entry.expiresAt <= now) {
      marketplaceCaptureTokens.delete(token)
    }
  }
}

export function issueMarketplaceCaptureToken(apiKey: string) {
  const now = Date.now()
  pruneExpiredTokens(now)
  const token = crypto.randomUUID()
  const expiresAt = now + MARKETPLACE_CAPTURE_TOKEN_TTL_MS
  marketplaceCaptureTokens.set(token, {
    apiKey: String(apiKey || '').trim(),
    expiresAt,
  })
  return { token, expiresAt }
}

export function consumeMarketplaceCaptureToken(token: string) {
  const now = Date.now()
  pruneExpiredTokens(now)
  const normalizedToken = String(token || '').trim()
  const entry = marketplaceCaptureTokens.get(normalizedToken)
  if (!entry || entry.expiresAt <= now) {
    if (entry) {
      marketplaceCaptureTokens.delete(normalizedToken)
    }
    return null
  }
  marketplaceCaptureTokens.delete(normalizedToken)
  return entry
}
