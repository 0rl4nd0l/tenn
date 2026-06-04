import type { ChatMessage, Source } from './cockpit-types'
import {
  CHAT_EVIDENCE_STATE_LABELS,
  CHAT_EVIDENCE_STATE_ORDER,
  NON_EVIDENCE_SOURCE_LABELS,
  applyContextOnlyBoundaries,
  isCanonicalFinancialTruthLabelSet,
  isClaimVerifiedLabelSet,
  normalizeEvidenceLabels,
  stringArray,
  type ChatEvidenceStateCode,
} from './cockpit-evidence-taxonomy'

export type ChatEvidenceActionKey =
  | 'pull_market_data'
  | 'run_metric_extraction'
  | 'review_filing_group'

export type ChatEvidenceAction = {
  id: ChatEvidenceActionKey
  label: string
  enabled: boolean
}

export type ChatEvidenceActionability = {
  stateCodes: ChatEvidenceStateCode[]
  stateLabels: string[]
  gaps: string[]
  suggestedActions: ChatEvidenceAction[]
  hasMarketTrendClaim: boolean
  hasMarketPriceEvidence: boolean
}

const MARKET_TREND_CLAIM_RE = new RegExp(
  [
    String.raw`\b(?:price|share price|stock|market|technical|chart|rsi|macd|moving average|sma|ema|trend)\b.{0,90}\b(?:bearish|bullish|downtrend|uptrend|falling|rising|weakening|strengthening|selloff|rally|plunge|breakout|support|resistance|overbought|oversold)\b`,
    String.raw`\b(?:bearish|bullish|downtrend|uptrend)\b.{0,90}\b(?:price|trend|technical|chart|market)\b`,
    String.raw`\b(?:price trend|technical trend|trend regime|market trend)\b`,
  ].join('|'),
  'i',
)

const MARKET_GAP_RE = /\b(?:market_context|market data|market_data|price|price_data|technical|technicals|trend)\b/i
const METRIC_GAP_RE = /\b(?:financials|financial rows unavailable|metric|metric_extraction|extraction|extracted metrics)\b/i
const PRICE_SOURCE_ID_RE = /^(?:local_price|price|price_query|price_on_date|price_range|tv_indicators|tv_screener|market_update|price_horizon):/i
const PRICE_SOURCE_LABEL_RE = /\b(?:market_data|market price|price_data|technical_indicator|technical indicators)\b/i

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function addState(states: Set<ChatEvidenceStateCode>, condition: boolean, code: ChatEvidenceStateCode): void {
  if (condition) {
    states.add(code)
  }
}

function collectMessageLabels(message: ChatMessage): Set<string> {
  const analyst = message.metadata?.analyst
  const routing = asRecord(message.metadata?.routing)
  const labels: string[] = []

  for (const value of [
    ...(analyst?.evidenceLabels || []),
    analyst?.sourceCoverageStatus || '',
    ...stringArray(routing.evidence_labels),
    String(routing.source_coverage_status || ''),
  ]) {
    if (value) {
      labels.push(value)
    }
  }

  for (const source of message.sources || []) {
    labels.push(...sourceLabels(source))
  }

  return applyContextOnlyBoundaries(labels)
}

function collectMissingTerms(message: ChatMessage): string[] {
  const analyst = message.metadata?.analyst
  const routing = asRecord(message.metadata?.routing)
  const terms = [
    ...(analyst?.missingCategories || []),
    ...(analyst?.missingCategoriesBeforeRecovery || []),
    ...stringArray(routing.missing_categories_after_recovery),
    ...stringArray(routing.missing_categories_before_recovery),
    ...stringArray(routing.missing_categories),
  ]

  if (/financial rows unavailable/i.test(message.content)) {
    terms.push('financial rows unavailable')
  }
  if (/market data (?:is )?(?:missing|unavailable)|price data (?:is )?(?:missing|unavailable)/i.test(message.content)) {
    terms.push('market data missing')
  }
  return Array.from(new Set(terms.map((term) => term.trim()).filter(Boolean)))
}

function sourceLabels(source: Source): string[] {
  return Array.from(normalizeEvidenceLabels(source.evidenceLabel, source.evidenceLabels))
}

function sourceHasMarketPriceEvidence(source: Source): boolean {
  const labels = sourceLabels(source)
  const docType = String(source.docType || '').trim()
  if (
    labels.some((label) => NON_EVIDENCE_SOURCE_LABELS.has(label))
    || docType === 'operational_no_hit'
    || docType === 'runtime_failure'
  ) {
    return false
  }

  const sourceId = String(source.sourceId || '').trim()
  if (PRICE_SOURCE_ID_RE.test(sourceId)) {
    return true
  }

  const haystack = [
    source.kind,
    source.docType,
    ...labels,
  ].join(' ')

  return PRICE_SOURCE_LABEL_RE.test(haystack)
}

