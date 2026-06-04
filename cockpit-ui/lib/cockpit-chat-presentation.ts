import type { ActionPreview, ChatMessage } from './cockpit-types'
import {
  deriveChatEvidenceActionability,
  type ChatEvidenceAction,
  type ChatEvidenceActionKey,
} from './cockpit-chat-actionability'
import {
  isCanonicalFinancialTruthLabelSet,
  isClaimVerifiedLabelSet,
  normalizeEvidenceLabels,
  stringArray,
} from './cockpit-evidence-taxonomy'

export type ChatPresentationActionKind = 'open_sources'

export type ChatPresentationAction = ChatEvidenceAction & {
  kind?: ChatPresentationActionKind
  onClick?: () => void
}

export type SuggestedChatActionRequest = {
  actionKey: ChatEvidenceActionKey
  label: string
  ticker: string
}

export type ChatPresentationOptions = {
  onSuggestedAction?: (action: SuggestedChatActionRequest) => void
}

export type ChatAnalystShellModel = {
  shouldRender: boolean
  entityLabel: string | null
  answerType: string
  trustLabel: string
  sourceCount: number
  toolCount: number
  latestSourceDate: string | null
  evidenceKinds: string[]
  sourceSummaryLabel: string | null
  keyFacts: string[]
  gaps: string[]
  sourceWarnings: string[]
  evidenceStateLabels: string[]
  nextActions: ChatPresentationAction[]
}

export type ActionPreviewPresentation = {
  riskLabels: string[]
  whyLabel: string | null
  impactLabel: string
  argsSummary: string
  safetyLabel: string
}

