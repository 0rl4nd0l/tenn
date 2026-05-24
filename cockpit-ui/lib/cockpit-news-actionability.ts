import type { NewsSearchResult } from '@/lib/cockpit-types'

const DEFAULT_STALE_DAYS = 14

export type NewsActionabilityReason =
  | 'DATA_MISSING'
  | 'SEARCHING'
  | 'DEGRADED'
  | 'UNRESOLVED'
  | 'STALE'
  | 'PARTIAL_SOURCE_CONTEXT'
  | 'SOURCE_READY'
  | 'DUPLICATED'

export type NewsActionabilityTone = 'ready' | 'warning' | 'error' | 'neutral'

export interface NewsActionabilityResult extends NewsSearchResult {
  publishedAtMissing?: boolean
}

export interface NewsDuplicateGroup {
  key: string
  count: number
  headline: string
}

export interface NewsReadiness {
  reason: NewsActionabilityReason
  label: string
  detail: string
  tone: NewsActionabilityTone
  stats: string[]
  duplicateGroups: NewsDuplicateGroup[]
}

export interface NewsResultReadiness {
  reason: NewsActionabilityReason
  label: string
  detail: string
  tone: NewsActionabilityTone
  duplicateCount: number
}

export function getNewsReadiness(input: {
  query: string
  isSearching: boolean
  searchError: string | null
  results: NewsActionabilityResult[] | null
  now?: Date
}): NewsReadiness {
  const query = input.query.trim()
  const now = input.now ?? new Date()

  if (!query) {
    return {
      reason: 'DATA_MISSING',
      label: 'DATA_MISSING',
      detail: 'No query has been submitted, so this screen has no news context to support an action.',
      tone: 'warning',
      stats: ['query missing'],
      duplicateGroups: [],
    }
  }

  if (input.isSearching) {
    return {
      reason: 'SEARCHING',
      label: 'SEARCHING',
      detail: 'News context is still loading. Do not treat the current view as complete.',
      tone: 'neutral',
      stats: ['request in flight'],
      duplicateGroups: [],
    }
  }

  if (input.searchError) {
    return {
      reason: 'DEGRADED',
      label: 'DEGRADED',
      detail: 'News search failed. Existing visible context is incomplete and should not be used as current evidence.',
      tone: 'error',
      stats: ['search failed'],
      duplicateGroups: [],
    }
  }

  if (input.results === null) {
    return {
      reason: 'DATA_MISSING',
      label: 'DATA_MISSING',
      detail: 'No search response has been loaded for this query yet.',
      tone: 'warning',
      stats: ['response missing'],
      duplicateGroups: [],
    }
  }

  if (input.results.length === 0) {
    return {
      reason: 'UNRESOLVED',
      label: 'UNRESOLVED',
      detail: 'The search completed but returned no matching news context.',
      tone: 'warning',
      stats: ['0 results'],
      duplicateGroups: [],
    }
  }

  const duplicateGroups = getNewsDuplicateGroups(input.results)
  const staleCount = input.results.filter((result) => isNewsResultStale(result, now)).length
  const missingDateCount = input.results.filter((result) => result.publishedAtMissing).length
  const missingUrlCount = input.results.filter((result) => !hasSourceUrl(result)).length
  const stats = [
    `${input.results.length} results`,
    `${input.results.length - missingUrlCount} source links`,
    `${missingDateCount} date missing`,
    `${staleCount} stale`,
  ]

  if (missingDateCount > 0) {
    return {
      reason: 'DATA_MISSING',
      label: 'DATA_MISSING',
      detail: 'At least one result is missing published_at, so freshness cannot be proven from existing news data.',
      tone: 'warning',
      stats,
      duplicateGroups,
    }
  }

  if (staleCount === input.results.length) {
    return {
      reason: 'STALE',
      label: 'STALE',
      detail: `All visible results are older than ${DEFAULT_STALE_DAYS} days.`,
      tone: 'warning',
      stats,
      duplicateGroups,
    }
  }

  if (duplicateGroups.length > 0) {
    return {
      reason: 'DUPLICATED',
      label: 'DUPLICATED',
      detail: 'Repeated returned items are grouped visually; treat repeated filing notices as one evidence cluster.',
      tone: 'warning',
      stats: [...stats, `${duplicateGroups.length} duplicate clusters`],
      duplicateGroups,
    }
  }

  if (missingUrlCount > 0) {
    return {
      reason: 'PARTIAL_SOURCE_CONTEXT',
      label: 'PARTIAL',
      detail: 'Some results have snippet context but no source URL, so they are not independently inspectable from this screen.',
      tone: 'warning',
      stats,
      duplicateGroups,
    }
  }

  return {
    reason: 'SOURCE_READY',
    label: 'SOURCE READY',
    detail: 'Returned news items include source links and dates. This is inspectable context, not verified financial truth.',
    tone: 'ready',
    stats,
    duplicateGroups,
  }
}

