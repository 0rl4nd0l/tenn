import type { MarketplaceMatch } from '@/lib/marketplace-api'

export const RECENT_MATCH_THRESHOLD_DAYS = 7

const RECENT_MATCH_THRESHOLD_MS = RECENT_MATCH_THRESHOLD_DAYS * 24 * 60 * 60 * 1000
const MATERIAL_LAST_SEEN_UPDATE_MS = 60 * 60 * 1000

export function timestampValue(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function formatMatchClock(value: string | null | undefined): string {
  if (!value) return 'n/a'
  const parsed = timestampValue(value)
  if (!parsed) return value
  return new Date(parsed).toLocaleString('en-AU', {
    hour12: false,
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function firstFoundTimestamp(match: MarketplaceMatch): string | null {
  return match.first_found_at || match.captured_at || match.updated_at || null
}

export function lastSeenTimestamp(match: MarketplaceMatch): string | null {
  return match.last_seen_at || match.captured_at || match.updated_at || null
}

export function compareByFirstFoundDesc(left: MarketplaceMatch, right: MarketplaceMatch): number {
  const firstFoundCompare =
    timestampValue(firstFoundTimestamp(right)) - timestampValue(firstFoundTimestamp(left))
  if (firstFoundCompare !== 0) return firstFoundCompare
  return timestampValue(right.captured_at) - timestampValue(left.captured_at)
}

export function hasRecentFirstFound(match: MarketplaceMatch, now = Date.now()): boolean {
  const firstFound = timestampValue(match.first_found_at)
  return firstFound > 0 && firstFound >= now - RECENT_MATCH_THRESHOLD_MS
}

export function isNewOpportunity(match: MarketplaceMatch, now = Date.now()): boolean {
  return String(match.status || '').toLowerCase() === 'new' || hasRecentFirstFound(match, now)
}

export function hasMaterialLastSeenUpdate(match: MarketplaceMatch): boolean {
  const firstFound = timestampValue(match.first_found_at)
  const lastSeen = timestampValue(match.last_seen_at)
  return firstFound > 0 && lastSeen > 0 && lastSeen - firstFound >= MATERIAL_LAST_SEEN_UPDATE_MS
}

export function shouldShowCapturedTimestamp(match: MarketplaceMatch): boolean {
  const captured = timestampValue(match.captured_at)
  if (!captured) return false
  const firstFound = timestampValue(match.first_found_at)
  const lastSeen = timestampValue(match.last_seen_at)
  return (firstFound > 0 || lastSeen > 0) && captured !== firstFound && captured !== lastSeen
}
