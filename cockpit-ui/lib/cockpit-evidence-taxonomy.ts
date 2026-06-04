export type ChatEvidenceStateCode =
  | 'claim_verified'
  | 'context_only'
  | 'no_hit'
  | 'market_data_missing'
  | 'metric_extraction_missing'
  | 'degraded_runtime'
  | 'local_personal_data'
  | 'memory_context'
  | 'external_web_context'
  | 'demo_mock'
  | 'unresolved_source'
  | 'snippet_only'
  | 'draft_only'
  | 'unsupported_or_not_verified'

export const CHAT_EVIDENCE_STATE_LABELS: Record<ChatEvidenceStateCode, string> = {
  claim_verified: 'Claim verified',
  context_only: 'Context only',
  no_hit: 'No hit',
  market_data_missing: 'Market data missing',
  metric_extraction_missing: 'Metric extraction missing',
  degraded_runtime: 'Degraded runtime',
  local_personal_data: 'Local personal data',
  memory_context: 'Memory context',
  external_web_context: 'External web context',
  demo_mock: 'Demo/mock',
  unresolved_source: 'Unresolved source',
  snippet_only: 'Snippet only',
  draft_only: 'Draft only',
  unsupported_or_not_verified: 'Unsupported / not verified',
}

export const CHAT_EVIDENCE_STATE_ORDER: ChatEvidenceStateCode[] = [
  'degraded_runtime',
  'market_data_missing',
  'metric_extraction_missing',
  'unsupported_or_not_verified',
  'no_hit',
  'claim_verified',
  'context_only',
  'local_personal_data',
  'memory_context',
  'external_web_context',
  'demo_mock',
  'unresolved_source',
  'snippet_only',
  'draft_only',
]

export const NON_EVIDENCE_SOURCE_LABELS = new Set([
  'no_hit',
  'missing_required_evidence',
  'degraded_runtime',
  'insufficient_for_recent_news',
  'market_data_missing',
  'metric_extraction_missing',
  'unsupported_or_not_verified',
])

const CONTEXT_ONLY_SOURCE_LABELS = new Set([
  'context_only',
  'memory_context',
  'external_web_context',
  'unknown_unclassified',
])

const CANONICAL_FINANCIAL_TRUTH_BLOCKING_LABELS = new Set([
  ...CONTEXT_ONLY_SOURCE_LABELS,
  ...NON_EVIDENCE_SOURCE_LABELS,
  'local_personal_data',
  'local_news_context',
  'operational_trace',
])

function labelsFromIterable(labels: Iterable<string>): Set<string> {
  const normalized = new Set<string>()
  for (const label of labels) {
    const text = String(label || '').trim()
    if (text) {
      normalized.add(text)
    }
  }
  return normalized
}

export function stringArray(value: unknown): string[] {
  if (typeof value === 'string') {
    return value.trim() ? [value.trim()] : []
  }
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

export function isContextOnlyLabelSet(labels: Iterable<string>): boolean {
  const labelSet = labelsFromIterable(labels)
  return Array.from(CONTEXT_ONLY_SOURCE_LABELS).some((label) => labelSet.has(label))
    || Array.from(NON_EVIDENCE_SOURCE_LABELS).some((label) => labelSet.has(label))
}

export function isClaimVerifiedLabelSet(labels: Iterable<string>): boolean {
  const labelSet = labelsFromIterable(labels)
  return labelSet.has('claim_verified') && !isContextOnlyLabelSet(labelSet)
}

export function isCanonicalFinancialTruthLabelSet(labels: Iterable<string>): boolean {
  const labelSet = labelsFromIterable(labels)
  if (!labelSet.has('financial_truth')) {
    return false
  }
  return !Array.from(CANONICAL_FINANCIAL_TRUTH_BLOCKING_LABELS).some((label) => labelSet.has(label))
}

export function applyContextOnlyBoundaries(labels: Iterable<string>): Set<string> {
  const effective = labelsFromIterable(labels)
  if (isContextOnlyLabelSet(effective)) {
    effective.add('context_only')
  }
  if (!isClaimVerifiedLabelSet(effective)) {
    effective.delete('claim_verified')
  }
  if (!isCanonicalFinancialTruthLabelSet(effective)) {
    effective.delete('financial_truth')
    effective.delete('financial_truth_numeric')
  }
  return effective
}

export function normalizeEvidenceLabels(...values: unknown[]): Set<string> {
  const labels: string[] = []
  for (const value of values) {
    labels.push(...stringArray(value))
  }
  return applyContextOnlyBoundaries(labels)
}