export function getNewsResultReadiness(
  result: NewsActionabilityResult,
  allResults: NewsActionabilityResult[],
  now: Date = new Date(),
): NewsResultReadiness {
  const duplicateCount = countNewsDuplicates(result, allResults)
  if (result.publishedAtMissing) {
    return {
      reason: 'DATA_MISSING',
      label: 'DATE MISSING',
      detail: 'The backend result did not include published_at, so freshness is DATA_MISSING.',
      tone: 'warning',
      duplicateCount,
    }
  }

  if (duplicateCount > 1) {
    return {
      reason: 'DUPLICATED',
      label: `DUPLICATE x${duplicateCount}`,
      detail: 'This result repeats another returned item by URL or headline/source.',
      tone: 'warning',
      duplicateCount,
    }
  }

  if (isNewsResultStale(result, now)) {
    return {
      reason: 'STALE',
      label: 'STALE',
      detail: `Published date is older than ${DEFAULT_STALE_DAYS} days.`,
      tone: 'warning',
      duplicateCount,
    }
  }

  if (!hasSourceUrl(result)) {
    return {
      reason: 'PARTIAL_SOURCE_CONTEXT',
      label: 'SNIPPET ONLY',
      detail: 'Snippet context is visible but no source URL was returned for direct inspection.',
      tone: 'warning',
      duplicateCount,
    }
  }

  return {
    reason: 'SOURCE_READY',
    label: 'SOURCE LINK',
    detail: 'A source URL is available for inspection. This does not mark the claim as verified.',
    tone: 'ready',
    duplicateCount,
  }
}

function hasSourceUrl(result: NewsActionabilityResult): boolean {
  return Boolean(result.url?.trim())
}

function isNewsResultStale(result: NewsActionabilityResult, now: Date): boolean {
  if (result.publishedAtMissing) {
    return false
  }
  const timestamp = result.date.getTime()
  if (!Number.isFinite(timestamp)) {
    return false
  }
  return now.getTime() - timestamp > DEFAULT_STALE_DAYS * 24 * 60 * 60 * 1000
}

function countNewsDuplicates(result: NewsActionabilityResult, allResults: NewsActionabilityResult[]): number {
  const key = newsDuplicateKey(result)
  return allResults.filter((candidate) => newsDuplicateKey(candidate) === key).length
}

export function getNewsDuplicateGroups(results: NewsActionabilityResult[]): NewsDuplicateGroup[] {
  const groups = new Map<string, { count: number; headline: string }>()
  for (const result of results) {
    const key = newsDuplicateKey(result)
    const existing = groups.get(key)
    if (existing) {
      existing.count += 1
    } else {
      groups.set(key, { count: 1, headline: result.headline })
    }
  }
  return Array.from(groups.entries())
    .filter(([, group]) => group.count > 1)
    .map(([key, group]) => ({ key, count: group.count, headline: group.headline }))
}

function newsDuplicateKey(result: NewsActionabilityResult): string {
  const url = result.url?.trim().toLowerCase()
  if (url) {
    return `url:${url.split('#')[0]}`
  }
  return `headline:${normalizeText(result.source)}:${normalizeText(result.headline)}`
}

function normalizeText(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ')
}