function sourceIsSnippetOnly(source: Source): boolean {
  return Boolean(source.snippet) && !source.url && !source.documentId && !source.sourceId && !source.path
}

function hasRepeatedFilingContext(sources: Source[]): boolean {
  const counts = new Map<string, number>()
  for (const source of sources) {
    const labels = sourceLabels(source)
    const isContextFiling = labels.includes('context_only')
      && /filing|appendix|announcement|document|asx/i.test(`${source.kind || ''} ${source.docType || ''} ${source.title || ''}`)
    if (!isContextFiling) {
      continue
    }
    const key = String(source.title || source.documentId || '').trim().toLowerCase()
    if (!key) {
      continue
    }
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return Array.from(counts.values()).some((count) => count > 1)
}

export function deriveChatEvidenceActionability(message: ChatMessage): ChatEvidenceActionability {
  const labels = collectMessageLabels(message)
  const missingTerms = collectMissingTerms(message)
  const sources = message.sources || []
  const states = new Set<ChatEvidenceStateCode>()
  const hasClaimVerified = isClaimVerifiedLabelSet(labels)
    || sources.some((source) => source.claimVerified !== false && isClaimVerifiedLabelSet(sourceLabels(source)))
  const hasFinancialTruth = isCanonicalFinancialTruthLabelSet(labels)
    || sources.some((source) => isCanonicalFinancialTruthLabelSet(sourceLabels(source)))
  const hasMarketTrendClaim = MARKET_TREND_CLAIM_RE.test(message.content)
  const hasMarketPriceEvidence = sources.some(sourceHasMarketPriceEvidence)
  const hasMarketGap = labels.has('market_data_missing')
    || missingTerms.some((term) => MARKET_GAP_RE.test(term))
    || (hasMarketTrendClaim && !hasMarketPriceEvidence)
  const hasMetricGap = labels.has('metric_extraction_missing')
    || missingTerms.some((term) => METRIC_GAP_RE.test(term))
  const hasGroundingGuard = Boolean(
    message.metadata?.analyst?.groundingGuard
    || String(asRecord(message.metadata?.routing).grounding_guard || '').trim(),
  )

  addState(states, labels.has('degraded_runtime') || Boolean(asRecord(message.metadata?.routing).provider_error), 'degraded_runtime')
  addState(states, hasMarketGap, 'market_data_missing')
  addState(states, hasMetricGap, 'metric_extraction_missing')
  addState(states, labels.has('no_hit'), 'no_hit')
  addState(states, hasClaimVerified, 'claim_verified')
  addState(states, labels.has('local_personal_data'), 'local_personal_data')
  addState(states, labels.has('memory_context'), 'memory_context')
  addState(states, labels.has('external_web_context'), 'external_web_context')
  addState(states, labels.has('unknown_unclassified') || labels.has('missing_required_evidence'), 'unresolved_source')
  addState(states, sources.some(sourceIsSnippetOnly), 'snippet_only')
  addState(states, Boolean(message.actionPreview), 'draft_only')
  addState(states, /demo|mock/i.test(`${message.content} ${sources.map((source) => source.title).join(' ')}`), 'demo_mock')

  const contextOnly = labels.has('context_only')
    || (sources.length > 0 && !hasClaimVerified && !hasFinancialTruth && !hasMarketPriceEvidence)
  addState(states, contextOnly, 'context_only')

  addState(
    states,
    hasGroundingGuard
      || hasMarketGap
      || hasMetricGap
      || labels.has('missing_required_evidence')
      || labels.has('unknown_unclassified')
      || labels.has('unsupported_or_not_verified'),
    'unsupported_or_not_verified',
  )

  const gaps: string[] = []
  if (states.has('market_data_missing')) {
    gaps.push('market_data_missing')
  }
  if (states.has('metric_extraction_missing')) {
    gaps.push('metric_extraction_missing')
  }
  if (states.has('degraded_runtime')) {
    gaps.push('degraded_runtime')
  }

  const suggestedActions: ChatEvidenceAction[] = []
  if (states.has('market_data_missing')) {
    suggestedActions.push({ id: 'pull_market_data', label: 'Pull market data', enabled: false })
  }
  if (states.has('metric_extraction_missing')) {
    suggestedActions.push({ id: 'run_metric_extraction', label: 'Run metric extraction', enabled: false })
  }
  if (hasRepeatedFilingContext(sources)) {
    suggestedActions.push({ id: 'review_filing_group', label: 'Review filing group', enabled: false })
  }

  const stateCodes = CHAT_EVIDENCE_STATE_ORDER.filter((code) => states.has(code))
  return {
    stateCodes,
    stateLabels: stateCodes.map((code) => CHAT_EVIDENCE_STATE_LABELS[code]),
    gaps,
    suggestedActions,
    hasMarketTrendClaim,
    hasMarketPriceEvidence,
  }
}