export type ChatPresentationModel = {
  shell: ChatAnalystShellModel
  actionPreview: ActionPreviewPresentation | null
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

export function compactPresentationLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function extractTickerFromAction(message: ChatMessage): string | null {
  const args = asRecord(message.actionPreview?.args)
  const ticker = String(args.ticker || args.symbol || '').trim().toUpperCase()
  return /^[A-Z0-9]{2,6}$/.test(ticker) ? ticker : null
}

function actionableTicker(value: string | null): string | null {
  const ticker = String(value || '').trim().toUpperCase()
  return /^[A-Z0-9]{2,6}$/.test(ticker) ? ticker : null
}

function extractTextGaps(content: string): string[] {
  const gaps: string[] = []
  const unresolved = content.match(/Unresolved evidence gaps:\s*([^\n.]+)/i)
  if (unresolved?.[1]) {
    gaps.push(...unresolved[1].split(',').map((item) => item.trim()).filter(Boolean))
  }
  const dataInsufficient = content.match(/Data insufficient:\s*([^\n]+)/i)
  if (dataInsufficient?.[1]) {
    gaps.push(dataInsufficient[1].trim())
  }
  if (/financial rows unavailable/i.test(content)) {
    gaps.push('financial rows unavailable')
  }
  return Array.from(new Set(gaps))
}

function extractKeyFacts(content: string): string[] {
  const lines = content.split('\n')
  const start = lines.findIndex((line) => /^\s*(?:#{1,4}\s*)?(?:key facts?|key takeaways?|takeaways?)\s*:?\s*$/i.test(line))
  if (start < 0) {
    return []
  }
  const facts: string[] = []
  for (const rawLine of lines.slice(start + 1)) {
    const line = rawLine.trim()
    if (!line) {
      if (facts.length > 0) break
      continue
    }
    if (/^\s*(?:#{1,4}\s*)?[A-Z][A-Za-z ]+\s*:?\s*$/.test(line) && facts.length > 0) {
      break
    }
    const cleaned = line.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, '').trim()
    if (cleaned) {
      facts.push(cleaned)
    }
    if (facts.length >= 5) break
  }
  return facts
}

function latestPublishedDate(message: ChatMessage): string | null {
  const dates = (message.sources || [])
    .map((source) => source.publishedAt)
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value))
    .filter((value) => !Number.isNaN(value.getTime()))
    .sort((a, b) => b.getTime() - a.getTime())
  return dates[0]?.toISOString().slice(0, 10) ?? null
}

function evidenceKindLabels(message: ChatMessage): string[] {
  const labels = new Set<string>()
  for (const source of message.sources || []) {
    const raw = source.kind || source.docType || ''
    if (!raw) continue
    if (raw === 'document' || /financial|annual|quarter|filing|appendix/i.test(raw)) {
      labels.add('filings')
    } else if (raw === 'news' || /news/i.test(raw)) {
      labels.add('news')
    } else if (raw === 'web') {
      labels.add('web context')
    } else if (raw === 'context' || raw === 'rag') {
      labels.add('local context')
    } else {
      labels.add(compactPresentationLabel(raw).toLowerCase())
    }
  }
  return Array.from(labels).slice(0, 4)
}

function sourceStatusWarnings(sourceStatus: Record<string, unknown> | undefined): string[] {
  if (!sourceStatus) {
    return []
  }
  return Object.entries(sourceStatus).flatMap(([source, status]) => {
    if (typeof status === 'string') {
      return status && status.toLowerCase() !== 'ok'
        ? [`${compactPresentationLabel(source)}: ${compactPresentationLabel(status)}`]
        : []
    }
    const record = asRecord(status)
    const value = String(record.status || '').trim()
    if (value && value.toLowerCase() !== 'ok') {
      return [`${compactPresentationLabel(source)}: ${compactPresentationLabel(value)}`]
    }
    if (record.ok === false) {
      return [`${compactPresentationLabel(source)}: not ok`]
    }
    return []
  })
}

export function buildChatPresentationModel(
  message: ChatMessage,
  options: ChatPresentationOptions = {},
): ChatPresentationModel {
  return {
    shell: buildAnalystShell(message, options),
    actionPreview: message.actionPreview
      ? deriveActionPreviewPresentation(message.actionPreview)
      : null,
  }
}

function buildAnalystShell(
  message: ChatMessage,
  options: ChatPresentationOptions,
): ChatAnalystShellModel {
  const analyst = message.metadata?.analyst
  const routing = asRecord(message.metadata?.routing)
  const routeTicker = String(asRecord(routing.entities).primary_ticker || '').trim().toUpperCase()
  const entityLabel =
    analyst?.entity
    || analyst?.ticker
    || routeTicker
    || extractTickerFromAction(message)
    || null
  const suggestedTicker =
    actionableTicker(analyst?.ticker || null)
    || actionableTicker(routeTicker)
    || actionableTicker(extractTickerFromAction(message))
    || actionableTicker(entityLabel)
  const sourceCount = message.sources?.length || 0
  const toolCount = message.toolTraces?.length || 0
  const evidenceActionability = deriveChatEvidenceActionability(message)
  const missingFromMetadata = analyst?.missingCategories || stringArray(routing.missing_categories_after_recovery)
  const gaps = Array.from(new Set([
    ...missingFromMetadata,
    ...extractTextGaps(message.content),
    ...evidenceActionability.gaps,
  ]))
  const sourceWarnings = sourceStatusWarnings(analyst?.sourceStatus || asRecord(routing.source_status))
  const responseClassification = analyst?.responseClassification || String(routing.response_classification || '')
  const groundingGuard = analyst?.groundingGuard || String(routing.grounding_guard || '')
  const sourceCoverageStatus =
    analyst?.sourceCoverageStatus || String(routing.source_coverage_status || '')
  const rawEvidenceLabels = [
    ...(analyst?.evidenceLabels || []),
    ...stringArray(routing.evidence_labels),
  ]
  const rawSourceLabels = (message.sources || []).flatMap((source) => [
    source.evidenceLabel || '',
    ...(source.evidenceLabels || []),
  ])
  const effectiveEvidenceLabels = normalizeEvidenceLabels(
    rawEvidenceLabels,
    sourceCoverageStatus,
    rawSourceLabels,
  )
  const evidenceLabels = Array.from(effectiveEvidenceLabels)
  const hasEvidenceLabel = (label: string) => (
    effectiveEvidenceLabels.has(label)
  )
  const hasClaimVerifiedEvidence = evidenceActionability.stateCodes.includes('claim_verified')
    && isClaimVerifiedLabelSet(effectiveEvidenceLabels)
  const hasFinancialTruthEvidence = isCanonicalFinancialTruthLabelSet(effectiveEvidenceLabels)
  const hasMeaningfulSourceCoverage = Boolean(
    sourceCoverageStatus && sourceCoverageStatus !== 'no_visible_sources',
  )
  const sufficientForAnalysis =
    analyst?.sufficientForAnalysis
    ?? (typeof routing.sufficient_for_analysis === 'boolean' ? routing.sufficient_for_analysis : null)
  const keyFacts = extractKeyFacts(message.content)
  const hasRoutingMetadata = Boolean(
    analyst?.intent
    || analyst?.sourcePlan?.length
    || responseClassification
    || groundingGuard
    || sourceWarnings.length
    || gaps.length
    || evidenceLabels.length
    || hasMeaningfulSourceCoverage
    || sufficientForAnalysis === false
  )
  const shouldRender = Boolean(
    message.actionPreview
    || sourceCount > 0
    || toolCount > 0
    || hasRoutingMetadata
    || keyFacts.length > 0
  )

  let answerType = 'General model answer'
  if (message.actionPreview) {
    answerType = 'Action proposal'
  } else if (hasEvidenceLabel('degraded_runtime')) {
    answerType = 'Degraded runtime'
  } else if (groundingGuard) {
    answerType = 'Data missing'
  } else if (sufficientForAnalysis === false || gaps.length > 0) {
    answerType = 'Partial evidence'
  } else if (hasClaimVerifiedEvidence) {
    answerType = 'Evidence-bound'
  } else if (hasFinancialTruthEvidence) {
    answerType = 'Financial truth'
  } else if (sourceCount > 0) {
    answerType = 'Context only'
  } else if (responseClassification) {
    answerType = compactPresentationLabel(responseClassification)
  }

  let trustLabel = 'No visible sources'
  if (message.actionPreview?.requiresConfirmation) {
    trustLabel = 'Confirmation required'
  } else if (hasEvidenceLabel('degraded_runtime')) {
    trustLabel = 'Degraded runtime'
  } else if (evidenceActionability.stateCodes.includes('market_data_missing')) {
    trustLabel = 'Market data missing'
  } else if (evidenceActionability.stateCodes.includes('metric_extraction_missing')) {
    trustLabel = 'Metrics missing'
  } else if (evidenceActionability.stateCodes.includes('unsupported_or_not_verified')) {
    trustLabel = 'Unsupported / not verified'
  } else if (groundingGuard) {
    trustLabel = 'Unsupported claim blocked'
  } else if (sufficientForAnalysis === false || gaps.length > 0) {
    trustLabel = 'Evidence gaps visible'
  } else if (hasClaimVerifiedEvidence) {
    trustLabel = 'Claim-supported'
  } else if (hasFinancialTruthEvidence) {
    trustLabel = 'Financial truth evidence'
  } else if (hasEvidenceLabel('no_hit')) {
    trustLabel = 'No-hit audit'
  } else if (hasEvidenceLabel('local_personal_data')) {
    trustLabel = 'Local personal data'
  } else if (sourceCount > 0) {
    trustLabel = 'Context sources only'
  }

  let sourceSummaryLabel: string | null = null
  if (hasEvidenceLabel('degraded_runtime')) {
    sourceSummaryLabel = 'Runtime degraded'
  } else if (evidenceActionability.stateCodes.includes('market_data_missing')) {
    sourceSummaryLabel = 'Market evidence missing'
  } else if (evidenceActionability.stateCodes.includes('metric_extraction_missing')) {
    sourceSummaryLabel = 'Metric extraction missing'
  } else if (groundingGuard || hasEvidenceLabel('missing_required_evidence') || gaps.length > 0) {
    sourceSummaryLabel = 'Evidence incomplete'
  } else if (hasClaimVerifiedEvidence) {
    sourceSummaryLabel = 'Verified sources'
  } else if (hasFinancialTruthEvidence) {
    sourceSummaryLabel = 'Financial truth numeric context'
  } else if (hasEvidenceLabel('local_personal_data')) {
    sourceSummaryLabel = 'Local holdings'
  } else if (hasEvidenceLabel('memory_context')) {
    sourceSummaryLabel = 'Memory context'
  } else if (hasEvidenceLabel('no_hit')) {
    sourceSummaryLabel = 'No relevant source found'
  } else if (sourceCount > 0) {
    sourceSummaryLabel = 'Context sources'
  }

  const nextActions: ChatPresentationAction[] = []
  const suggestedActionIds = new Set(evidenceActionability.suggestedActions.map((action) => action.id))
  if (sourceCount > 0) {
    nextActions.push({ label: 'Review evidence', enabled: true, kind: 'open_sources' })
    nextActions.push({ label: 'Verify against evidence', enabled: false })
  }
  if (gaps.some((gap) => /news|announcement|recent|market_context/i.test(gap))) {
    nextActions.push({ label: 'Check recent news', enabled: false })
  }
  if (
    gaps.some((gap) => /financial|rows/i.test(gap))
    && !suggestedActionIds.has('run_metric_extraction')
  ) {
    nextActions.push({ label: 'Backfill financials', enabled: false })
  }
  for (const action of evidenceActionability.suggestedActions) {
    if (!nextActions.some((item) => item.label === action.label)) {
      if (action.id === 'review_filing_group') {
        nextActions.push({ label: action.label, enabled: true, kind: 'open_sources' })
        continue
      }
      if (suggestedTicker && options.onSuggestedAction) {
        nextActions.push({
          label: action.label,
          enabled: true,
          onClick: () => options.onSuggestedAction?.({
            actionKey: action.id,
            label: action.label,
            ticker: suggestedTicker,
          }),
        })
        continue
      }
      nextActions.push(action)
    }
  }
  return {
    shouldRender,
    entityLabel,
    answerType,
    trustLabel,
    sourceCount,
    toolCount,
    latestSourceDate: analyst?.dataFreshness || latestPublishedDate(message),
    evidenceKinds: evidenceKindLabels(message),
    sourceSummaryLabel,
    keyFacts,
    gaps,
    sourceWarnings,
    evidenceStateLabels: evidenceActionability.stateLabels,
    nextActions,
  }
}

function actionArgsSummary(args: Record<string, unknown>): string {
  const entries = Object.entries(args)
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
    .slice(0, 5)
  if (!entries.length) {
    return 'No parameters supplied'
  }
  return entries.map(([key, value]) => `${key}=${String(value)}`).join(', ')
}

function actionRiskLabels(actionPreview: ActionPreview): string[] {
  const id = actionPreview.id.toLowerCase()
  const labels = [actionPreview.requiresConfirmation ? 'Confirmation required' : 'No confirmation required']
  if (actionPreview.isMutating || /ingest|backfill|create|add|save|write|thesis|memory|update|rebuild/.test(id)) {
    labels.push(/thesis|memory/.test(id) ? 'Memory write' : 'Mutates state')
  }
  if ((actionPreview.timeoutSeconds || 0) > 60 || /ingest|backfill|analysis|rebuild|scan/.test(id)) {
    labels.push('Long job')
  }
  return Array.from(new Set(labels))
}

export function deriveActionPreviewPresentation(
  actionPreview: ActionPreview,
): ActionPreviewPresentation {
  return {
    riskLabels: actionRiskLabels(actionPreview),
    whyLabel: actionPreview.description || null,
    impactLabel: actionPreview.impact
      || actionPreview.scope
      || 'Run the named backend action with the parameters shown below.',
    argsSummary: actionArgsSummary(actionPreview.args),
    safetyLabel: 'No action runs until you confirm.',
  }
}
