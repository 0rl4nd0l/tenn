'use client'

import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Info,
  Maximize2,
  Rocket,
  ShieldCheck,
} from 'lucide-react'
import type { ChatMessage as ChatMessageType } from '@/lib/cockpit-types'
import { deriveChatEvidenceActionability } from '@/lib/cockpit-chat-actionability'
import {
  isCanonicalFinancialTruthLabelSet,
  isClaimVerifiedLabelSet,
  normalizeEvidenceLabels,
} from '@/lib/cockpit-evidence-taxonomy'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface TerminalMessageProps {
  message: ChatMessageType
  isStreaming?: boolean
  showSources?: boolean
  codexDeployStatus?: string | null
  onConfirmAction?: (actionPreview: ChatMessageType['actionPreview']) => void
  onCancelAction?: (actionPreview: ChatMessageType['actionPreview']) => void
  onDeployCodexFlag?: (reportId: string) => void
}

function formatDurationLabel(durationMs: number): string {
  const roundedMs = Math.max(0, Math.round(durationMs))

  if (roundedMs < 1000) {
    return `${roundedMs}ms`
  }

  if (roundedMs < 10_000) {
    return `${(roundedMs / 1000).toFixed(1)}s`
  }

  if (roundedMs < 60_000) {
    return `${Math.round(roundedMs / 1000)}s`
  }

  const totalSeconds = Math.round(roundedMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  if (seconds === 0) {
    return `${minutes}m`
  }

  return `${minutes}m ${seconds}s`
}

type AnalystShell = {
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
  nextActions: Array<{ label: string; enabled: boolean; onClick?: () => void }>
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function compactLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => String(item || '').trim()).filter(Boolean)
    : []
}

function extractTickerFromAction(message: ChatMessageType): string | null {
  const args = asRecord(message.actionPreview?.args)
  const ticker = String(args.ticker || args.symbol || '').trim().toUpperCase()
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

function latestPublishedDate(message: ChatMessageType): string | null {
  const dates = (message.sources || [])
    .map((source) => source.publishedAt)
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value))
    .filter((value) => !Number.isNaN(value.getTime()))
    .sort((a, b) => b.getTime() - a.getTime())
  return dates[0]?.toISOString().slice(0, 10) ?? null
}

function evidenceKindLabels(message: ChatMessageType): string[] {
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
      labels.add(compactLabel(raw).toLowerCase())
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
        ? [`${compactLabel(source)}: ${compactLabel(status)}`]
        : []
    }
    const record = asRecord(status)
    const value = String(record.status || '').trim()
    if (value && value.toLowerCase() !== 'ok') {
      return [`${compactLabel(source)}: ${compactLabel(value)}`]
    }
    if (record.ok === false) {
      return [`${compactLabel(source)}: not ok`]
    }
    return []
  })
}

