'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import {
  ApiError,
  createExtractionReviewSession,
  getExtractionReviewErrors,
  getExtractionReviewRunStatus,
  getExtractionReviewRuns,
  getExtractionReviewSessions,
  getExtractionReviewSession,
  getTickerDocuments,
  getVerificationRuns,
  processDocument,
  runVerificationContext,
  submitExtractionReviewDecision,
} from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import { cn } from '@/lib/utils'
import type {
  ContextDocument,
  ExtractionReviewErrorQueue,
  ExtractionReviewRunStatusResponse,
  ExtractionReviewRunSummary,
  ExtractionReviewSession,
  ExtractionReviewSessionSummary,
  VerificationRunHistory,
  VerificationResult,
} from '@/lib/cockpit-types'

import { ACTIVE_RUNS_STORAGE_KEY } from './constants'
import { GoldEvalTabPanel } from './tabs/gold-eval-tab-panel'
import { MetricCoverageTabPanel } from './tabs/metric-coverage-tab-panel'
import { ReviewTabPanel } from './tabs/review-tab-panel'
import { RunsTabPanel } from './tabs/runs-tab-panel'
import { VerifyTabPanel } from './tabs/verify-tab-panel'
import { VerificationProgressLog } from './verification-progress-log'
import { VerificationSidebar } from './verification-sidebar'
import type {
  ActiveExtractionMonitorRun,
  ConfirmedMetricCoverageArtifacts,
  ConfirmedMetricCoveragePacket,
  ConfirmedMetricCoverageRow,
  ConfirmedMetricCoverageSummary,
  ProcessDocumentResponse,
  RealGoldEvalResponse,
  RealGoldEvalTaskProgressEvent,
  RealGoldEvalTaskResponse,
  VerificationProgressEntry,
  VerificationProgressLevel,
  VerificationTab,
} from './types'
import { useSnippetImage } from './use-snippet-image'
import { VerificationHeader } from './verification-header'
import { VerificationStatusStrip } from './verification-status-strip'
import { VerificationTabBar } from './verification-tab-bar'
import {
  downloadFile,
  escapeHtml,
  evidenceQualityRank,
  evidenceQualityForItem,
  formatMethodLabel,
  isKeyboardShortcutBlocked,
  isReviewableExtractionStatus,
  mapResponseToResults,
  normalizeEvidenceText,
  parseActiveExtractionMonitorRuns,
  parseDocumentIds,
  parseVerificationTab,
  reviewSessionRunIds,
  summarizeSessionDocuments,
} from './utils'

const BROWSER_API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''
const GOLD_EVAL_POLL_INTERVAL_MS = 1500
const GOLD_EVAL_TIMEOUT_MS = 60 * 60 * 1000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function fetchErrorDetail(response: Response, fallback: string): Promise<string> {
  const text = await response.text().catch(() => '')
  if (!text) return fallback
  try {
    const body = JSON.parse(text) as { detail?: unknown }
    return body && typeof body === 'object' && 'detail' in body
      ? String(body.detail)
      : text
  } catch {
    return text
  }
}

function realGoldProgressLevel(event: RealGoldEvalTaskProgressEvent): VerificationProgressLevel {
  const status = String(event.status || '').toLowerCase()
  if (status === 'failed' || status === 'error') return 'error'
  if (status === 'succeeded' || status === 'completed') return 'success'
  if (status === 'warning') return 'warning'
  return 'info'
}

function realGoldProgressKey(event: RealGoldEvalTaskProgressEvent, index: number): string {
  return [
    event.timestamp ?? index,
    event.stage || '',
    event.status || '',
    event.document_id || '',
    event.message || '',
  ].join('|')
}

function formatAccuracy(value: number | null | undefined): string | null {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : null
}

function realGoldProgressDetail(event: RealGoldEvalTaskProgressEvent): string | undefined {
  const parts: string[] = []
  if (event.stage) parts.push(`stage=${event.stage}`)
  if (event.document_id) parts.push(`document_id=${event.document_id}`)
  if (typeof event.completed === 'number' && typeof event.total === 'number') {
    parts.push(`progress=${event.completed}/${event.total}`)
  }
  if (event.trust_outcome) parts.push(`trust=${event.trust_outcome}`)
  if (typeof event.failed_metric_count === 'number') {
    parts.push(`failed_metrics=${event.failed_metric_count}`)
  }
  const metricAccuracy = formatAccuracy(event.total_accuracy)
  if (metricAccuracy) parts.push(`metric_accuracy=${metricAccuracy}`)
  const contextAccuracy = formatAccuracy(event.context_accuracy)
  if (contextAccuracy) parts.push(`context_accuracy=${contextAccuracy}`)
  return parts.length > 0 ? parts.join(' ') : undefined
}

function realGoldProgressMessage(event: RealGoldEvalTaskProgressEvent): string {
  if (event.message) return event.message
  if (event.stage && event.status) return `Real-Gold ${event.stage} ${event.status}`
  return 'Real-Gold progress update'
}

function mergeMetricCoverageResponses(
  summaryResponse: Partial<ConfirmedMetricCoveragePacket> & {
    summary?: ConfirmedMetricCoverageSummary | null
    artifacts?: ConfirmedMetricCoverageArtifacts | null
  },
  rowsResponse: Partial<ConfirmedMetricCoveragePacket> & {
    rows?: ConfirmedMetricCoverageRow[]
    count?: number
    artifacts?: ConfirmedMetricCoverageArtifacts | null
  },
): ConfirmedMetricCoveragePacket {
  const warnings = [
    ...(Array.isArray(summaryResponse.warnings) ? summaryResponse.warnings : []),
    ...(Array.isArray(rowsResponse.warnings) ? rowsResponse.warnings : []),
  ]
  const errors = [
    ...(Array.isArray(summaryResponse.errors) ? summaryResponse.errors : []),
    ...(Array.isArray(rowsResponse.errors) ? rowsResponse.errors : []),
  ]
  return {
    status: String(rowsResponse.status || summaryResponse.status || 'not_generated'),
    profile: String(summaryResponse.profile || rowsResponse.profile || 'confirmed_metric_coverage'),
    generated_at: summaryResponse.generated_at || summaryResponse.summary?.generated_at || null,
    head: summaryResponse.head || summaryResponse.summary?.head || null,
    branch: summaryResponse.branch || summaryResponse.summary?.branch || null,
    git_available: summaryResponse.git_available ?? summaryResponse.summary?.git_available ?? rowsResponse.git_available ?? null,
    git_head: summaryResponse.git_head || summaryResponse.summary?.git_head || rowsResponse.git_head || null,
    git_head_short: summaryResponse.git_head_short || summaryResponse.summary?.git_head_short || rowsResponse.git_head_short || null,
    git_branch: summaryResponse.git_branch || summaryResponse.summary?.git_branch || rowsResponse.git_branch || null,
    git_dirty: summaryResponse.git_dirty ?? summaryResponse.summary?.git_dirty ?? rowsResponse.git_dirty ?? null,
    git_status_short_summary: summaryResponse.git_status_short_summary || summaryResponse.summary?.git_status_short_summary || rowsResponse.git_status_short_summary || null,
    git_unavailable_reason: summaryResponse.git_unavailable_reason || summaryResponse.summary?.git_unavailable_reason || rowsResponse.git_unavailable_reason || null,
    fixtures_dir: summaryResponse.fixtures_dir || null,
    fixture_dir: summaryResponse.fixture_dir || summaryResponse.summary?.fixture_dir || rowsResponse.fixture_dir || null,
    artifact_path: summaryResponse.artifact_path || summaryResponse.summary?.artifact_path || rowsResponse.artifact_path || null,
    app_runtime_context: summaryResponse.app_runtime_context || summaryResponse.summary?.app_runtime_context || rowsResponse.app_runtime_context || null,
    summary: summaryResponse.summary || null,
    rows: Array.isArray(rowsResponse.rows) ? rowsResponse.rows : [],
    count: typeof rowsResponse.count === 'number' ? rowsResponse.count : (rowsResponse.rows?.length ?? 0),
    artifacts: summaryResponse.artifacts || rowsResponse.artifacts || null,
    errors,
    warnings: Array.from(new Set(warnings)),
  }
}

function renderMetricCoverageMarkdown(packet: ConfirmedMetricCoveragePacket): string {
  const summary = packet.summary
  const lines = [
    '# Confirmed Metric Coverage Review',
    '',
    '- This review does not run extraction.',
    '- Candidate metrics require human source-evidence review before production scoring.',
    '- Canonical trust semantics are unchanged.',
    '',
    '## Summary',
    '',
    `- status: \`${packet.status}\``,
    `- profile: \`${packet.profile}\``,
    `- fixtures: \`${summary?.fixture_count ?? 'DATA_MISSING'}\``,
    `- expectations: \`${summary?.total_expectations ?? 'DATA_MISSING'}\``,
    `- scored: \`${summary?.scored_count ?? 'DATA_MISSING'}\``,
    `- candidates: \`${summary?.candidate_review_required_count ?? 'DATA_MISSING'}\``,
    `- ambiguous: \`${summary?.ambiguous_count ?? 'DATA_MISSING'}\``,
    `- unsupported: \`${summary?.unsupported_count ?? 'DATA_MISSING'}\``,
    `- generated_at: \`${summary?.generated_at ?? packet.generated_at ?? 'DATA_MISSING'}\``,
    `- git_available: \`${summary?.git_available ?? packet.git_available ?? 'DATA_MISSING'}\``,
    `- git_head: \`${summary?.git_head ?? packet.git_head ?? 'DATA_MISSING'}\``,
    `- git_head_short: \`${summary?.git_head_short ?? packet.git_head_short ?? summary?.head ?? packet.head ?? 'DATA_MISSING'}\``,
    `- git_branch: \`${summary?.git_branch ?? packet.git_branch ?? summary?.branch ?? packet.branch ?? 'DATA_MISSING'}\``,
    `- git_dirty: \`${summary?.git_dirty ?? packet.git_dirty ?? 'DATA_MISSING'}\``,
    `- git_unavailable_reason: \`${summary?.git_unavailable_reason ?? packet.git_unavailable_reason ?? 'DATA_MISSING'}\``,
    `- artifact_path: \`${summary?.artifact_path ?? packet.artifact_path ?? packet.artifacts?.json_path ?? 'DATA_MISSING'}\``,
    '',
    '## Rows',
    '',
    '| ticker | fixture | period | metric | classification | source | action |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ]
  packet.rows.forEach((row) => {
    lines.push([
      row.ticker || '-',
      row.fixture || row.document_id,
      row.period.period_end || '-',
      row.metric_name,
      row.classification,
      row.source_pdf_status,
      row.recommended_action,
    ].map((value) => String(value).replaceAll('|', '\\|')).join(' | ').replace(/^/, '| ').replace(/$/, ' |'))
  })
  lines.push('')
  return lines.join('\n')
}

export function VerificationScreen() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { activeTicker, preferences } = useCockpitStore()
  const isIPhoneScale = preferences.iphoneScale

  const [hasHydrated, setHasHydrated] = useState(false)
  const [activeTab, setActiveTab] = useState<VerificationTab>(parseVerificationTab(searchParams.get('tab')))
  const [ticker, setTicker] = useState(activeTicker || '')

  const updateTab = useCallback((value: string) => {
    const nextTab = parseVerificationTab(value)
    setActiveTab(nextTab)
    const params = new URLSearchParams(searchParams.toString())
    if (nextTab === 'review') {
      params.delete('tab')
    } else {
      params.set('tab', nextTab)
    }
    const nextUrl = params.toString() ? `${pathname}?${params.toString()}` : pathname
    router.replace(nextUrl, { scroll: false })
  }, [pathname, router, searchParams])

  const [isRunning, setIsRunning] = useState(false)

  const [results, setResults] = useState<VerificationResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [documents, setDocuments] = useState<ContextDocument[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [extraDocumentIds, setExtraDocumentIds] = useState('')
  const [docsLimit, setDocsLimit] = useState('10')
  const [extractionMethod, setExtractionMethod] = useState<'auto' | 'docling' | 'pymupdf' | 'anthropic'>('auto')
  const [strictMethod, setStrictMethod] = useState(true)

  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewActionLoading, setReviewActionLoading] = useState(false)
  const [reviewSession, setReviewSession] = useState<ExtractionReviewSession | null>(null)
  const [selectedReviewItemId, setSelectedReviewItemId] = useState<string | null>(null)
  const [reviewSessionLoadingMessage, setReviewSessionLoadingMessage] = useState<string | null>(null)
  const [activeMonitorNotice, setActiveMonitorNotice] = useState<string | null>(null)
  const [wrongQueue, setWrongQueue] = useState<ExtractionReviewErrorQueue | null>(null)
  const [recentRuns, setRecentRuns] = useState<ExtractionReviewRunSummary[]>([])
  const [recentRunsLoading, setRecentRunsLoading] = useState(false)
  const [recentRunsError, setRecentRunsError] = useState<string | null>(null)
  const [recentReviewSessions, setRecentReviewSessions] = useState<ExtractionReviewSessionSummary[]>([])
  const [recentReviewSessionsLoading, setRecentReviewSessionsLoading] = useState(false)
  const [recentReviewSessionsError, setRecentReviewSessionsError] = useState<string | null>(null)
  const [selectedRunId, setSelectedRunId] = useState('')
  const [selectedReviewSessionId, setSelectedReviewSessionId] = useState('')
  const [activeRunIdsByDocumentId, setActiveRunIdsByDocumentId] = useState<Record<string, string>>({})
  const [attachedRunMetadataByDocumentId, setAttachedRunMetadataByDocumentId] = useState<Record<string, ActiveExtractionMonitorRun>>({})
  const [runStatus, setRunStatus] = useState<ExtractionReviewRunStatusResponse | null>(null)
  const [runStatuses, setRunStatuses] = useState<Record<string, ExtractionReviewRunStatusResponse>>({})
  const [unavailableRunStatusIds, setUnavailableRunStatusIds] = useState<Set<string>>(new Set())
  const [runStatusLoading, setRunStatusLoading] = useState(false)

  const [goldLimit, setGoldLimit] = useState('10')
  const [goldEvalLoading, setGoldEvalLoading] = useState(false)
  const [goldEvalError, setGoldEvalError] = useState<string | null>(null)
  const [goldEval, setGoldEval] = useState<RealGoldEvalResponse | null>(null)

  const [metricCoverageLoading, setMetricCoverageLoading] = useState(false)
  const [metricCoverageRunning, setMetricCoverageRunning] = useState(false)
  const [metricCoverageError, setMetricCoverageError] = useState<string | null>(null)
  const [metricCoverage, setMetricCoverage] = useState<ConfirmedMetricCoveragePacket | null>(null)

  const [verificationRunHistory, setVerificationRunHistory] = useState<VerificationRunHistory[]>([])
  const [verificationHistoryLoading, setVerificationHistoryLoading] = useState(false)
  const [progressLog, setProgressLog] = useState<VerificationProgressEntry[]>([])

  const documentLoadLockRef = useRef(false)
  const recentRunsLoadLockRef = useRef(false)
  const recentReviewSessionsLoadLockRef = useRef(false)
  const reviewActionLockRef = useRef(false)
  const unavailableRunStatusIdsRef = useRef<Set<string>>(new Set())
  const pendingRunStatusIdsRef = useRef<Set<string>>(new Set())
  const progressSequenceRef = useRef(0)

  const appendProgress = useCallback((entry: {
    level?: VerificationProgressLevel
    scope: string
    message: string
    detail?: string
  }) => {
    progressSequenceRef.current += 1
    const nextEntry: VerificationProgressEntry = {
      id: `verification-progress-${Date.now()}-${progressSequenceRef.current}`,
      timestamp: new Date().toISOString(),
      level: entry.level ?? 'info',
      scope: entry.scope,
      message: entry.message,
      detail: entry.detail,
    }
    setProgressLog((current) => [nextEntry, ...current].slice(0, 100))
  }, [])

  const clearProgressLog = useCallback(() => {
    setProgressLog([])
  }, [])

  const describeError = useCallback((err: unknown, fallback: string): string => (
    err instanceof Error ? err.message : fallback
  ), [])

  const markRunStatusUnavailable = useCallback((runId: string) => {
    if (!runId) return
    unavailableRunStatusIdsRef.current.add(runId)
    setUnavailableRunStatusIds((current) => {
      if (current.has(runId)) return current
      const next = new Set(current)
      next.add(runId)
      return next
    })
  }, [])

  const loadRunStatus = useCallback(async (runId: string): Promise<ExtractionReviewRunStatusResponse | null> => {
    if (!runId || unavailableRunStatusIdsRef.current.has(runId)) return null
    if (pendingRunStatusIdsRef.current.has(runId)) return null
    pendingRunStatusIdsRef.current.add(runId)
    try {
      return await getExtractionReviewRunStatus(runId, 200)
    } catch (err: unknown) {
      const status = err instanceof ApiError
        ? err.status
        : (typeof err === 'object' && err !== null && 'status' in err ? Number((err as { status?: unknown }).status) : null)
      if (status === 404) {
        markRunStatusUnavailable(runId)
        return null
      }
      throw err
    } finally {
      pendingRunStatusIdsRef.current.delete(runId)
    }
  }, [markRunStatusUnavailable])

  const handleLoadDocuments = useCallback(async (tickerOverride?: string) => {
    if (documentLoadLockRef.current) return
    const cleanTicker = (typeof tickerOverride === 'string' ? tickerOverride : ticker).trim().toUpperCase()
    if (!cleanTicker) {
      setReviewError('Ticker is required to load review documents.')
      return
    }

    documentLoadLockRef.current = true
    setReviewError(null)
    setDocumentsLoading(true)
    try {
      const parsedLimit = Number.parseInt(docsLimit, 10)
      const resolvedLimit = Number.isFinite(parsedLimit) ? parsedLimit : 10
      appendProgress({
        scope: 'docs',
        message: `Loading review documents for ${cleanTicker}`,
        detail: `docs_limit=${resolvedLimit}`,
      })
      const docs = await getTickerDocuments(cleanTicker, resolvedLimit)
      const runsPayload = await getExtractionReviewRuns(cleanTicker, 20)
      const sessionsPayload = await getExtractionReviewSessions(cleanTicker, 20)
      setTicker(cleanTicker)
      setDocuments(docs)
      setRecentRuns(runsPayload.items)
      setRecentReviewSessions(sessionsPayload.items)
      const defaultDoc = docs[0]?.document_id ?? ''
      setSelectedDocumentId((current) => docs.some((doc) => doc.document_id === current) ? current : defaultDoc)
      setSelectedRunId((current) => runsPayload.items.some((run) => run.run_id === current) ? current : (runsPayload.items[0]?.run_id || ''))
      setSelectedReviewSessionId((current) => sessionsPayload.items.some((session) => session.session_id === current) ? current : (sessionsPayload.items[0]?.session_id || ''))
      appendProgress({
        level: 'success',
        scope: 'docs',
        message: `Loaded ${docs.length} document(s), ${runsPayload.items.length} run(s), and ${sessionsPayload.items.length} saved review(s) for ${cleanTicker}`,
      })
      toast.success(`Loaded ${docs.length} document(s) for ${cleanTicker}`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to load documents')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'docs', message: 'Document load failed', detail: message })
      toast.error(message)
    } finally {
      documentLoadLockRef.current = false
      setDocumentsLoading(false)
    }
  }, [appendProgress, describeError, docsLimit, ticker])

  const handleLoadRecentRuns = useCallback(async (filterTicker?: string) => {
    if (recentRunsLoadLockRef.current) return
    
    // If no ticker provided, we use the current component state ticker if it exists
    const targetTicker = filterTicker !== undefined ? filterTicker : ticker.trim().toUpperCase()
    
    recentRunsLoadLockRef.current = true
    setRecentRunsLoading(true)
    setRecentRunsError(null)
    try {
      // Fetch recent runs (optional ticker filter)
      appendProgress({
        scope: 'runs',
        message: targetTicker ? `Loading recent runs for ${targetTicker}` : 'Loading recent runs across all tickers',
        detail: 'limit=50',
      })
      const payload = await getExtractionReviewRuns(targetTicker, 50)
      setRecentRuns(payload.items)
      appendProgress({
        level: 'success',
        scope: 'runs',
        message: `Loaded ${payload.items.length} recent extraction run(s)`,
        detail: targetTicker ? `ticker=${targetTicker}` : 'ticker=BROAD',
      })
      
      // If we are filtering by a specific ticker, also update the selected run
      if (targetTicker) {
        setSelectedRunId((current) => 
          payload.items.some((run) => run.run_id === current) ? current : (payload.items[0]?.run_id || '')
        )
      }
    } catch (err: unknown) {
      console.error('Failed to load recent runs:', err)
      const message = describeError(err, 'Failed to load recent runs')
      setRecentRunsError(message)
      appendProgress({ level: 'error', scope: 'runs', message: 'Recent run load failed', detail: message })
      if (targetTicker) {
        setReviewError(message)
        toast.error(message)
      }
    } finally {
      recentRunsLoadLockRef.current = false
      setRecentRunsLoading(false)
    }
  }, [appendProgress, describeError, ticker])

  const handleLoadReviewSessions = useCallback(async (filterTicker?: string) => {
    if (recentReviewSessionsLoadLockRef.current) return

    const targetTicker = filterTicker !== undefined ? filterTicker : ticker.trim().toUpperCase()

    recentReviewSessionsLoadLockRef.current = true
    setRecentReviewSessionsLoading(true)
    setRecentReviewSessionsError(null)
    try {
      appendProgress({
        scope: 'sessions',
        message: targetTicker ? `Loading review history for ${targetTicker}` : 'Loading review history across all tickers',
        detail: 'limit=50',
      })
      const payload = await getExtractionReviewSessions(targetTicker, 50)
      setRecentReviewSessions(payload.items)
      appendProgress({
        level: 'success',
        scope: 'sessions',
        message: `Loaded ${payload.items.length} review history record(s)`,
        detail: targetTicker ? `ticker=${targetTicker}` : 'ticker=BROAD',
      })
      setSelectedReviewSessionId((current) => (
        payload.items.some((session) => session.session_id === current)
          ? current
          : (payload.items[0]?.session_id || '')
      ))
    } catch (err: unknown) {
      console.error('Failed to load review sessions:', err)
      const message = describeError(err, 'Failed to load review sessions')
      setRecentReviewSessionsError(message)
      appendProgress({ level: 'error', scope: 'sessions', message: 'Saved review session load failed', detail: message })
      if (targetTicker) {
        setReviewError(message)
        toast.error(message)
      }
    } finally {
      recentReviewSessionsLoadLockRef.current = false
      setRecentReviewSessionsLoading(false)
    }
  }, [appendProgress, describeError, ticker])

  const handleSelectHistoryTicker = useCallback((historyTicker: string) => {
    const cleanTicker = historyTicker.trim().toUpperCase()
    setTicker(cleanTicker)
    void handleLoadDocuments(cleanTicker)
    void handleLoadReviewSessions(cleanTicker)
  }, [handleLoadDocuments, handleLoadReviewSessions])

  useEffect(() => {
    setHasHydrated(true)
  }, [])

  useEffect(() => {
    if (activeTicker) {
      setTicker(activeTicker)
    }
  }, [activeTicker])

  useEffect(() => {
    const nextTab = parseVerificationTab(searchParams.get('tab'))
    setActiveTab((current) => (current === nextTab ? current : nextTab))
  }, [searchParams])

  const reviewItems = useMemo(() => {
    const items = reviewSession?.items ?? []
    return [...items].sort((left, right) => {
      const qualityDiff = evidenceQualityRank(evidenceQualityForItem(left)) - evidenceQualityRank(evidenceQualityForItem(right))
      if (qualityDiff !== 0) return qualityDiff
      return left.metric_name.localeCompare(right.metric_name)
    })
  }, [reviewSession])

  const currentReviewItem = useMemo(() => {
    if (reviewItems.length === 0) return null
    if (!selectedReviewItemId) return reviewItems[0]
    return reviewItems.find((item) => item.item_id === selectedReviewItemId) ?? reviewItems[0]
  }, [reviewItems, selectedReviewItemId])

  const currentReviewIndex = currentReviewItem
    ? reviewItems.findIndex((item) => item.item_id === currentReviewItem.item_id)
    : -1

  const currentEvidenceQuality = evidenceQualityForItem(currentReviewItem)
  const loadedSessionRunIds = useMemo(() => reviewSessionRunIds(reviewSession), [reviewSession])
  const hasRunSelectionMismatch = Boolean(
    reviewSession
    && selectedRunId
    && loadedSessionRunIds.length > 0
    && !loadedSessionRunIds.includes(selectedRunId),
  )
  const evidenceSuspendMessage = reviewSessionLoadingMessage
    || (hasRunSelectionMismatch ? 'Selected run changed. Inspect the selected run to load matching evidence.' : null)
  const activeRunId = currentReviewItem?.run_id || loadedSessionRunIds[0] || selectedRunId || ''
  const matchedEvidenceText = normalizeEvidenceText(currentReviewItem?.matched_text)
    || normalizeEvidenceText(currentReviewItem?.snippet.matched_text)
    || normalizeEvidenceText(currentReviewItem?.evidence_text)
  const currentSnippetUrl = currentReviewItem?.image_url || currentReviewItem?.snippet.image_url || null
  const currentSnippetPath = currentReviewItem?.image_path || currentReviewItem?.snippet.image_path || null
  const currentEvidenceKey = reviewSession && currentReviewItem
    ? `${reviewSession.session_id}:${currentReviewItem.item_id}:${currentReviewItem.run_id || 'runless'}`
    : null
  const currentRowRef = currentReviewItem?.row_refs?.[currentReviewItem.metric_name] || null
  const hasPrevReviewItem = currentReviewIndex > 0
  const hasNextReviewItem = currentReviewIndex >= 0 && currentReviewIndex < reviewItems.length - 1

  const selectedReviewDocumentIds = useMemo(() => {
    const ids = parseDocumentIds(extraDocumentIds)
    if (selectedDocumentId && !ids.includes(selectedDocumentId)) {
      ids.unshift(selectedDocumentId)
    }
    return ids
  }, [extraDocumentIds, selectedDocumentId])

  const selectedRunStatuses = useMemo(
    () => selectedReviewDocumentIds
      .map((documentId) => ({
        documentId,
        runId: activeRunIdsByDocumentId[documentId],
        status: runStatuses[documentId],
      }))
      .filter((entry) => entry.runId),
    [activeRunIdsByDocumentId, runStatuses, selectedReviewDocumentIds],
  )

  const attachActiveRuns = searchParams.get('attach') === 'active'

  useEffect(() => {
    if (reviewItems.length === 0) {
      setSelectedReviewItemId(null)
      return
    }
    if (!selectedReviewItemId || !reviewItems.some((item) => item.item_id === selectedReviewItemId)) {
      setSelectedReviewItemId(reviewItems[0].item_id)
    }
  }, [reviewItems, selectedReviewItemId])

  const handleReviewSessionRefresh = useCallback((session: ExtractionReviewSession, itemId: string | null) => {
    setReviewSession(session)
    setSelectedReviewItemId((current) => (
      itemId && session.items.some((item) => item.item_id === itemId) ? itemId : current
    ))
  }, [])

  const {
    snippetImageState,
    snippetImageUrl,
    beginSessionSwap,
    handleSnippetImageLoad,
    handleSnippetImageError,
  } = useSnippetImage({
    currentEvidenceKey,
    currentSnippetUrl,
    evidenceSuspendMessage,
    currentReviewItem,
    currentEvidenceQuality,
    reviewSessionId: reviewSession?.session_id || null,
    getReviewSession: getExtractionReviewSession,
    onSessionRefresh: handleReviewSessionRefresh,
  })

  const currentSnippetRenderKey = `${currentEvidenceKey || 'no-evidence'}:${snippetImageState.retryAttempted ? 'retry' : 'initial'}`

  const persistActiveRuns = useCallback((value: Record<string, string>) => {
    setActiveRunIdsByDocumentId(value)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ACTIVE_RUNS_STORAGE_KEY, JSON.stringify(value))
    }
  }, [])

  const refreshRunStatuses = useCallback(async (runIdsByDocumentId: Record<string, string>) => {
    const responses = await Promise.all(
      Object.entries(runIdsByDocumentId).map(async ([documentId, runId]) => {
        try {
          const status = await loadRunStatus(runId)
          return status ? ([documentId, status] as const) : null
        } catch {
          return null
        }
      }),
    )

    const foundResponses = responses.filter((entry): entry is NonNullable<typeof entry> => entry !== null)
    if (foundResponses.length === 0) return

    setRunStatuses((current) => {
      const next = { ...current }
      for (const entry of foundResponses) {
        next[entry[0]] = entry[1]
      }
      return next
    })
  }, [loadRunStatus])

  useEffect(() => {
    if (!hasHydrated || typeof window === 'undefined') return
    try {
      const raw = window.localStorage.getItem(ACTIVE_RUNS_STORAGE_KEY)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object') {
        setActiveRunIdsByDocumentId(parsed as Record<string, string>)
      }
    } catch {
      window.localStorage.removeItem(ACTIVE_RUNS_STORAGE_KEY)
    }
  }, [hasHydrated])

  useEffect(() => {
    if (!hasHydrated || !attachActiveRuns) return
    let cancelled = false

    const attachMonitor = async () => {
      try {
        appendProgress({ scope: 'monitor', message: 'Loading active extraction run metadata from backend config' })
        const response = await fetch('/api/cockpit/config', { cache: 'no-store' })
        if (!response.ok) {
          throw new Error(`Failed to load active extraction runs (HTTP ${response.status})`)
        }

        const payload = await response.json() as Record<string, unknown>
        const activeRuns = parseActiveExtractionMonitorRuns(payload)
        if (cancelled) return

        if (activeRuns.length === 0) {
          setAttachedRunMetadataByDocumentId({})
          setActiveMonitorNotice('No active extraction runs were reported by the backend.')
          appendProgress({
            level: 'warning',
            scope: 'monitor',
            message: 'No active extraction runs were reported by the backend',
          })
          return
        }

        const runIdsByDocumentId = Object.fromEntries(activeRuns.map((run) => [run.documentId, run.runId]))
        const metadataByDocumentId = Object.fromEntries(activeRuns.map((run) => [run.documentId, run]))

        setAttachedRunMetadataByDocumentId(metadataByDocumentId)
        persistActiveRuns(runIdsByDocumentId)
        setSelectedDocumentId(activeRuns[0]?.documentId ?? '')
        setExtraDocumentIds(activeRuns.slice(1).map((run) => run.documentId).join('\n'))
        setSelectedRunId(activeRuns[0]?.runId ?? '')
        setTicker((current) => current.trim() ? current : (activeRuns[0]?.ticker || current))
        setActiveMonitorNotice(
          `Attached to ${activeRuns.length} active extraction run${activeRuns.length === 1 ? '' : 's'} from backend state.`,
        )
        appendProgress({
          level: 'success',
          scope: 'monitor',
          message: `Attached to ${activeRuns.length} active extraction run${activeRuns.length === 1 ? '' : 's'}`,
          detail: activeRuns.map((run) => `${run.documentId}:${run.runId}`).join(', '),
        })
        await refreshRunStatuses(runIdsByDocumentId)
      } catch (err: unknown) {
        if (cancelled) return
        const message = describeError(err, 'Failed to attach to the active extraction run')
        setAttachedRunMetadataByDocumentId({})
        setActiveMonitorNotice(message)
        appendProgress({ level: 'error', scope: 'monitor', message: 'Active extraction monitor attach failed', detail: message })
      }
    }

    void attachMonitor()
    return () => {
      cancelled = true
    }
  }, [appendProgress, attachActiveRuns, describeError, hasHydrated, persistActiveRuns, refreshRunStatuses])

  useEffect(() => {
    const activeEntries = Object.entries(activeRunIdsByDocumentId).filter(([documentId, runId]) => {
      const status = runStatuses[documentId]?.summary?.status
      return Boolean(runId)
        && !unavailableRunStatusIds.has(runId)
        && !['succeeded', 'failed', 'blocked'].includes(String(status || ''))
    })
    if (activeEntries.length === 0) return

    let cancelled = false
    const poll = async () => {
      const responses = await Promise.all(
        activeEntries.map(async ([documentId, runId]) => {
          try {
            const status = await loadRunStatus(runId)
            return status ? ([documentId, status] as const) : null
          } catch {
            return null
          }
        }),
      )
      if (cancelled) return
      const foundResponses = responses.filter((entry): entry is NonNullable<typeof entry> => entry !== null)
      if (foundResponses.length === 0) return
      setRunStatuses((current) => {
        const next = { ...current }
        for (const entry of foundResponses) {
          next[entry[0]] = entry[1]
        }
        return next
      })
    }

    void poll()
    const interval = window.setInterval(() => {
      void poll()
    }, 2500)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [activeRunIdsByDocumentId, loadRunStatus, runStatuses, unavailableRunStatusIds])

  const moveReviewSelection = useCallback((direction: 'prev' | 'next') => {
    if (currentReviewIndex < 0) return
    const delta = direction === 'next' ? 1 : -1
    const nextItem = reviewItems[currentReviewIndex + delta]
    if (!nextItem) return
    setSelectedReviewItemId(nextItem.item_id)
  }, [currentReviewIndex, reviewItems])

  const beginReviewSessionSwap = useCallback((message: string) => {
    setReviewSessionLoadingMessage(message)
    setReviewSession(null)
    setSelectedReviewItemId(null)
    setRunStatus(null)
    beginSessionSwap(message)
  }, [beginSessionSwap])

  const handleRunVerification = useCallback(async (broad: boolean = false) => {
    setIsRunning(true)
    setResults(null)
    setError(null)

    const queryTicker = broad ? '' : ticker.trim()
    try {
      appendProgress({
        scope: 'verify',
        message: queryTicker ? `Running backend verification for ${queryTicker}` : 'Running broad backend verification',
        detail: 'failures_limit=100 low_confidence_threshold=0.4 low_confidence_limit=100',
      })
      const data = await runVerificationContext({ ticker: queryTicker || null })
      const mappedResults = mapResponseToResults(data)
      setResults(mappedResults)
      if (data.run) {
        setVerificationRunHistory((current) => [
          data.run!,
          ...current.filter((run) => run.run_id !== data.run!.run_id),
        ].slice(0, 10))
      }
      const failedCount = mappedResults.filter((result) => !result.passed).length
      appendProgress({
        level: failedCount > 0 ? 'warning' : 'success',
        scope: 'verify',
        message: `Verification finished with ${failedCount} failed check(s) out of ${mappedResults.length}`,
        detail: data.run ? `run_id=${data.run.run_id} passed=${data.run.passed}` : undefined,
      })
    } catch (err: unknown) {
      const message = describeError(err, 'Unexpected error during verification')
      setError(message)
      appendProgress({ level: 'error', scope: 'verify', message: 'Verification request failed', detail: message })
    } finally {
      setIsRunning(false)
    }
  }, [appendProgress, describeError, ticker])

  const failedChecksCount = useMemo(() => results?.filter((r) => !r.passed).length ?? 0, [results])

  const runSelectedDocumentExtractions = useCallback(async (documentIds = selectedReviewDocumentIds): Promise<{
    queuedIds: string[]
    failedRuns: string[]
    runIds: string[]
    runIdsByDocumentId: Record<string, string>
    results: ProcessDocumentResponse[]
  }> => {
    const queuedIds: string[] = []
    const failedRuns: string[] = []
    const runIds: string[] = []
    const runIdsByDocumentId: Record<string, string> = {}
    const results: ProcessDocumentResponse[] = []

    for (const documentId of documentIds) {
      appendProgress({
        scope: 'extract',
        message: `Starting extraction for ${documentId.slice(0, 12)}`,
        detail: `method=${extractionMethod} strict=${strictMethod}`,
      })
      const result = await processDocument({
        documentId,
        method: extractionMethod,
        strictMethod,
      }) as ProcessDocumentResponse

      results.push(result)
      const mode = String(result.mode ?? '')
      const extractionStatus = String(result.extraction_status ?? '')
      if (result.run_id) {
        runIdsByDocumentId[documentId] = result.run_id
      }
      if (mode === 'celery') {
        queuedIds.push(documentId)
        appendProgress({
          level: 'warning',
          scope: 'extract',
          message: `Extraction queued for ${documentId.slice(0, 12)}`,
          detail: result.run_id ? `run_id=${result.run_id}` : undefined,
        })
        continue
      }
      if (result.run_id) {
        runIds.push(result.run_id)
        appendProgress({
          level: 'success',
          scope: 'extract',
          message: `Extraction completed for ${documentId.slice(0, 12)}`,
          detail: `run_id=${result.run_id} status=${extractionStatus || 'unknown'} actual_method=${formatMethodLabel(result.method_provenance?.actual_method || extractionMethod)}`,
        })
        continue
      }
      if (!isReviewableExtractionStatus(extractionStatus)) {
        failedRuns.push(`${documentId.slice(0, 12)}:${extractionStatus || 'unknown'}`)
        appendProgress({
          level: 'error',
          scope: 'extract',
          message: `Extraction did not produce a reviewable result for ${documentId.slice(0, 12)}`,
          detail: `status=${extractionStatus || 'unknown'}`,
        })
        continue
      }
    }

    return { queuedIds, failedRuns, runIds, runIdsByDocumentId, results }
  }, [appendProgress, extractionMethod, selectedReviewDocumentIds, strictMethod])

  const handleRunExtraction = useCallback(async () => {
    if (reviewActionLockRef.current) return
    if (selectedReviewDocumentIds.length === 0) {
      setReviewError('Select one document or enter document IDs first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    try {
      appendProgress({
        scope: 'extract',
        message: `Running extraction for ${selectedReviewDocumentIds.length} selected document(s)`,
        detail: selectedReviewDocumentIds.map((id) => id.slice(0, 12)).join(', '),
      })
      const { queuedIds, failedRuns, results: extractionResults, runIdsByDocumentId } = await runSelectedDocumentExtractions()
      if (Object.keys(runIdsByDocumentId).length > 0) {
        const next = { ...activeRunIdsByDocumentId, ...runIdsByDocumentId }
        persistActiveRuns(next)
        await refreshRunStatuses(runIdsByDocumentId)
      }
      if (queuedIds.length > 0) {
        const message = `Extraction queued for ${queuedIds.length} document(s). Wait for completion before loading the review session.`
        setReviewError(message)
        appendProgress({ level: 'warning', scope: 'extract', message, detail: queuedIds.join(', ') })
        toast.info(message)
        return
      }
      if (failedRuns.length > 0) {
        const message = `Latest extraction did not produce a reviewable result for: ${failedRuns.join(', ')}`
        setReviewError(message)
        appendProgress({ level: 'error', scope: 'extract', message })
        toast.error(message)
        return
      }
      const methodSummary = extractionResults[0]?.method_provenance
      appendProgress({
        level: 'success',
        scope: 'extract',
        message: `Extraction request finished for ${selectedReviewDocumentIds.length} document(s)`,
        detail: `actual_method=${formatMethodLabel(methodSummary?.actual_method || extractionMethod)} strict=${strictMethod}`,
      })
      toast.success(
        `Extraction requested for ${selectedReviewDocumentIds.length} document(s) using ${formatMethodLabel(methodSummary?.actual_method || extractionMethod)}${strictMethod ? ' (strict)' : ''}`,
      )
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to run extraction')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'extract', message: 'Extraction request failed', detail: message })
      toast.error(message)
    } finally {
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [
    activeRunIdsByDocumentId,
    appendProgress,
    describeError,
    extractionMethod,
    persistActiveRuns,
    refreshRunStatuses,
    runSelectedDocumentExtractions,
    selectedReviewDocumentIds,
    strictMethod,
  ])

  const loadWrongQueue = useCallback(async () => {
    try {
      appendProgress({ scope: 'queue', message: 'Loading review error queue', detail: 'limit=200' })
      const payload = await getExtractionReviewErrors(200)
      setWrongQueue(payload)
      appendProgress({
        level: payload.count > 0 ? 'warning' : 'success',
        scope: 'queue',
        message: `Wrong queue loaded with ${payload.count} item(s)`,
      })
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to load wrong queue')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'queue', message: 'Wrong queue load failed', detail: message })
    }
  }, [appendProgress, describeError])

  useEffect(() => {
    // Initial global load for discovery - we pass empty string to ensure global fetch
    void handleLoadRecentRuns('')
    void handleLoadReviewSessions('')
    void loadWrongQueue()
  }, [handleLoadRecentRuns, handleLoadReviewSessions, loadWrongQueue])

  useEffect(() => {
    setVerificationHistoryLoading(true)
    appendProgress({ scope: 'verify', message: 'Loading recent verification run history', detail: 'limit=10' })
    getVerificationRuns(10)
      .then((payload) => {
        if (payload.ok && Array.isArray(payload.runs)) {
          setVerificationRunHistory(payload.runs as VerificationRunHistory[])
          appendProgress({
            level: 'success',
            scope: 'verify',
            message: `Loaded ${payload.runs.length} recent verification run(s)`,
          })
        }
      })
      .catch((err: unknown) => {
        appendProgress({
          level: 'warning',
          scope: 'verify',
          message: 'Verification history load failed',
          detail: describeError(err, 'history is best-effort'),
        })
      })
      .finally(() => setVerificationHistoryLoading(false))
  }, [appendProgress, describeError])

  const handleInspectSelectedRun = useCallback(async (runIdOverride?: string) => {
    if (reviewActionLockRef.current) return
    const runId = (typeof runIdOverride === 'string' ? runIdOverride : selectedRunId).trim()
    if (!runId) {
      setReviewError('Select a recent run first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap(`Loading review session for run ${runId.slice(0, 12)}...`)
    try {
      appendProgress({ scope: 'review', message: `Creating review session for historical run ${runId.slice(0, 12)}`, detail: `run_id=${runId}` })
      const session = await createExtractionReviewSession({ runIds: [runId] })
      setReviewSession(session)
      setSelectedReviewSessionId(session.session_id)
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      await loadWrongQueue()
      void handleLoadReviewSessions(ticker.trim().toUpperCase())
      appendProgress({
        level: 'success',
        scope: 'review',
        message: `Loaded review session with ${session.items.length} item(s)`,
        detail: `session_id=${session.session_id}`,
      })
      toast.success(`Loaded historical run ${runId.slice(0, 12)}`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to inspect selected run')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'review', message: 'Historical run inspection failed', detail: message })
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [appendProgress, beginReviewSessionSwap, describeError, handleLoadReviewSessions, loadWrongQueue, selectedRunId, ticker])

  const handleSelectHistoryRun = useCallback((runId: string) => {
    setSelectedRunId(runId)
    updateTab('runs')
    void handleInspectSelectedRun(runId)
  }, [handleInspectSelectedRun, updateTab])

  const handleInspectSelectedReviewSession = useCallback(async (sessionIdOverride?: string) => {
    if (reviewActionLockRef.current) return
    const sessionId = (typeof sessionIdOverride === 'string' ? sessionIdOverride : selectedReviewSessionId).trim()
    if (!sessionId) {
      setReviewError('Select a saved review session first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap(`Loading saved review session ${sessionId}...`)
    try {
      appendProgress({ scope: 'review', message: `Loading saved review session ${sessionId}` })
      const session = await getExtractionReviewSession(sessionId)
      setReviewSession(session)
      setSelectedReviewSessionId(session.session_id)
      setSelectedRunId(session.run_ids?.[0] || '')
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      updateTab('review')
      await loadWrongQueue()
      appendProgress({
        level: 'success',
        scope: 'review',
        message: `Opened saved review session with ${session.items.length} item(s)`,
        detail: `session_id=${session.session_id}`,
      })
      toast.success(`Loaded saved review session ${sessionId}`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to load saved review session')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'review', message: 'Saved review session load failed', detail: message })
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [appendProgress, beginReviewSessionSwap, describeError, loadWrongQueue, selectedReviewSessionId, updateTab])

  const handleSelectReviewSessionHistory = useCallback((sessionId: string) => {
    setSelectedReviewSessionId(sessionId)
    void handleInspectSelectedReviewSession(sessionId)
  }, [handleInspectSelectedReviewSession])

  const handleSelectRunGroup = useCallback(async (runIds: string[]) => {
    if (runIds.length === 0) return
    setSelectedRunId(runIds[0])
    updateTab('runs')

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap(`Loading review session for group of ${runIds.length} runs...`)
    try {
      appendProgress({
        scope: 'review',
        message: `Creating bundled review session for ${runIds.length} run(s)`,
        detail: runIds.map((runId) => runId.slice(0, 12)).join(', '),
      })
      const session = await createExtractionReviewSession({ runIds })
      setReviewSession(session)
      setSelectedReviewSessionId(session.session_id)
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      await loadWrongQueue()
      void handleLoadReviewSessions(ticker.trim().toUpperCase())
      appendProgress({
        level: 'success',
        scope: 'review',
        message: `Loaded bundled review session with ${session.items.length} item(s)`,
        detail: `session_id=${session.session_id}`,
      })
      toast.success(`Loaded bundled review session for ${runIds.length} runs`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to inspect selected group')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'review', message: 'Bundled review load failed', detail: message })
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [appendProgress, beginReviewSessionSwap, describeError, handleLoadReviewSessions, loadWrongQueue, ticker, updateTab])

  const handleLoadReview = useCallback(async (documentIds?: string[]) => {
    if (reviewActionLockRef.current) return
    const targetDocumentIds = Array.isArray(documentIds) ? documentIds : selectedReviewDocumentIds
    if (targetDocumentIds.length === 0) {
      setReviewError('Select one document or enter document IDs first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap('Loading a fresh review session for the selected document set...')
    try {
      appendProgress({
        scope: 'review',
        message: `Building latest review session for ${targetDocumentIds.length} document(s)`,
        detail: targetDocumentIds.map((id) => id.slice(0, 12)).join(', '),
      })
      const { queuedIds, failedRuns, runIds, runIdsByDocumentId } = await runSelectedDocumentExtractions(targetDocumentIds)
      if (Object.keys(runIdsByDocumentId).length > 0) {
        const next = { ...activeRunIdsByDocumentId, ...runIdsByDocumentId }
        persistActiveRuns(next)
        await refreshRunStatuses(runIdsByDocumentId)
      }

      if (queuedIds.length > 0) {
        const message = `Extraction is queued for ${queuedIds.length} document(s). Wait for the worker to finish, then retry loading the review.`
        setReviewError(message)
        appendProgress({ level: 'warning', scope: 'review', message, detail: queuedIds.join(', ') })
        toast.info(message)
        return
      }

      if (failedRuns.length > 0) {
        await loadWrongQueue()
        const message = `Latest extraction failed or produced no reviewable metrics for: ${failedRuns.join(', ')}`
        setReviewError(message)
        appendProgress({ level: 'error', scope: 'review', message })
        toast.error(message)
        return
      }

      appendProgress({
        scope: 'review',
        message: `Creating backend review session from ${runIds.length} run(s)`,
        detail: runIds.map((runId) => runId.slice(0, 12)).join(', '),
      })
      const session = await createExtractionReviewSession({ runIds })
      setReviewSession(session)
      setSelectedReviewSessionId(session.session_id)
      setSelectedRunId(runIds[0] ?? '')
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      await loadWrongQueue()
      void handleLoadReviewSessions(ticker.trim().toUpperCase())

      if (session.items.length > 0) {
        appendProgress({
          level: 'success',
          scope: 'review',
          message: `Loaded ${session.items.length} review item(s)`,
          detail: `session_id=${session.session_id}`,
        })
        toast.success(`Loaded ${session.items.length} review item(s)`)
      } else {
        const diagnostic = summarizeSessionDocuments(session)
        setReviewError(`No reviewable extracted metrics were available for the selected document set. ${diagnostic}`)
        appendProgress({
          level: 'warning',
          scope: 'review',
          message: 'Review session loaded with no reviewable extracted metrics',
          detail: diagnostic,
        })
        toast.error('No reviewable extracted metrics were available for the selected document set')
      }
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to load review session')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'review', message: 'Review session load failed', detail: message })
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [
    activeRunIdsByDocumentId,
    appendProgress,
    beginReviewSessionSwap,
    describeError,
    loadWrongQueue,
    handleLoadReviewSessions,
    persistActiveRuns,
    refreshRunStatuses,
    runSelectedDocumentExtractions,
    selectedReviewDocumentIds,
    ticker,
  ])

  const handleInspectResult = useCallback((result: VerificationResult) => {
    updateTab('review')
    appendProgress({
      scope: 'verify',
      message: `Opening review workflow for ${result.metric}`,
      detail: result.document_id ? `document_id=${result.document_id}` : result.details,
    })

    if (result.document_id) {
      setSelectedDocumentId(result.document_id)

      // If the document is not in our current review items, we should trigger a load.
      const isDocInSession = reviewSession?.document_ids?.includes(result.document_id)
        || reviewItems.some((item) => item.document_id === result.document_id)

      if (!isDocInSession) {
        const nextDocumentIds = parseDocumentIds(extraDocumentIds)
        if (!nextDocumentIds.includes(result.document_id)) {
          nextDocumentIds.unshift(result.document_id)
        }
        setExtraDocumentIds((current) => {
          const existing = parseDocumentIds(current)
          if (existing.includes(result.document_id!)) return current
          return existing.length > 0 ? `${current}, ${result.document_id}` : result.document_id!
        })
        void handleLoadReview(nextDocumentIds)
      }
    }

    if (result.item_id) {
      setSelectedReviewItemId(result.item_id)
    } else if (result.metric) {
      const match = reviewItems.find((item) => item.metric_name === result.metric)
      if (match) {
        setSelectedReviewItemId(match.item_id)
      }
    }

    toast.info(`Inspecting ${result.metric}. Review evidence for ${result.document_id ? result.document_id.slice(0, 12) : 'the document'}...`)
  }, [appendProgress, extraDocumentIds, handleLoadReview, reviewItems, reviewSession, updateTab])

  const handleRunGoldEval = useCallback(async () => {
    setGoldEvalLoading(true)
    setGoldEvalError(null)
    try {
      const parsedLimit = Number.parseInt(goldLimit, 10)
      const resolvedLimit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : 0
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (BROWSER_API_KEY) {
        headers['X-API-Key'] = BROWSER_API_KEY
      }

      appendProgress({
        scope: 'gold',
        message: 'Scheduling Real-Gold evaluation as a backend background task',
        detail: `limit=${resolvedLimit} method=${extractionMethod} strict=${strictMethod}`,
      })
      const response = await fetch('/api/extraction-eval/real-gold?background=true', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          limit: resolvedLimit,
          method: extractionMethod,
          strict_method: strictMethod,
        }),
      })

      if (response.status !== 202) {
        throw new Error(await fetchErrorDetail(response, `Gold set evaluation scheduling failed (HTTP ${response.status})`))
      }

      const scheduled = await response.json() as RealGoldEvalTaskResponse
      if (!scheduled.task_id) {
        throw new Error('Gold set evaluation scheduling did not return a task_id')
      }

      appendProgress({
        level: 'success',
        scope: 'gold',
        message: `Real-Gold task scheduled (${scheduled.status})`,
        detail: `task_id=${scheduled.task_id}`,
      })

      const startedAt = Date.now()
      let pollCount = 0
      let lastStatus = String(scheduled.status || 'pending')
      const seenProgressEvents = new Set<string>()

      while (Date.now() - startedAt < GOLD_EVAL_TIMEOUT_MS) {
        await sleep(GOLD_EVAL_POLL_INTERVAL_MS)
        pollCount += 1

        const pollResponse = await fetch(`/api/extraction-eval/real-gold/tasks/${encodeURIComponent(scheduled.task_id)}`, {
          headers,
          cache: 'no-store',
        })
        if (!pollResponse.ok) {
          throw new Error(await fetchErrorDetail(pollResponse, `Gold set evaluation polling failed (HTTP ${pollResponse.status})`))
        }

        const task = await pollResponse.json() as RealGoldEvalTaskResponse
        const status = String(task.status || 'unknown')
        const progressEvents = task.progress || []
        progressEvents.forEach((event, index) => {
          const key = realGoldProgressKey(event, index)
          if (seenProgressEvents.has(key)) return
          seenProgressEvents.add(key)
          appendProgress({
            level: realGoldProgressLevel(event),
            scope: 'gold',
            message: realGoldProgressMessage(event),
            detail: realGoldProgressDetail(event),
          })
        })
        const elapsedSeconds = Math.round((Date.now() - startedAt) / 1000)
        if (status !== lastStatus || pollCount === 1 || pollCount % 4 === 0) {
          appendProgress({
            scope: 'gold',
            message: `Real-Gold task ${status}`,
            detail: `task_id=${scheduled.task_id} elapsed=${elapsedSeconds}s polls=${pollCount}`,
          })
        }
        lastStatus = status

        if (status === 'completed') {
          if (!task.result) {
            throw new Error('Gold set evaluation completed without a result payload')
          }
          const data = task.result
          setGoldEval(data)
          appendProgress({
            level: 'success',
            scope: 'gold',
            message: `Gold eval completed for ${data.summary.total_documents} document(s)`,
            detail: `metric_accuracy=${(data.summary.total_accuracy * 100).toFixed(1)}% context_accuracy=${(data.summary.context_accuracy * 100).toFixed(1)}%`,
          })
          toast.success(
            `Gold set evaluation finished for ${data.summary.total_documents} document(s) using ${formatMethodLabel(data.requested_method || extractionMethod)}${strictMethod ? ' (strict)' : ''}`,
          )
          return
        }

        if (status === 'failed') {
          throw new Error(task.error || 'Gold set evaluation failed')
        }
      }

      throw new Error('Gold set evaluation timed out while polling background task')
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to run gold set evaluation')
      setGoldEvalError(message)
      appendProgress({ level: 'error', scope: 'gold', message: 'Gold eval failed', detail: message })
      toast.error(message)
    } finally {
      setGoldEvalLoading(false)
    }
  }, [appendProgress, describeError, extractionMethod, goldLimit, strictMethod])

  const handleLoadMetricCoverageLatest = useCallback(async () => {
    setMetricCoverageLoading(true)
    setMetricCoverageError(null)
    try {
      appendProgress({
        scope: 'metric coverage',
        message: 'Loading latest confirmed metric coverage review artifact',
      })
      const [summaryResponse, rowsResponse] = await Promise.all([
        fetch('/api/extraction-eval/confirmed-metric-coverage/summary', { cache: 'no-store' }),
        fetch('/api/extraction-eval/confirmed-metric-coverage/rows', { cache: 'no-store' }),
      ])
      if (!summaryResponse.ok) {
        throw new Error(await fetchErrorDetail(summaryResponse, `Coverage summary load failed (HTTP ${summaryResponse.status})`))
      }
      if (!rowsResponse.ok) {
        throw new Error(await fetchErrorDetail(rowsResponse, `Coverage rows load failed (HTTP ${rowsResponse.status})`))
      }
      const summaryPayload = await summaryResponse.json() as Partial<ConfirmedMetricCoveragePacket> & {
        summary?: ConfirmedMetricCoverageSummary | null
        artifacts?: ConfirmedMetricCoverageArtifacts | null
      }
      const rowsPayload = await rowsResponse.json() as Partial<ConfirmedMetricCoveragePacket> & {
        rows?: ConfirmedMetricCoverageRow[]
        count?: number
        artifacts?: ConfirmedMetricCoverageArtifacts | null
      }
      const merged = mergeMetricCoverageResponses(summaryPayload, rowsPayload)
      setMetricCoverage(merged)
      appendProgress({
        level: merged.status === 'not_generated' ? 'warning' : 'success',
        scope: 'metric coverage',
        message: merged.status === 'not_generated'
          ? 'No confirmed metric coverage review artifact has been generated yet'
          : `Loaded confirmed metric coverage review with ${merged.rows.length} row(s)`,
        detail: merged.artifacts?.json_path ? `artifact=${merged.artifacts.json_path}` : undefined,
      })
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to load confirmed metric coverage review')
      setMetricCoverageError(message)
      appendProgress({ level: 'error', scope: 'metric coverage', message: 'Coverage review load failed', detail: message })
    } finally {
      setMetricCoverageLoading(false)
    }
  }, [appendProgress, describeError])

  const handleRunMetricCoverageReview = useCallback(async () => {
    setMetricCoverageRunning(true)
    setMetricCoverageError(null)
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (BROWSER_API_KEY) {
        headers['X-API-Key'] = BROWSER_API_KEY
      }
      appendProgress({
        scope: 'metric coverage',
        message: 'Generating confirmed metric coverage review packet',
        detail: 'dry_run=true extraction=false',
      })
      const response = await fetch('/api/extraction-eval/confirmed-metric-coverage/run', {
        method: 'POST',
        headers,
      })
      if (!response.ok) {
        throw new Error(await fetchErrorDetail(response, `Coverage review generation failed (HTTP ${response.status})`))
      }
      const payload = await response.json() as ConfirmedMetricCoveragePacket
      setMetricCoverage(payload)
      appendProgress({
        level: payload.status === 'ready' ? 'success' : 'warning',
        scope: 'metric coverage',
        message: `Confirmed metric coverage review ${payload.status}`,
        detail: `rows=${payload.rows.length} artifact=${payload.artifacts?.json_path || 'DATA_MISSING'}`,
      })
      toast.success(`Confirmed metric coverage review generated (${payload.rows.length} rows)`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to run confirmed metric coverage review')
      setMetricCoverageError(message)
      appendProgress({ level: 'error', scope: 'metric coverage', message: 'Coverage review generation failed', detail: message })
      toast.error(message)
    } finally {
      setMetricCoverageRunning(false)
    }
  }, [appendProgress, describeError])

  useEffect(() => {
    void handleLoadMetricCoverageLatest()
  }, [handleLoadMetricCoverageLatest])

  const handleOpenGoldEvalReviewSession = useCallback(async (sessionId: string) => {
    if (reviewActionLockRef.current) return
    if (!sessionId.trim()) {
      setGoldEvalError('Selected gold-eval document does not expose a backend review session.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap(`Loading backend review session ${sessionId}...`)
    try {
      appendProgress({ scope: 'gold', message: `Opening Real-Gold review session ${sessionId}` })
      const session = await getExtractionReviewSession(sessionId)
      setReviewSession(session)
      setSelectedReviewSessionId(session.session_id)
      setSelectedRunId(session.run_ids?.[0] || '')
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      updateTab('review')
      await loadWrongQueue()
      appendProgress({
        level: 'success',
        scope: 'gold',
        message: `Loaded Real-Gold review session with ${session.items.length} item(s)`,
        detail: `session_id=${session.session_id}`,
      })
      toast.success(`Loaded backend review session for ${session.document_ids[0] || 'gold-eval document'}`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to load backend review session')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'gold', message: 'Real-Gold review session load failed', detail: message })
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [appendProgress, beginReviewSessionSwap, describeError, loadWrongQueue, updateTab])

  const handleSubmitReview = useCallback(async (verdict: 'correct' | 'wrong' | 'unsure') => {
    if (reviewActionLockRef.current) return
    if (!reviewSession || !currentReviewItem) return

    const status = verdict === 'correct' ? 'approved' : verdict === 'unsure' ? 'abstain' : 'wrong'
    const nextSelectedItemId = reviewItems[currentReviewIndex + 1]?.item_id ?? currentReviewItem.item_id

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    try {
      appendProgress({
        scope: 'review',
        message: `Saving ${verdict} verdict for ${currentReviewItem.metric_name}`,
        detail: `session_id=${reviewSession.session_id} item_id=${currentReviewItem.item_id}`,
      })
      const result = await submitExtractionReviewDecision({
        sessionId: reviewSession.session_id,
        itemId: currentReviewItem.item_id,
        status,
      })

      const nextItems = [...reviewItems]
      nextItems[currentReviewIndex] = result.item
      const nextSession: ExtractionReviewSession = {
        ...reviewSession,
        items: nextItems,
        summary: result.summary,
      }
      setReviewSession(nextSession)
      setSelectedReviewItemId(nextSelectedItemId)
      await loadWrongQueue()
      appendProgress({
        level: 'success',
        scope: 'review',
        message: `${currentReviewItem.metric_name} marked ${verdict}`,
        detail: `pending=${result.summary.pending} correct=${result.summary.approved} wrong=${result.summary.wrong} unsure=${result.summary.abstain}`,
      })
      toast.success(`${currentReviewItem.metric_name} marked ${verdict}`)
    } catch (err: unknown) {
      const message = describeError(err, 'Failed to save review decision')
      setReviewError(message)
      appendProgress({ level: 'error', scope: 'review', message: 'Review verdict save failed', detail: message })
      toast.error(message)
    } finally {
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [appendProgress, currentReviewIndex, currentReviewItem, describeError, loadWrongQueue, reviewItems, reviewSession])

  useEffect(() => {
    if (!activeRunId) {
      setRunStatus(null)
      return
    }
    if (unavailableRunStatusIds.has(activeRunId)) {
      setRunStatus(null)
      setRunStatusLoading(false)
      return
    }

    let cancelled = false
    setRunStatusLoading(true)
    void loadRunStatus(activeRunId)
      .then((payload) => {
        if (!cancelled) {
          setRunStatus(payload)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load run timeline'
          setReviewError(message)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setRunStatusLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [activeRunId, loadRunStatus, unavailableRunStatusIds])

  useEffect(() => {
    if (activeTab !== 'review' || !currentReviewItem) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (isKeyboardShortcutBlocked(event.target)) return
      if (reviewActionLoading || evidenceSuspendMessage) return

      if (event.key === 'c' || event.key === 'C') {
        event.preventDefault()
        void handleSubmitReview('correct')
      } else if (event.key === 'w' || event.key === 'W') {
        event.preventDefault()
        void handleSubmitReview('wrong')
      } else if (event.key === 'u' || event.key === 'U') {
        event.preventDefault()
        void handleSubmitReview('unsure')
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault()
        moveReviewSelection('prev')
      } else if (event.key === 'ArrowRight') {
        event.preventDefault()
        moveReviewSelection('next')
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [activeTab, currentReviewItem, evidenceSuspendMessage, handleSubmitReview, moveReviewSelection, reviewActionLoading])

  if (!hasHydrated) return null

  const handleExportJson = () => {
    if (!results) return
    const payload = {
      ticker: ticker || 'broad',
      exportedAt: new Date().toISOString(),
      summary: {
        passed: results.filter((result) => result.passed).length,
        failed: results.filter((result) => !result.passed).length,
        total: results.length,
      },
      results,
    }
    const filename = `verification-${ticker || 'broad'}-${new Date().toISOString().slice(0, 10)}.json`
    downloadFile(JSON.stringify(payload, null, 2), filename, 'application/json')
  }

  const handleExportHtml = () => {
    if (!results) return
    const passed = results.filter((result) => result.passed).length
    const failed = results.filter((result) => !result.passed).length
    const rate = results.length > 0 ? ((passed / results.length) * 100).toFixed(0) : '0'

    const rows = results.map((result) => {
      const statusIcon = result.passed ? '&#10003;' : '&#10007;'
      const statusColor = result.passed ? '#22c55e' : '#ef4444'
      return `<tr>
        <td style="color:${statusColor};text-align:center;font-size:18px">${statusIcon}</td>
        <td>${escapeHtml(result.metric)}</td>
        <td style="text-align:right;font-family:monospace">${escapeHtml(String(result.expected))}</td>
        <td style="text-align:right;font-family:monospace">${escapeHtml(String(result.actual))}</td>
        <td style="color:#888">${escapeHtml(result.details || '-')}</td>
      </tr>`
    }).join('\n')

    const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Verification Report – ${escapeHtml(ticker || 'Broad')}</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;color:#e0e0e0;background:#0a0a0a}
  h1{font-size:1.4rem}
  .summary{display:flex;gap:2rem;margin:1rem 0}
  .summary div{text-align:center;padding:1rem;border-radius:8px;background:#1a1a1a;min-width:100px}
  .summary .val{font-size:2rem;font-weight:700;font-family:monospace}
  table{width:100%;border-collapse:collapse;margin-top:1rem}
  th,td{padding:8px 12px;border-bottom:1px solid #222;text-align:left;font-size:0.9rem}
  th{background:#111;color:#aaa;font-weight:600}
</style></head><body>
<h1>Verification Report${ticker ? ` — ${escapeHtml(ticker)}` : ''}</h1>
<p style="color:#888">Generated ${new Date().toLocaleString()}</p>
<div class="summary">
  <div><div class="val" style="color:#22c55e">${passed}</div><div>Passed</div></div>
  <div><div class="val" style="color:#ef4444">${failed}</div><div>Failed</div></div>
  <div><div class="val" style="color:#3b82f6">${rate}%</div><div>Pass Rate</div></div>
</div>
<table><thead><tr><th>Status</th><th>Metric</th><th style="text-align:right">Expected</th><th style="text-align:right">Actual</th><th>Details</th></tr></thead>
<tbody>${rows}</tbody></table>
</body></html>`

    const filename = `verification-${ticker || 'broad'}-${new Date().toISOString().slice(0, 10)}.html`
    downloadFile(html, filename, 'text/html')
  }

  const handleExportReviewArtifacts = () => {
    if (!reviewSession) return
    const date = new Date().toISOString().slice(0, 10)
    downloadFile(JSON.stringify(reviewSession, null, 2), `extraction-review-${date}.json`, 'application/json')
    if (wrongQueue) {
      downloadFile(JSON.stringify(wrongQueue, null, 2), `extraction-review-wrong-queue-${date}.json`, 'application/json')
    }
  }

  const handleExportGoldEvalJson = () => {
    if (!goldEval) return
    const date = new Date().toISOString().slice(0, 10)
    downloadFile(JSON.stringify(goldEval, null, 2), `real-gold-eval-${date}.json`, 'application/json')
  }

  const handleExportMetricCoverageJson = () => {
    if (!metricCoverage) return
    const date = new Date().toISOString().slice(0, 10)
    downloadFile(JSON.stringify(metricCoverage, null, 2), `confirmed-metric-coverage-${date}.json`, 'application/json')
  }

  const handleExportMetricCoverageMarkdown = () => {
    if (!metricCoverage) return
    const date = new Date().toISOString().slice(0, 10)
    downloadFile(renderMetricCoverageMarkdown(metricCoverage), `confirmed-metric-coverage-${date}.md`, 'text/markdown')
  }

  const runStatusCards = selectedRunStatuses.map(({ documentId, runId, status }) => {
    const document = documents.find((entry) => entry.document_id === documentId)
    return {
      documentId,
      runId,
      status,
      title: document?.title || attachedRunMetadataByDocumentId[documentId]?.title || documentId,
      fallbackMethod: attachedRunMetadataByDocumentId[documentId]?.requestedMethod || extractionMethod,
    }
  })

  return (
    <div className={cn(
      "flex h-full min-h-0 w-full",
      isIPhoneScale ? "gap-2 p-2" : "gap-6 p-6"
    )}>
      <Tabs value={activeTab} onValueChange={updateTab} className={cn(
        "flex min-w-0 flex-1 flex-col",
        isIPhoneScale ? "gap-2" : "gap-4"
      )}>
        <VerificationHeader
          ticker={ticker}
          extractionMethod={extractionMethod}
          strictMethod={strictMethod}
          reviewSession={reviewSession}
          failedChecksCount={failedChecksCount}
          onTickerChange={setTicker}
          onMethodChange={setExtractionMethod}
          onStrictMethodChange={setStrictMethod}
        />

        <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          Run or review evidence checks. Start with Guided Review or Verify, then use Runs and Real-Gold for deeper validation.
        </div>

        <VerificationTabBar
          wrongQueueCount={wrongQueue?.count ?? 0}
          pendingCount={reviewSession?.summary?.pending ?? 0}
          failedChecksCount={failedChecksCount}
        />

        {isIPhoneScale ? (
          <VerificationProgressLog
            entries={progressLog}
            onClear={clearProgressLog}
            compact
          />
        ) : null}

        <div className="min-h-0 flex-1">
          <TabsContent value="review" className="m-0 h-full min-h-0 outline-none data-[state=active]:flex">
            <ScrollArea className="h-full w-full">
              <div className="pr-4">
                <ReviewTabPanel
                  documents={documents}
                  documentsLoading={documentsLoading}
                  docsLimit={docsLimit}
                  extraDocumentIds={extraDocumentIds}
                  reviewError={reviewError}
                  reviewActionLoading={reviewActionLoading}
                  reviewSession={reviewSession}
                  reviewSessionLoadingMessage={reviewSessionLoadingMessage}
                  wrongQueue={wrongQueue}
                  recentRuns={recentRuns}
                  recentRunsLoading={recentRunsLoading}
                  recentRunsError={recentRunsError}
                  recentReviewSessions={recentReviewSessions}
                  recentReviewSessionsLoading={recentReviewSessionsLoading}
                  recentReviewSessionsError={recentReviewSessionsError}
                  selectedRunId={selectedRunId}
                  selectedReviewSessionId={selectedReviewSessionId}
                  selectedDocumentId={selectedDocumentId}
                  selectedReviewDocumentIds={selectedReviewDocumentIds}
                  currentReviewItem={currentReviewItem}
                  currentReviewIndex={currentReviewIndex}
                  currentEvidenceQuality={currentEvidenceQuality}
                  matchedEvidenceText={matchedEvidenceText}
                  currentSnippetPath={currentSnippetPath}
                  currentSnippetUrl={currentSnippetUrl}
                  currentSnippetImageSrc={snippetImageUrl}
                  currentSnippetRenderKey={currentSnippetRenderKey}
                  currentRowRef={currentRowRef}
                  reviewItems={reviewItems}
                  evidenceSuspendMessage={evidenceSuspendMessage}
                  snippetImageState={snippetImageState}
                  hasPrevReviewItem={hasPrevReviewItem}
                  hasNextReviewItem={hasNextReviewItem}
                  onDocsLimitChange={setDocsLimit}
                  onExtraDocumentIdsChange={setExtraDocumentIds}
                  onLoadDocuments={handleLoadDocuments}
                  onRunExtraction={handleRunExtraction}
                  onLoadReview={handleLoadReview}
                  onRefreshWrongQueue={() => void loadWrongQueue()}
                  onExportReviewArtifacts={handleExportReviewArtifacts}
                  onSelectedRunIdChange={setSelectedRunId}
                  onLoadRecentRuns={() => void handleLoadRecentRuns()}
                  onInspectSelectedRun={() => void handleInspectSelectedRun()}
                  onSelectedReviewSessionIdChange={setSelectedReviewSessionId}
                  onLoadReviewSessions={() => void handleLoadReviewSessions()}
                  onInspectSelectedReviewSession={() => void handleInspectSelectedReviewSession()}
                  onSelectedDocumentIdChange={setSelectedDocumentId}
                  onMoveReviewSelection={moveReviewSelection}
                  onSelectedReviewItemIdChange={setSelectedReviewItemId}
                  onSnippetImageLoad={handleSnippetImageLoad}
                  onSnippetImageError={handleSnippetImageError}
                  onSubmitReview={(verdict) => void handleSubmitReview(verdict)}
                />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="runs" className="m-0 h-full min-h-0 outline-none data-[state=active]:flex">
            <ScrollArea className="h-full w-full">
              <div className="space-y-8 pr-4">
                <RunsTabPanel
                  attachActiveRuns={attachActiveRuns}
                  activeMonitorNotice={activeMonitorNotice}
                  statusCards={runStatusCards}
                  runStatusLoading={runStatusLoading}
                  activeRunId={activeRunId}
                  runStatus={runStatus}
                />
                
                {selectedRunId && (
                  <div className="border-t border-border/40 pt-8">
                    <div className="mb-4 flex items-center gap-2">
                      <Badge variant="outline" className="px-2 py-0.5">Review Panel</Badge>
                      <div className="h-px flex-1 bg-border/40" />
                    </div>
                    <ReviewTabPanel
                      documents={documents}
                      documentsLoading={documentsLoading}
                      docsLimit={docsLimit}
                      extraDocumentIds={extraDocumentIds}
                      reviewError={reviewError}
                      reviewActionLoading={reviewActionLoading}
                      reviewSession={reviewSession}
                      reviewSessionLoadingMessage={reviewSessionLoadingMessage}
                      wrongQueue={wrongQueue}
                      recentRuns={recentRuns}
                      recentRunsLoading={recentRunsLoading}
                      recentRunsError={recentRunsError}
                      recentReviewSessions={recentReviewSessions}
                      recentReviewSessionsLoading={recentReviewSessionsLoading}
                      recentReviewSessionsError={recentReviewSessionsError}
                      selectedRunId={selectedRunId}
                      selectedReviewSessionId={selectedReviewSessionId}
                      selectedDocumentId={selectedDocumentId}
                      selectedReviewDocumentIds={selectedReviewDocumentIds}
                      currentReviewItem={currentReviewItem}
                      currentReviewIndex={currentReviewIndex}
                      currentEvidenceQuality={currentEvidenceQuality}
                      matchedEvidenceText={matchedEvidenceText}
                      currentSnippetPath={currentSnippetPath}
                      currentSnippetUrl={currentSnippetUrl}
                      currentSnippetImageSrc={snippetImageUrl}
                      currentSnippetRenderKey={currentSnippetRenderKey}
                      currentRowRef={currentRowRef}
                      reviewItems={reviewItems}
                      evidenceSuspendMessage={evidenceSuspendMessage}
                      snippetImageState={snippetImageState}
                      hasPrevReviewItem={hasPrevReviewItem}
                      hasNextReviewItem={hasNextReviewItem}
                      onDocsLimitChange={setDocsLimit}
                      onExtraDocumentIdsChange={setExtraDocumentIds}
                      onLoadDocuments={handleLoadDocuments}
                      onRunExtraction={handleRunExtraction}
                      onLoadReview={handleLoadReview}
                      onRefreshWrongQueue={() => void loadWrongQueue()}
                      onExportReviewArtifacts={handleExportReviewArtifacts}
                      onSelectedRunIdChange={setSelectedRunId}
                      onLoadRecentRuns={() => void handleLoadRecentRuns()}
                      onInspectSelectedRun={() => void handleInspectSelectedRun()}
                      onSelectedReviewSessionIdChange={setSelectedReviewSessionId}
                      onLoadReviewSessions={() => void handleLoadReviewSessions()}
                      onInspectSelectedReviewSession={() => void handleInspectSelectedReviewSession()}
                      onSelectedDocumentIdChange={setSelectedDocumentId}
                      onMoveReviewSelection={moveReviewSelection}
                      onSelectedReviewItemIdChange={setSelectedReviewItemId}
                      onSnippetImageLoad={handleSnippetImageLoad}
                      onSnippetImageError={handleSnippetImageError}
                      onSubmitReview={(verdict) => void handleSubmitReview(verdict)}
                    />
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="gold-eval" className="m-0 h-full min-h-0 outline-none data-[state=active]:flex">
            <ScrollArea className="h-full w-full">
              <div className="pr-4">
                <GoldEvalTabPanel
                  goldLimit={goldLimit}
                  goldEvalLoading={goldEvalLoading}
                  goldEvalError={goldEvalError}
                  goldEval={goldEval}
                  extractionMethod={extractionMethod}
                  onGoldLimitChange={setGoldLimit}
                  onRunGoldEval={() => void handleRunGoldEval()}
                  onExportGoldEvalJson={handleExportGoldEvalJson}
                  onOpenReviewSession={(sessionId) => void handleOpenGoldEvalReviewSession(sessionId)}
                />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="metric-coverage" className="m-0 h-full min-h-0 outline-none data-[state=active]:flex">
            <ScrollArea className="h-full w-full">
              <div className="pr-4">
                <MetricCoverageTabPanel
                  packet={metricCoverage}
                  loading={metricCoverageLoading}
                  running={metricCoverageRunning}
                  error={metricCoverageError}
                  onLoadLatest={() => void handleLoadMetricCoverageLatest()}
                  onRunReview={() => void handleRunMetricCoverageReview()}
                  onExportJson={handleExportMetricCoverageJson}
                  onExportMarkdown={handleExportMetricCoverageMarkdown}
                />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="verify" className="m-0 h-full min-h-0 outline-none data-[state=active]:flex">
            <ScrollArea className="h-full w-full">
              <div className="space-y-4 pr-4">
                <VerifyTabPanel
                  ticker={ticker}
                  isRunning={isRunning}
                  error={error}
                  results={results}
                  onRunVerification={(broad) => void handleRunVerification(broad)}
                  onExportJson={handleExportJson}
                  onExportHtml={handleExportHtml}
                  onInspectResult={handleInspectResult}
                />

                <div className="mt-4 rounded border border-border/40 p-3">
                  <h3 className="mb-2 text-sm font-semibold text-muted-foreground">
                    Recent Verification Runs
                  </h3>
                  {verificationHistoryLoading && verificationRunHistory.length === 0 ? (
                    <p className="text-xs text-muted-foreground">Loading history...</p>
                  ) : verificationRunHistory.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      No saved verification runs yet.
                    </p>
                  ) : (
                    <div className="space-y-1">
                      {verificationRunHistory.map((run) => (
                        <div
                          key={run.run_id}
                          className="flex items-center justify-between border-b border-border/30 py-1 text-sm last:border-0"
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs font-bold">
                              {run.ticker}
                            </span>
                            <span className={run.passed ? 'text-green-600' : 'text-red-500'}>
                              {run.passed ? 'Pass' : 'Fail'}
                            </span>
                            <span className="truncate text-xs text-muted-foreground">
                              {run.outcome_summary || new Date(run.timestamp).toLocaleDateString()}
                            </span>
                          </div>
                          <button
                            type="button"
                            className="ml-2 shrink-0 text-xs text-blue-500 hover:underline"
                            onClick={() => handleSelectHistoryTicker(run.ticker)}
                          >
                            Re-run
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </div>

        <VerificationStatusStrip
          wrongQueueCount={wrongQueue?.count ?? 0}
          pendingCount={reviewSession?.summary?.pending ?? 0}
          activeRunId={activeRunId}
          attachActiveRuns={attachActiveRuns}
        />
      </Tabs>

      {!isIPhoneScale && (
        <aside className="flex w-80 shrink-0 flex-col gap-4 border-l border-border/40 pl-6">
          <VerificationProgressLog
            entries={progressLog}
            onClear={clearProgressLog}
          />
          <div className="min-h-0 flex-1">
            <VerificationSidebar
              recentRuns={recentRuns}
              recentReviewSessions={recentReviewSessions}
              loading={recentRunsLoading}
              onSelectTicker={handleSelectHistoryTicker}
              onSelectRun={handleSelectHistoryRun}
              onSelectSession={handleSelectReviewSessionHistory}
              onSelectRunGroup={handleSelectRunGroup}
              activeTicker={ticker}
            />
          </div>
        </aside>
      )}
    </div>
  )
}