function buildAnalystShell(
  message: ChatMessageType,
  openSources: () => void,
): AnalystShell {
  const analyst = message.metadata?.analyst
  const routing = asRecord(message.metadata?.routing)
  const entityLabel =
    analyst?.entity
    || analyst?.ticker
    || String(asRecord(routing.entities).primary_ticker || '').trim().toUpperCase()
    || extractTickerFromAction(message)
    || null
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
    || extractKeyFacts(message.content).length > 0
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
    answerType = compactLabel(responseClassification)
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

  const nextActions: AnalystShell['nextActions'] = []
  if (sourceCount > 0) {
    nextActions.push({ label: 'Review evidence', enabled: true, onClick: openSources })
    nextActions.push({ label: 'Verify against evidence', enabled: false })
  }
  if (gaps.some((gap) => /news|announcement|recent|market_context/i.test(gap))) {
    nextActions.push({ label: 'Check recent news', enabled: false })
  }
  if (gaps.some((gap) => /financial|rows/i.test(gap))) {
    nextActions.push({ label: 'Backfill financials', enabled: false })
  }
  for (const action of evidenceActionability.suggestedActions) {
    if (!nextActions.some((item) => item.label === action.label)) {
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
    keyFacts: extractKeyFacts(message.content),
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

function actionRiskLabels(actionPreview: NonNullable<ChatMessageType['actionPreview']>): string[] {
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

export function TerminalMessage({
  message,
  isStreaming,
  showSources = true,
  codexDeployStatus,
  onConfirmAction,
  onCancelAction,
  onDeployCodexFlag,
}: TerminalMessageProps) {
  const [sourcesExpanded, setSourcesExpanded] = useState(Boolean(showSources))
  const [copied, setCopied] = useState(false)
  const [rawDumpExpanded, setRawDumpExpanded] = useState(false)
  const [chartDialogOpen, setChartDialogOpen] = useState(false)
  const [autoOpenedFilestatsChart, setAutoOpenedFilestatsChart] = useState(false)
  const analystShell = buildAnalystShell(message, () => setSourcesExpanded(true))

  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const codexDeployReportId = message.metadata?.codexDeploy?.reportId
  const effectiveCodexDeployStatus = codexDeployStatus || 'queued'
  const codexDeployDisabled = ['launching', 'running', 'completed'].includes(effectiveCodexDeployStatus)
  const rawLatencyMs = message.metadata?.latencyMs
  const latencyMs =
    typeof rawLatencyMs === 'number' && Number.isFinite(rawLatencyMs)
      ? rawLatencyMs
      : null
  const responseTimingLabel = latencyMs !== null ? formatDurationLabel(latencyMs) : null

  const timestamp = message.timestamp.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatSourceScore = (score: number | undefined): string => {
    const numericScore = Number(score)
    if (!Number.isFinite(numericScore)) {
      return '[--]'
    }
    const pct = Math.max(0, Math.min(100, numericScore * 100))
    return `[${pct.toFixed(0)}%]`
  }

  const formatSourceDate = (value: string | undefined): string | null => {
    if (!value) {
      return null
    }

    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
      return value.slice(0, 10) || value
    }

    return parsed.toISOString().slice(0, 10)
  }

  const isFilestatsDump = message.content.includes('Company Data Dump:')
  const hasFilestatsChart = Boolean(message.chart && /filestats/i.test(message.chart.title || ''))
  const shouldCollapseRawDump = isFilestatsDump && hasFilestatsChart
  const filestatsPreview = message.content.split('\n').slice(0, 10).join('\n')

  useEffect(() => {
    if (hasFilestatsChart && !autoOpenedFilestatsChart) {
      setChartDialogOpen(true)
      setAutoOpenedFilestatsChart(true)
    }
  }, [autoOpenedFilestatsChart, hasFilestatsChart])

  useEffect(() => {
    setSourcesExpanded(Boolean(showSources))
  }, [message.id, showSources])

  // Parse content for code blocks and format
  const formatContent = (content: string) => {
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    const matches = Array.from(content.matchAll(codeBlockRegex))

    for (const match of matches) {
      const matchIndex = match.index ?? 0
      // Add text before code block
      if (matchIndex > lastIndex) {
        parts.push(
          <span key={`text-${lastIndex}`}>
            {formatInlineContent(content.slice(lastIndex, matchIndex))}
          </span>
        )
      }
      
      // Add code block
      const lang = match[1] || 'text'
      const code = match[2]
      parts.push(
        <div key={`code-${matchIndex}`} className="my-2 rounded border border-blue-500/30 bg-black/40 overflow-hidden">
          <div className="flex items-center justify-between px-2 py-1 border-b border-blue-500/30 text-[10px] text-blue-400/60">
            <span>{lang}</span>
          </div>
          <pre className="p-2 overflow-x-auto text-base">
            <code className="text-white">{code}</code>
          </pre>
        </div>
      )
      
      lastIndex = matchIndex + match[0].length
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {formatInlineContent(content.slice(lastIndex))}
        </span>
      )
    }

    return parts.length > 0 ? parts : formatInlineContent(content)
  }

  const formatInlineContent = (text: string) => {
    // Handle inline code
    return text.split(/(`[^`]+`)/).map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-white text-base">
            {part.slice(1, -1)}
          </code>
        )
      }
      // Handle bold
      return part.split(/(\*\*[^*]+\*\*)/).map((subpart, j) => {
        if (subpart.startsWith('**') && subpart.endsWith('**')) {
          return <strong key={`${i}-${j}`} className="text-white font-semibold">{subpart.slice(2, -2)}</strong>
        }
        return subpart
      })
    })
  }

  if (isUser) {
    return (
      <div className="group rounded-md border border-transparent px-2 py-1 transition-colors duration-150 hover:border-border/40 hover:bg-white/[0.02]">
        <div className="flex items-start gap-2">
          <span className="text-blue-400 shrink-0">{`>`}</span>
          <span className="text-white text-lg whitespace-pre-wrap break-words">{message.content}</span>
        </div>
        <div className="text-[10px] text-blue-400/60 ml-4 opacity-70 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-opacity">
          [{timestamp}]
        </div>
      </div>
    )
  }

  if (isSystem) {
    return (
      <div className="rounded-md border border-[oklch(0.78_0.17_80/0.35)] bg-[oklch(0.78_0.17_80/0.08)] px-2 py-1 text-amber-300 text-xs transition-colors duration-150 hover:bg-[oklch(0.78_0.17_80/0.12)]">
        <span className="text-amber-500">[SYSTEM]</span>{' '}
        <span className="whitespace-pre-wrap break-words">
          {formatContent(message.content)}
        </span>
        {codexDeployReportId && onDeployCodexFlag ? (
          <div className="mt-2 rounded-md border border-amber-500/30 bg-black/20 p-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.14em] text-amber-200">
                <AlertTriangle className="h-3 w-3" />
                Potential issue detected
              </span>
              <span className="font-mono text-[11px] text-amber-100/80">
                report: {codexDeployReportId}
              </span>
              <span className="font-mono text-[11px] text-amber-100/65">
                status: {effectiveCodexDeployStatus}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {message.metadata?.codexDeploy?.readApiPath ? (
                <span className="rounded border border-amber-400/25 px-2 py-1 font-mono text-[11px] text-amber-100/75">
                  View diagnostic
                </span>
              ) : null}
              {message.metadata?.codexDeploy?.promptPath ? (
                <span className="rounded border border-amber-400/25 px-2 py-1 font-mono text-[11px] text-amber-100/75">
                  Draft repair prompt
                </span>
              ) : null}
            <button
              type="button"
              disabled={codexDeployDisabled}
              onClick={() => onDeployCodexFlag(codexDeployReportId)}
              className="inline-flex items-center gap-1 rounded border border-amber-400/40 bg-amber-500/10 px-2 py-1 font-mono text-[11px] text-amber-100 transition-colors hover:bg-amber-500/20 disabled:cursor-default disabled:opacity-60"
            >
              <Rocket className="h-3 w-3" />
              {effectiveCodexDeployStatus === 'completed'
                ? 'Codex completed'
                : effectiveCodexDeployStatus === 'running' || effectiveCodexDeployStatus === 'launching'
                  ? 'Codex running'
                : 'Deploy Codex'}
            </button>
            </div>
          </div>
        ) : null}
      </div>
    )
  }

  // Assistant message
  return (
    <div className="group mt-2 mb-3 rounded-md border border-transparent px-2 py-1 transition-colors duration-150 hover:border-border/40 hover:bg-white/[0.02]">
      {/* Response and tool timings */}
      {(responseTimingLabel || (message.toolTraces && message.toolTraces.length > 0)) && (
        <div className="mb-1 ml-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-blue-400/70">
          {responseTimingLabel && <span>[response: {responseTimingLabel}]</span>}
          {message.toolTraces?.map((trace, i) => (
            <span key={i}>
              [{trace.tool}: {trace.durationMs}ms]
            </span>
          ))}
        </div>
      )}

      {analystShell.shouldRender && (
        <div className="ml-4 mb-2 rounded-md border border-blue-500/20 bg-blue-500/[0.04] p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            {analystShell.entityLabel ? (
              <span className="rounded border border-emerald-500/35 bg-emerald-500/10 px-2 py-0.5 font-mono text-xs text-emerald-200">
                Entity: {analystShell.entityLabel}
              </span>
            ) : null}
            <span className="rounded border border-blue-500/35 bg-blue-500/10 px-2 py-0.5 font-mono text-xs text-blue-200">
              {analystShell.answerType}
            </span>
            <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-xs text-cyan-100">
              Sources: {analystShell.sourceCount}
            </span>
            {analystShell.toolCount > 0 ? (
              <span className="rounded border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 font-mono text-xs text-violet-100">
                Tools: {analystShell.toolCount}
              </span>
            ) : null}
            {analystShell.latestSourceDate ? (
              <span className="rounded border border-zinc-600 bg-zinc-900 px-2 py-0.5 font-mono text-xs text-zinc-300">
                Updated: {analystShell.latestSourceDate}
              </span>
            ) : null}
            <span className="rounded border border-zinc-600 bg-zinc-900 px-2 py-0.5 font-mono text-xs text-zinc-300">
              Trust: {analystShell.trustLabel}
            </span>
          </div>

          {analystShell.keyFacts.length > 0 ? (
            <div className="mt-3 rounded border border-emerald-500/20 bg-emerald-500/[0.05] p-2">
              <div className="mb-1 flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.14em] text-emerald-300/80">
                <ShieldCheck className="h-3 w-3" />
                Key facts
              </div>
              <ul className="space-y-1 text-sm text-emerald-50/90">
                {analystShell.keyFacts.map((fact, index) => (
                  <li key={`${fact}-${index}`} className="flex gap-2">
                    <span className="text-emerald-400">{`>`}</span>
                    <span>{fact}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-blue-100/80">
            <span className="inline-flex items-center gap-1">
              <Info className="h-3 w-3" />
              Evidence: {analystShell.evidenceKinds.length ? analystShell.evidenceKinds.join(' + ') : 'No visible sources'}
            </span>
            {analystShell.sourceSummaryLabel ? <span>{analystShell.sourceSummaryLabel}</span> : null}
          </div>

          {analystShell.evidenceStateLabels.length > 0 ? (
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-blue-300/70">
                Evidence state
              </span>
              {analystShell.evidenceStateLabels.map((label) => (
                <span key={label} className="rounded border border-zinc-600 bg-zinc-900 px-2 py-0.5 font-mono text-[11px] text-zinc-200">
                  {label}
                </span>
              ))}
            </div>
          ) : null}

          {(analystShell.gaps.length > 0 || analystShell.sourceWarnings.length > 0) ? (
            <div className="mt-3 rounded border border-amber-500/30 bg-amber-500/[0.08] p-2 text-amber-100">
              <div className="mb-1 flex items-center gap-1 font-mono text-[11px] uppercase tracking-[0.14em] text-amber-300">
                <AlertTriangle className="h-3 w-3" />
                Missing data / gaps
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[...analystShell.gaps, ...analystShell.sourceWarnings].map((gap) => (
                  <span key={gap} className="rounded border border-amber-500/30 bg-black/20 px-2 py-0.5 font-mono text-[11px]">
                    {gap}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {analystShell.nextActions.length > 0 ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-blue-300/70">
                Suggested next
              </span>
              {analystShell.nextActions.map((action) => action.enabled && action.onClick ? (
                <button
                  key={action.label}
                  type="button"
                  onClick={action.onClick}
                  className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 font-mono text-[11px] text-blue-100 transition-colors hover:bg-blue-500/20"
                >
                  {action.label}
                </button>
              ) : (
                <span
                  key={action.label}
                  className={action.enabled
                    ? 'rounded border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 font-mono text-[11px] text-blue-100'
                    : 'rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 font-mono text-[11px] text-zinc-500'}
                >
                  {action.enabled ? action.label : `${action.label} (not connected)`}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}

      {/* Main content */}
      <div className="flex items-start gap-2">
        <span className="text-blue-400 shrink-0">{`$`}</span>
        {shouldCollapseRawDump ? (
          <div className="flex-1 space-y-2">
            <div className="rounded-md border border-cyan-500/30 bg-cyan-500/8 p-3">
              <div className="text-sm uppercase tracking-[0.16em] text-cyan-300/90">Filestats Visual Mode</div>
              <div className="mt-1 text-sm text-cyan-100/90">
                Interactive dashboard rendered below. Raw dump is collapsed for readability.
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setChartDialogOpen(true)}
                  className="inline-flex items-center gap-1 rounded border border-cyan-400/50 bg-cyan-500/12 px-2 py-1 text-xs text-cyan-100 hover:bg-cyan-500/20 transition-colors"
                >
                  <Maximize2 className="h-3 w-3" />
                  Open dashboard fullscreen
                </button>
                <button
                  onClick={() => setRawDumpExpanded(!rawDumpExpanded)}
                  className="inline-flex items-center gap-1 rounded border border-cyan-500/40 px-2 py-1 text-xs text-cyan-200 hover:bg-cyan-500/12 transition-colors"
                >
                  {rawDumpExpanded ? 'Hide raw dump' : 'Show raw dump'}
                </button>
              </div>
            </div>
            {rawDumpExpanded && (
              <div className="rounded-md border border-blue-500/25 bg-black/25 p-2 text-white text-base whitespace-pre-wrap break-words leading-relaxed">
                {formatContent(message.content)}
              </div>
            )}
            {!rawDumpExpanded && (
              <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-2 text-sm text-blue-100/80 whitespace-pre-wrap break-words">
                {filestatsPreview}
              </div>
            )}
          </div>
        ) : (
          <div className="text-white text-lg whitespace-pre-wrap break-words leading-relaxed flex-1">
            {formatContent(message.content)}
            {isStreaming && <span className="terminal-cursor" />}
          </div>
        )}
      </div>

      {/* Action Preview */}
      {message.actionPreview && (
        <div className="ml-4 mt-2 rounded-md border border-amber-500/30 bg-amber-500/[0.06] p-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="font-mono text-xs font-bold uppercase tracking-[0.14em] text-amber-300">
              Action proposal
            </div>
            {actionRiskLabels(message.actionPreview).map((label) => (
              <span key={label} className="rounded border border-amber-500/30 bg-black/20 px-2 py-0.5 font-mono text-[11px] text-amber-100">
                {label}
              </span>
            ))}
          </div>
          <div className="mt-2 text-sm font-semibold text-amber-50">
            {message.actionPreview.name}
          </div>
          {message.actionPreview.description ? (
            <div className="mt-1 text-xs text-amber-100/80">
              Why: {message.actionPreview.description}
            </div>
          ) : null}
          <div className="mt-1 text-xs text-amber-100/75">
            What it will do: {message.actionPreview.impact || message.actionPreview.scope || 'Run the named backend action with the parameters shown below.'}
          </div>
          <div className="mt-1 font-mono text-[11px] text-amber-100/65">
            Parameters: {actionArgsSummary(message.actionPreview.args)}
          </div>
          <div className="mt-1 text-[11px] text-amber-100/60">
            No action runs until you confirm.
          </div>
          <div className="mt-3 flex gap-2">
            <button
              className="rounded border border-green-500/30 bg-green-500/20 px-2 py-0.5 text-xs text-green-300 transition-colors hover:bg-green-500/30"
              onClick={() => onConfirmAction?.(message.actionPreview)}
            >
              Confirm
            </button>
            <button
              className="rounded border border-red-500/30 bg-red-500/20 px-2 py-0.5 text-xs text-red-300 transition-colors hover:bg-red-500/30"
              onClick={() => onCancelAction?.(message.actionPreview)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {message.chart && (
        hasFilestatsChart ? (
          <div className="ml-4 mt-3 rounded border border-cyan-500/30 bg-cyan-500/6 p-3">
            <div className="text-xs uppercase tracking-[0.16em] text-cyan-300/90">Visual dashboard</div>
            <div className="mt-1 text-sm text-cyan-100/85">
              Filestats dashboard is opened in fullscreen mode for chart-like readability.
            </div>
            <button
              onClick={() => setChartDialogOpen(true)}
              className="mt-2 inline-flex items-center gap-1 rounded border border-cyan-400/50 bg-cyan-500/12 px-2 py-1 text-xs text-cyan-100 hover:bg-cyan-500/20 transition-colors"
            >
              <Maximize2 className="h-3 w-3" />
              Re-open fullscreen dashboard
            </button>
          </div>
        ) : (
          <div className="ml-4 mt-3 overflow-hidden rounded border border-cyan-500/30 bg-cyan-500/5">
            <div className="border-b border-cyan-500/20 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300/90">
              {message.chart.title}
            </div>
            <iframe
              title={message.chart.title}
              srcDoc={message.chart.html}
              sandbox="allow-scripts allow-same-origin"
              loading="lazy"
              className="h-[720px] w-full bg-black"
            />
          </div>
        )
      )}

      {message.chart && (
        <Dialog open={chartDialogOpen} onOpenChange={setChartDialogOpen}>
          <DialogContent className="h-[94vh] w-[97vw] max-w-[97vw] border-cyan-500/30 bg-zinc-950 p-0 text-zinc-100">
            <DialogHeader className="border-b border-cyan-500/20 px-4 py-3">
              <DialogTitle className="font-mono text-sm uppercase tracking-[0.14em] text-cyan-200">
                {message.chart.title}
              </DialogTitle>
              <DialogDescription className="text-xs text-cyan-100/70">
                Interactive dashboard view. Press Esc to close.
              </DialogDescription>
            </DialogHeader>
            <iframe
              title={`${message.chart.title}-fullscreen`}
              srcDoc={message.chart.html}
              sandbox="allow-scripts allow-same-origin"
              loading="lazy"
              className="h-[calc(94vh-74px)] w-full bg-black"
            />
          </DialogContent>
        </Dialog>
      )}

      {/* Sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="ml-4 mt-2">
          <button
            onClick={() => setSourcesExpanded(!sourcesExpanded)}
            className="flex items-center gap-1 text-sm text-blue-400/80 hover:text-blue-300 transition-colors"
          >
            {sourcesExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            [{message.sources.length} source{message.sources.length === 1 ? '' : 's'}]
          </button>
          {sourcesExpanded && (
            <div className="mt-2 space-y-2 rounded-md border border-blue-500/15 bg-blue-500/5 px-3 py-2 text-sm">
              {message.sources.map((source, i) => (
                <div
                  key={`${source.sourceId || source.documentId || source.url || source.title}-${i}`}
                  className="flex items-start gap-2"
                >
                  <span className="mt-0.5 text-blue-500">{`>`}</span>
                  <div className="min-w-0 flex-1">
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex max-w-full items-center gap-1 break-all text-blue-300 underline decoration-blue-500/40 underline-offset-2 hover:text-blue-200"
                      >
                        <span>{source.title}</span>
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <div className="break-words text-blue-200">{source.title}</div>
                    )}
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-blue-200/60">
                      {source.evidenceLabel && <span>{compactLabel(source.evidenceLabel)}</span>}
                      {source.kind && <span>{source.kind}</span>}
                      {source.docType && <span>{source.docType}</span>}
                      {formatSourceDate(source.publishedAt) && (
                        <span>{formatSourceDate(source.publishedAt)}</span>
                      )}
                      {source.documentId && (
                        <span className="font-mono">doc {source.documentId.slice(0, 12)}</span>
                      )}
                    </div>
                    {source.snippet && (
                      <p className="mt-1 whitespace-pre-wrap break-words text-blue-100/70">
                        {source.snippet}
                      </p>
                    )}
                    {!source.url && source.path && (
                      <p className="mt-1 break-all font-mono text-[11px] text-blue-100/45">
                        {source.path}
                      </p>
                    )}
                  </div>
                  <span className="shrink-0 text-blue-300/80">{formatSourceScore(source.score)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Metadata footer */}
      <div className="flex items-center gap-4 ml-4 mt-1 text-sm text-blue-400/60 opacity-70 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-opacity">
        <span>[{timestamp}]</span>
        {message.metadata && (
          <>
            {message.metadata.source && <span>source:{message.metadata.source}</span>}
            {message.metadata.model && <span>{message.metadata.model}</span>}
            {responseTimingLabel && <span>{responseTimingLabel}</span>}
            {message.metadata.costUsd !== undefined && <span>${message.metadata.costUsd.toFixed(4)}</span>}
          </>
        )}
        <button 
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-blue-400 transition-colors"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'copied' : 'copy'}
        </button>
      </div>
    </div>
  )
}
