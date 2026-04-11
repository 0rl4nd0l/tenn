'use client'

import Image from 'next/image'
import { useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle2,
  FileImage,
  FileJson,
  FileText,
  Play,
  RefreshCw,
  Search,
  XCircle,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  createExtractionReviewSession,
  getExtractionReviewErrors,
  getExtractionReviewRunStatus,
  getExtractionReviewRuns,
  getExtractionReviewSession,
  getTickerDocuments,
  processDocument,
  submitExtractionReviewDecision,
} from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import { cn } from '@/lib/utils'
import type {
  ContextDocument,
  ExtractionEvidenceQuality,
  ExtractionMethod,
  ExtractionReviewErrorQueue,
  ExtractionReviewItem,
  ExtractionReviewRunStatusResponse,
  ExtractionReviewRunSummary,
  ExtractionReviewSession,
  VerificationResult,
} from '@/lib/cockpit-types'

const BROWSER_API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

type RealGoldEvalMetricResult = {
  status: string
  expected: number | null
  actual: number | null
  reason: string
}

type RealGoldEvalDocument = {
  document_id: string
  extraction_status: string
  extraction_error?: string | null
  context_correct: boolean
  trust_outcome: 'trusted' | 'abstain' | 'quarantine'
  expected_trust: string
  mismatch_reasons: string[]
  metric_results: Record<string, RealGoldEvalMetricResult>
  method_provenance?: {
    requested_method?: ExtractionMethod
    actual_method?: string | null
    strict_method?: boolean
    parser_id?: string | null
    model_id?: string | null
    runtime_id?: string | null
    fallback_used?: boolean
    error_stage?: string | null
  }
}

type RealGoldEvalResponse = {
  dataset_dir: string
  requested_method?: ExtractionMethod
  strict_method?: boolean
  summary: {
    total_documents: number
    total_accuracy: number
    context_accuracy: number
    trust_matches_expected: number
    metric_status_counts: Record<string, number>
    trust_distribution: Record<string, number>
  }
  documents: RealGoldEvalDocument[]
}

type ProcessDocumentResponse = {
  mode?: string
  document_id?: string
  run_id?: string
  extraction_status?: string
  method_provenance?: {
    requested_method?: ExtractionMethod
    actual_method?: string | null
    strict_method?: boolean
    parser_id?: string | null
    model_id?: string | null
    runtime_id?: string | null
    fallback_used?: boolean
    error_stage?: string | null
    warnings?: string[]
  }
}

type SnippetImageState = {
  key: string | null
  status: 'idle' | 'loading' | 'ready' | 'retrying' | 'failed'
  retryAttempted: boolean
  message: string | null
}

type ActiveExtractionMonitorRun = {
  runId: string
  documentId: string
  requestedMethod: string | null
  strictMethod: boolean | null
  ticker: string | null
  title: string | null
  expiresInSeconds: number | null
}

const EXTRACTION_METHOD_OPTIONS: Array<{ value: ExtractionMethod; label: string }> = [
  { value: 'auto', label: 'Auto' },
  { value: 'docling', label: 'Docling' },
  { value: 'pymupdf', label: 'PyMuPDF' },
  { value: 'anthropic', label: 'Anthropic' },
]

const ACTIVE_RUNS_STORAGE_KEY = 'verification-active-runs-v1'

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function formatRawValue(v: unknown): string | number {
  if (typeof v === 'number') return v
  if (typeof v === 'string') return v
  if (v == null) return '-'
  return String(v)
}

function mapResponseToResults(data: unknown): VerificationResult[] {
  if (!data || typeof data !== 'object') {
    return [{ metric: 'Raw Response', expected: '-', actual: String(data), passed: false, details: 'Unexpected response format' }]
  }

  const items = Array.isArray(data)
    ? data
    : 'metrics' in data && Array.isArray((data as Record<string, unknown>).metrics)
      ? (data as Record<string, unknown>).metrics as unknown[]
      : null

  if (items) {
    return items.map((item: unknown, i: number) => {
      if (item && typeof item === 'object') {
        const r = item as Record<string, unknown>
        return {
          metric: String(r.metric ?? r.name ?? r.label ?? `Check ${i + 1}`),
          expected: formatRawValue(r.expected),
          actual: formatRawValue(r.actual ?? r.value),
          passed: typeof r.passed === 'boolean' ? r.passed : (r.status === 'pass' || r.status === 'ok'),
          details: r.details ? String(r.details) : undefined,
        }
      }
      return { metric: `Check ${i + 1}`, expected: '-', actual: String(item), passed: false }
    })
  }

  return [{ metric: 'Raw Response', expected: '-', actual: JSON.stringify(data, null, 2), passed: false, details: 'Unrecognized response shape' }]
}

function formatValue(value: string | number): string {
  if (typeof value === 'number') {
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
    return value.toLocaleString()
  }
  return value
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function parseDocumentIds(raw: string): string[] {
  return Array.from(
    new Set(
      raw
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  )
}

function isReviewableExtractionStatus(status: string): boolean {
  return status === 'ok' || status === 'ok_low_confidence'
}

function statusVariant(status: ExtractionReviewItem['review_status']): 'default' | 'secondary' | 'critical' | 'outline' {
  if (status === 'approved') return 'default'
  if (status === 'wrong') return 'critical'
  if (status === 'abstain') return 'secondary'
  return 'outline'
}

function reviewStatusLabel(status: ExtractionReviewItem['review_status']): string {
  if (status === 'approved') return 'correct'
  if (status === 'abstain') return 'unsure'
  return status
}

function evidenceMethodLabel(item: ExtractionReviewItem | null): string {
  if (!item) return 'unknown'
  return formatMethodLabel(item.method_provenance || item.actual_method || item.requested_method)
}

function summarizeSessionDocuments(session: ExtractionReviewSession | null): string {
  if (!session?.documents || session.documents.length === 0) {
    return 'No review session diagnostics available yet.'
  }
  return session.documents
    .map((doc) => {
      const label = doc.title || doc.document_id
      const status = doc.status || 'unknown'
      const count = typeof doc.items_count === 'number' ? doc.items_count : 0
      const reason = doc.reason ? `, ${doc.reason}` : ''
      const metrics = typeof doc.metrics_count === 'number' ? `, metrics ${doc.metrics_count}` : ''
      return `${label}: ${status}${count > 0 ? ` (${count} item${count === 1 ? '' : 's'})` : ''}${metrics}${reason}`
    })
    .join(' | ')
}

function formatMethodLabel(method: string | null | undefined): string {
  const normalized = String(method || '').trim()
  if (!normalized) return 'unknown'
  if (normalized === 'pymupdf') return 'PyMuPDF'
  if (normalized === 'pymupdf_degraded') return 'PyMuPDF degraded'
  return normalized
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatDuration(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`
  return `${value}ms`
}

function normalizeEvidenceText(value: string | null | undefined): string | null {
  const text = String(value || '').trim()
  if (!text) return null
  if (text.toLowerCase() === 'unknown') return null
  return text
}

function evidenceQualityForItem(item: ExtractionReviewItem | null): ExtractionEvidenceQuality {
  if (!item) return 'missing'
  const explicit = item.evidence_quality || item.snippet.evidence_quality
  if (explicit === 'precise' || explicit === 'approximate' || explicit === 'missing') {
    return explicit
  }

  const hasImage = Boolean(item.image_url || item.image_path || item.snippet.image_url || item.snippet.image_path)
  const matchedText = normalizeEvidenceText(item.matched_text)
    || normalizeEvidenceText(item.snippet.matched_text)
    || normalizeEvidenceText(item.evidence_text)

  if (hasImage && item.snippet.kind === 'line_crop' && matchedText) return 'precise'
  if (hasImage) return 'approximate'
  return 'missing'
}

function evidenceQualityRank(quality: ExtractionEvidenceQuality): number {
  if (quality === 'precise') return 0
  if (quality === 'approximate') return 1
  return 2
}

function evidenceQualityBadgeVariant(quality: ExtractionEvidenceQuality): 'default' | 'secondary' | 'outline' {
  if (quality === 'precise') return 'default'
  if (quality === 'approximate') return 'secondary'
  return 'outline'
}

function evidenceQualityLabel(quality: ExtractionEvidenceQuality): string {
  if (quality === 'precise') return 'precise'
  if (quality === 'approximate') return 'approximate'
  return 'missing'
}

function evidenceQualityHeadline(quality: ExtractionEvidenceQuality): string {
  if (quality === 'precise') return 'Exact line evidence'
  if (quality === 'approximate') return 'Exact line unavailable - showing source page/table preview'
  return 'No visual verification evidence available'
}

function evidenceQualityBody(quality: ExtractionEvidenceQuality): string {
  if (quality === 'precise') return 'This metric includes an exact matched line and cropped source evidence.'
  if (quality === 'approximate') return 'A source image is available, but the exact matched line was not preserved. Verify against the page/table preview.'
  return 'No snippet image was preserved for visual verification. Use provenance details only.'
}

function reviewSessionRunIds(session: ExtractionReviewSession | null): string[] {
  if (!session) return []
  const explicit = Array.isArray(session.run_ids)
    ? session.run_ids.filter((runId): runId is string => Boolean(runId))
    : []
  const fallback = session.items
    .map((item) => item.run_id)
    .filter((runId): runId is string => Boolean(runId))
  return Array.from(new Set([...explicit, ...fallback]))
}

function readMonitorString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function readMonitorNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function readMonitorBoolean(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value
  return null
}

function parseActiveExtractionMonitorRuns(payload: Record<string, unknown>): ActiveExtractionMonitorRun[] {
  const rawRuns = payload.extraction_active_runs
  if (!Array.isArray(rawRuns)) return []

  return rawRuns.flatMap((entry) => {
    if (!entry || typeof entry !== 'object') return []
    const run = entry as Record<string, unknown>
    const runId = readMonitorString(run.run_id)
    const documentId = readMonitorString(run.document_id)
    if (!runId || !documentId) return []

    return [{
      runId,
      documentId,
      requestedMethod: readMonitorString(run.requested_method),
      strictMethod: readMonitorBoolean(run.strict_method),
      ticker: readMonitorString(run.ticker),
      title: readMonitorString(run.title),
      expiresInSeconds: readMonitorNumber(run.expires_in_seconds),
    }]
  })
}

function runStatusVariant(status: string | null | undefined): 'default' | 'secondary' | 'critical' | 'outline' {
  if (status === 'succeeded') return 'default'
  if (status === 'failed' || status === 'blocked') return 'critical'
  if (status === 'running') return 'secondary'
  return 'outline'
}

function ExtractionRunStatusCard({
  documentId,
  runId,
  status,
  title,
  fallbackMethod,
}: {
  documentId: string
  runId: string
  status?: ExtractionReviewRunStatusResponse
  title?: string | null
  fallbackMethod: string
}) {
  const summary = status?.summary
  const events = status?.events ?? []

  return (
    <div className="rounded-lg border border-border/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{title || documentId}</p>
          <p className="font-mono text-xs text-muted-foreground">run {runId.slice(0, 12)} · doc {documentId.slice(0, 12)}</p>
        </div>
        <Badge variant={runStatusVariant(summary?.status)}>{summary?.status || 'pending'}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">stage {summary?.stage || 'queued'}</Badge>
        <Badge variant="outline">method {formatMethodLabel(summary?.actual_method || summary?.requested_method || fallbackMethod)}</Badge>
        <Badge variant="outline">mode {summary?.strict_method ? 'strict' : 'auto'}</Badge>
        <Badge variant="outline">elapsed {formatDuration(summary?.elapsed_ms)}</Badge>
        <Badge variant={(summary?.warning_codes?.length ?? 0) > 0 ? 'secondary' : 'outline'}>warnings {summary?.warning_codes?.length ?? 0}</Badge>
        <Badge variant={(summary?.error_codes?.length ?? 0) > 0 ? 'critical' : 'outline'}>errors {summary?.error_codes?.length ?? 0}</Badge>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{summary?.last_message || 'Waiting for worker status...'}</p>
      <div className="mt-3 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Event timeline</p>
        {events.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
            Waiting for run events...
          </div>
        ) : events.map((event, index) => (
          <div key={`${event.timestamp}-${index}`} className="rounded-md border border-border/60 bg-muted/20 p-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={runStatusVariant(event.status)}>{event.status}</Badge>
              <Badge variant="outline">{event.stage}</Badge>
              <span className="text-muted-foreground">{formatDuration(event.elapsed_ms)}</span>
            </div>
            <p className="mt-2 text-sm text-foreground">{event.message}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export function VerificationScreen() {
  const searchParams = useSearchParams()
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker } = useCockpitStore()

  const [ticker, setTicker] = useState(activeTicker || '')
  const [isRunning, setIsRunning] = useState(false)
  const [results, setResults] = useState<VerificationResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [documents, setDocuments] = useState<ContextDocument[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [extraDocumentIds, setExtraDocumentIds] = useState('')
  const [docsLimit, setDocsLimit] = useState('10')
  const [extractionMethod, setExtractionMethod] = useState<ExtractionMethod>('auto')
  const [strictMethod, setStrictMethod] = useState(true)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewActionLoading, setReviewActionLoading] = useState(false)
  const [reviewSession, setReviewSession] = useState<ExtractionReviewSession | null>(null)
  const [selectedReviewItemId, setSelectedReviewItemId] = useState<string | null>(null)
  const [reviewSessionLoadingMessage, setReviewSessionLoadingMessage] = useState<string | null>(null)
  const [activeMonitorNotice, setActiveMonitorNotice] = useState<string | null>(null)
  const [snippetImageState, setSnippetImageState] = useState<SnippetImageState>({
    key: null,
    status: 'idle',
    retryAttempted: false,
    message: null,
  })
  const [wrongQueue, setWrongQueue] = useState<ExtractionReviewErrorQueue | null>(null)
  const [recentRuns, setRecentRuns] = useState<ExtractionReviewRunSummary[]>([])
  const [recentRunsLoading, setRecentRunsLoading] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState('')
  const [activeRunIdsByDocumentId, setActiveRunIdsByDocumentId] = useState<Record<string, string>>({})
  const [attachedRunMetadataByDocumentId, setAttachedRunMetadataByDocumentId] = useState<Record<string, ActiveExtractionMonitorRun>>({})
  const [runStatus, setRunStatus] = useState<ExtractionReviewRunStatusResponse | null>(null)
  const [runStatuses, setRunStatuses] = useState<Record<string, ExtractionReviewRunStatusResponse>>({})
  const [runStatusLoading, setRunStatusLoading] = useState(false)
  const [goldLimit, setGoldLimit] = useState('10')
  const [goldEvalLoading, setGoldEvalLoading] = useState(false)
  const [goldEvalError, setGoldEvalError] = useState<string | null>(null)
  const [goldEval, setGoldEval] = useState<RealGoldEvalResponse | null>(null)
  const documentLoadLockRef = useRef(false)
  const recentRunsLoadLockRef = useRef(false)
  const reviewActionLockRef = useRef(false)
  const latestEvidenceKeyRef = useRef<string | null>(null)

  useEffect(() => {
    setHasHydrated(true)
  }, [])

  useEffect(() => {
    if (activeTicker) {
      setTicker(activeTicker)
    }
  }, [activeTicker])

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
  const currentSnippetRenderKey = `${currentEvidenceKey || 'no-evidence'}:${snippetImageState.retryAttempted ? 'retry' : 'initial'}`
  const currentRowRef = currentReviewItem?.row_refs?.[currentReviewItem.metric_name] || null
  const hasPrevReviewItem = currentReviewIndex > 0
  const hasNextReviewItem = currentReviewIndex >= 0 && currentReviewIndex < reviewItems.length - 1
  const passedCount = results?.filter((r) => r.passed).length || 0
  const totalCount = results?.length || 0
  const passRate = totalCount > 0 ? (passedCount / totalCount) * 100 : 0
  const goldSummary = goldEval?.summary ?? null

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

  useEffect(() => {
    latestEvidenceKeyRef.current = currentEvidenceKey
  }, [currentEvidenceKey])

  useEffect(() => {
    if (evidenceSuspendMessage) {
      setSnippetImageState({
        key: currentEvidenceKey,
        status: 'idle',
        retryAttempted: false,
        message: evidenceSuspendMessage,
      })
      return
    }
    if (!currentEvidenceKey || !currentSnippetUrl) {
      setSnippetImageState({
        key: currentEvidenceKey,
        status: 'idle',
        retryAttempted: false,
        message: null,
      })
      return
    }
    setSnippetImageState({
      key: currentEvidenceKey,
      status: 'loading',
      retryAttempted: false,
      message: null,
    })
  }, [currentEvidenceKey, currentSnippetUrl, evidenceSuspendMessage])

  const beginReviewSessionSwap = useCallback((message: string) => {
    setReviewSessionLoadingMessage(message)
    setReviewSession(null)
    setSelectedReviewItemId(null)
    setRunStatus(null)
    setSnippetImageState({
      key: null,
      status: 'idle',
      retryAttempted: false,
      message: message,
    })
  }, [])

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
          return [documentId, await getExtractionReviewRunStatus(runId, 200)] as const
        } catch {
          return null
        }
      }),
    )
    setRunStatuses((current) => {
      const next = { ...current }
      for (const entry of responses) {
        if (!entry) continue
        next[entry[0]] = entry[1]
      }
      return next
    })
  }, [])

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
          return
        }

        const runIdsByDocumentId = Object.fromEntries(
          activeRuns.map((run) => [run.documentId, run.runId]),
        )
        const metadataByDocumentId = Object.fromEntries(
          activeRuns.map((run) => [run.documentId, run]),
        )

        setAttachedRunMetadataByDocumentId(metadataByDocumentId)
        persistActiveRuns(runIdsByDocumentId)
        setSelectedDocumentId(activeRuns[0]?.documentId ?? '')
        setExtraDocumentIds(activeRuns.slice(1).map((run) => run.documentId).join('\n'))
        setSelectedRunId(activeRuns[0]?.runId ?? '')
        setTicker((current) => current.trim() ? current : (activeRuns[0]?.ticker || current))
        setActiveMonitorNotice(
          `Attached to ${activeRuns.length} active extraction run${activeRuns.length === 1 ? '' : 's'} from backend state.`,
        )
        await refreshRunStatuses(runIdsByDocumentId)
      } catch (err: unknown) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Failed to attach to the active extraction run'
        setAttachedRunMetadataByDocumentId({})
        setActiveMonitorNotice(message)
      }
    }

    void attachMonitor()
    return () => {
      cancelled = true
    }
  }, [attachActiveRuns, hasHydrated, persistActiveRuns, refreshRunStatuses])

  useEffect(() => {
    const activeEntries = Object.entries(activeRunIdsByDocumentId).filter(([documentId, runId]) => {
      const status = runStatuses[documentId]?.summary?.status
      return Boolean(runId) && !['succeeded', 'failed', 'blocked'].includes(String(status || ''))
    })
    if (activeEntries.length === 0) return
    let cancelled = false

    const poll = async () => {
      const responses = await Promise.all(
        activeEntries.map(async ([documentId, runId]) => {
          try {
            return [documentId, await getExtractionReviewRunStatus(runId, 200)] as const
          } catch {
            return null
          }
        }),
      )
      if (cancelled) return

      setRunStatuses((current) => {
        const next = { ...current }
        for (const entry of responses) {
          if (!entry) continue
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
  }, [activeRunIdsByDocumentId, runStatuses])

  const moveReviewSelection = useCallback((direction: 'prev' | 'next') => {
    if (currentReviewIndex < 0) return
    const delta = direction === 'next' ? 1 : -1
    const nextItem = reviewItems[currentReviewIndex + delta]
    if (!nextItem) return
    setSelectedReviewItemId(nextItem.item_id)
  }, [currentReviewIndex, reviewItems])

  const handleSnippetImageLoad = useCallback(() => {
    if (!currentEvidenceKey) return
    setSnippetImageState((previous) => {
      if (previous.key !== currentEvidenceKey) return previous
      return {
        ...previous,
        status: 'ready',
        message: null,
      }
    })
  }, [currentEvidenceKey])

  const handleSnippetImageError = useCallback(() => {
    if (!currentEvidenceKey) return

    const sessionId = reviewSession?.session_id || null
    const itemId = currentReviewItem?.item_id || null
    const fallbackMessage = currentReviewItem?.snippet.reason
      || (currentEvidenceQuality === 'approximate'
        ? 'Source page/table preview is unavailable for this session item. Exact line evidence was not preserved, so verify from provenance details only.'
        : evidenceQualityBody(currentEvidenceQuality))

    let shouldRetry = false
    setSnippetImageState((previous) => {
      if (previous.key !== currentEvidenceKey) return previous
      shouldRetry = !previous.retryAttempted && Boolean(sessionId && itemId)
      if (!shouldRetry) {
        return {
          ...previous,
          status: 'failed',
          message: fallbackMessage,
        }
      }
      return {
        ...previous,
        status: 'retrying',
        retryAttempted: true,
        message: 'Refreshing the current review session once to recover snippet evidence...',
      }
    })

    if (!shouldRetry || !sessionId || !itemId) return

    void getExtractionReviewSession(sessionId)
      .then((session) => {
        if (latestEvidenceKeyRef.current !== currentEvidenceKey) return
        setReviewSession(session)
        setSelectedReviewItemId((current) => (
          session.items.some((item) => item.item_id === itemId)
            ? itemId
            : current
        ))
        setSnippetImageState((previous) => {
          if (previous.key !== currentEvidenceKey) return previous
          return {
            ...previous,
            status: 'loading',
            message: null,
          }
        })
      })
      .catch(() => {
        if (latestEvidenceKeyRef.current !== currentEvidenceKey) return
        setSnippetImageState((previous) => {
          if (previous.key !== currentEvidenceKey) return previous
          return {
            ...previous,
            status: 'failed',
            message: fallbackMessage,
          }
        })
      })
  }, [
    currentEvidenceKey,
    currentEvidenceQuality,
    currentReviewItem,
    reviewSession?.session_id,
  ])

  const handleRunVerification = async (broad: boolean = false) => {
    setIsRunning(true)
    setResults(null)
    setError(null)

    const queryTicker = broad ? '' : ticker.trim()
    const url = queryTicker
      ? `/api/context/verification?ticker=${encodeURIComponent(queryTicker)}`
      : '/api/context/verification'

    try {
      const res = await fetch(url)
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `Verification failed (HTTP ${res.status})`)
      }

      const data: unknown = await res.json()
      setResults(mapResponseToResults(data))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unexpected error during verification'
      setError(message)
    } finally {
      setIsRunning(false)
    }
  }

  const handleLoadDocuments = async () => {
    if (documentLoadLockRef.current) return
    const cleanTicker = ticker.trim().toUpperCase()
    if (!cleanTicker) {
      setReviewError('Ticker is required to load review documents.')
      return
    }

    documentLoadLockRef.current = true
    setReviewError(null)
    setDocumentsLoading(true)
    try {
      const parsedLimit = Number.parseInt(docsLimit, 10)
      const docs = await getTickerDocuments(cleanTicker, Number.isFinite(parsedLimit) ? parsedLimit : 10)
      const runsPayload = await getExtractionReviewRuns(cleanTicker, 20)
      setDocuments(docs)
      setRecentRuns(runsPayload.items)
      const defaultDoc = docs[0]?.document_id ?? ''
      setSelectedDocumentId((current) => docs.some((doc) => doc.document_id === current) ? current : defaultDoc)
      setSelectedRunId((current) => runsPayload.items.some((run) => run.run_id === current) ? current : (runsPayload.items[0]?.run_id || ''))
      toast.success(`Loaded ${docs.length} document(s) for ${cleanTicker}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load documents'
      setReviewError(message)
      toast.error(message)
    } finally {
      documentLoadLockRef.current = false
      setDocumentsLoading(false)
    }
  }

  const runSelectedDocumentExtractions = async (): Promise<{
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

    for (const documentId of selectedReviewDocumentIds) {
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
        continue
      }
      if (!isReviewableExtractionStatus(extractionStatus)) {
        failedRuns.push(`${documentId.slice(0, 12)}:${extractionStatus || 'unknown'}`)
        continue
      }
      if (result.run_id) {
        runIds.push(result.run_id)
      }
    }

    return { queuedIds, failedRuns, runIds, runIdsByDocumentId, results }
  }

  const handleRunExtraction = async () => {
    if (reviewActionLockRef.current) return
    if (selectedReviewDocumentIds.length === 0) {
      setReviewError('Select one document or enter document IDs first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    try {
      const { queuedIds, failedRuns, results, runIdsByDocumentId } = await runSelectedDocumentExtractions()
      if (Object.keys(runIdsByDocumentId).length > 0) {
        const next = { ...activeRunIdsByDocumentId, ...runIdsByDocumentId }
        persistActiveRuns(next)
        await refreshRunStatuses(runIdsByDocumentId)
      }
      if (queuedIds.length > 0) {
        const message = `Extraction queued for ${queuedIds.length} document(s). Wait for completion before loading the review session.`
        setReviewError(message)
        toast.info(message)
        return
      }
      if (failedRuns.length > 0) {
        const message = `Latest extraction did not produce a reviewable result for: ${failedRuns.join(', ')}`
        setReviewError(message)
        toast.error(message)
        return
      }
      const methodSummary = results[0]?.method_provenance
      toast.success(
        `Extraction requested for ${selectedReviewDocumentIds.length} document(s) using ${formatMethodLabel(methodSummary?.actual_method || extractionMethod)}${strictMethod ? ' (strict)' : ''}`,
      )
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to run extraction'
      setReviewError(message)
      toast.error(message)
    } finally {
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }

  const loadWrongQueue = async () => {
    try {
      const payload = await getExtractionReviewErrors(200)
      setWrongQueue(payload)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load wrong queue'
      setReviewError(message)
    }
  }

  const handleLoadRecentRuns = async () => {
    if (recentRunsLoadLockRef.current) return
    const cleanTicker = ticker.trim().toUpperCase()
    if (!cleanTicker) {
      setReviewError('Ticker is required to inspect recent runs.')
      return
    }

    recentRunsLoadLockRef.current = true
    setRecentRunsLoading(true)
    setReviewError(null)
    try {
      const payload = await getExtractionReviewRuns(cleanTicker, 20)
      setRecentRuns(payload.items)
      setSelectedRunId((current) => payload.items.some((run) => run.run_id === current) ? current : (payload.items[0]?.run_id || ''))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load recent runs'
      setReviewError(message)
      toast.error(message)
    } finally {
      recentRunsLoadLockRef.current = false
      setRecentRunsLoading(false)
    }
  }

  const handleInspectSelectedRun = async () => {
    if (reviewActionLockRef.current) return
    if (!selectedRunId) {
      setReviewError('Select a recent run first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap(`Loading review session for run ${selectedRunId.slice(0, 12)}...`)
    try {
      const session = await createExtractionReviewSession({ runIds: [selectedRunId] })
      setReviewSession(session)
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      await loadWrongQueue()
      toast.success(`Loaded historical run ${selectedRunId.slice(0, 12)}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to inspect selected run'
      setReviewError(message)
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }

  const handleLoadReview = async () => {
    if (reviewActionLockRef.current) return
    if (selectedReviewDocumentIds.length === 0) {
      setReviewError('Select one document or enter document IDs first.')
      return
    }

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    beginReviewSessionSwap('Loading a fresh review session for the selected document set...')
    try {
      const { queuedIds, failedRuns, runIds, runIdsByDocumentId } = await runSelectedDocumentExtractions()

      if (Object.keys(runIdsByDocumentId).length > 0) {
        const next = { ...activeRunIdsByDocumentId, ...runIdsByDocumentId }
        persistActiveRuns(next)
        await refreshRunStatuses(runIdsByDocumentId)
      }

      if (queuedIds.length > 0) {
        const message = `Extraction is queued for ${queuedIds.length} document(s). Wait for the worker to finish, then retry loading the review.`
        setReviewError(message)
        toast.info(message)
        return
      }

      if (failedRuns.length > 0) {
        await loadWrongQueue()
        const message = `Latest extraction failed or produced no reviewable metrics for: ${failedRuns.join(', ')}`
        setReviewError(message)
        toast.error(message)
        return
      }

      const session = await createExtractionReviewSession({ runIds })

      setReviewSession(session)
      setSelectedRunId(runIds[0] ?? '')
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      await loadWrongQueue()

      if (session.items.length > 0) {
        toast.success(`Loaded ${session.items.length} review item(s)`)
      } else {
        const diagnostic = summarizeSessionDocuments(session)
        setReviewError(
          `No reviewable extracted metrics were available for the selected document set. ${diagnostic}`
        )
        toast.error('No reviewable extracted metrics were available for the selected document set')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load review session'
      setReviewError(message)
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }

  const handleRunGoldEval = async () => {
    setGoldEvalLoading(true)
    setGoldEvalError(null)
    try {
      const parsedLimit = Number.parseInt(goldLimit, 10)
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (BROWSER_API_KEY) {
        headers['X-API-Key'] = BROWSER_API_KEY
      }

      const res = await fetch('/api/extraction-eval/real-gold', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          limit: Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : 0,
          method: extractionMethod,
          strict_method: strictMethod,
        }),
      })

      if (!res.ok) {
        let detail = `Gold set evaluation failed (HTTP ${res.status})`
        try {
          const body = await res.json()
          if (body && typeof body === 'object' && 'detail' in body) {
            detail = String((body as { detail: unknown }).detail)
          }
        } catch {
          const text = await res.text().catch(() => '')
          if (text) detail = text
        }
        throw new Error(detail)
      }

      const data = await res.json() as RealGoldEvalResponse
      setGoldEval(data)
      toast.success(
        `Gold set evaluation finished for ${data.summary.total_documents} document(s) using ${formatMethodLabel(data.requested_method || extractionMethod)}${strictMethod ? ' (strict)' : ''}`,
      )
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to run gold set evaluation'
      setGoldEvalError(message)
      toast.error(message)
    } finally {
      setGoldEvalLoading(false)
    }
  }

  const handleSubmitReview = useCallback(async (verdict: 'correct' | 'wrong' | 'unsure') => {
    if (reviewActionLockRef.current) return
    if (!reviewSession || !currentReviewItem) return

    const status = verdict === 'correct' ? 'approved' : verdict === 'unsure' ? 'abstain' : 'wrong'
    const nextSelectedItemId = reviewItems[currentReviewIndex + 1]?.item_id ?? currentReviewItem.item_id

    reviewActionLockRef.current = true
    setReviewError(null)
    setReviewActionLoading(true)
    try {
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
      toast.success(`${currentReviewItem.metric_name} marked ${verdict}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save review decision'
      setReviewError(message)
      toast.error(message)
    } finally {
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [currentReviewIndex, currentReviewItem, reviewItems, reviewSession])

  useEffect(() => {
    if (!activeRunId) {
      setRunStatus(null)
      return
    }

    let cancelled = false
    setRunStatusLoading(true)
    void getExtractionReviewRunStatus(activeRunId, 200)
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
  }, [activeRunId])

  useEffect(() => {
    if (!currentReviewItem) return

    const onKeyDown = (event: KeyboardEvent) => {
      const tagName = (event.target as HTMLElement | null)?.tagName?.toLowerCase()
      if (tagName === 'input' || tagName === 'textarea') return
      if (reviewActionLoading) return
      if (evidenceSuspendMessage) return

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
  }, [currentReviewItem, evidenceSuspendMessage, handleSubmitReview, moveReviewSelection, reviewActionLoading])

  if (!hasHydrated) return null

  const handleExportJson = () => {
    if (!results) return
    const payload = {
      ticker: ticker || 'broad',
      exportedAt: new Date().toISOString(),
      summary: {
        passed: results.filter((r) => r.passed).length,
        failed: results.filter((r) => !r.passed).length,
        total: results.length,
      },
      results,
    }
    const filename = `verification-${ticker || 'broad'}-${new Date().toISOString().slice(0, 10)}.json`
    downloadFile(JSON.stringify(payload, null, 2), filename, 'application/json')
  }

  const handleExportHtml = () => {
    if (!results) return
    const passed = results.filter((r) => r.passed).length
    const failed = results.filter((r) => !r.passed).length
    const rate = results.length > 0 ? ((passed / results.length) * 100).toFixed(0) : '0'

    const rows = results.map((r) => {
      const statusIcon = r.passed ? '&#10003;' : '&#10007;'
      const statusColor = r.passed ? '#22c55e' : '#ef4444'
      return `<tr>
        <td style="color:${statusColor};text-align:center;font-size:18px">${statusIcon}</td>
        <td>${escapeHtml(r.metric)}</td>
        <td style="text-align:right;font-family:monospace">${escapeHtml(String(r.expected))}</td>
        <td style="text-align:right;font-family:monospace">${escapeHtml(String(r.actual))}</td>
        <td style="color:#888">${escapeHtml(r.details || '-')}</td>
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
<h1>Verification Report${ticker ? ' — ' + escapeHtml(ticker) : ''}</h1>
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

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
        {/* Global Configuration */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5 text-primary" />
              Extraction Configuration
            </CardTitle>
            <CardDescription>
              Set the active ticker and extraction parameters for all verification actions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-end gap-6">
              <Field className="w-[200px]">
                <FieldLabel>Active Ticker</FieldLabel>
                <Input
                  placeholder="e.g. BHP"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="font-mono"
                />
              </Field>
              <Field className="w-[200px]">
                <FieldLabel>Method / Provider</FieldLabel>
                <Select value={extractionMethod} onValueChange={(value) => setExtractionMethod(value as ExtractionMethod)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EXTRACTION_METHOD_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field className="w-[160px]">
                <FieldLabel>Strict Mode</FieldLabel>
                <div className="flex h-10 items-center gap-3 rounded-md border border-input bg-background px-3">
                  <Switch checked={strictMethod} onCheckedChange={setStrictMethod} />
                  <span className="text-sm text-muted-foreground whitespace-nowrap">No fallback</span>
                </div>
              </Field>
              
              <div className="flex-1" />
              
              <div className="flex flex-wrap gap-2 pt-2 md:pt-0">
                <Badge variant="outline" className="h-7 border-primary/30 font-mono">
                  {ticker ? `Target: ${ticker}` : 'Broad Mode'}
                </Badge>
                <Badge variant="outline" className="h-7 border-primary/30">
                  {extractionMethod}
                </Badge>
                <Badge variant="outline" className={cn("h-7", strictMethod ? "border-orange-500/50 text-orange-500" : "border-primary/30")}>
                  {strictMethod ? 'Strict' : 'Auto-fallback'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle2 className="h-5 w-5 text-primary" />
              Data Verification
            </CardTitle>
            <CardDescription>
              Read extraction failures and low-confidence financial rows from the backend state.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex gap-2">
                <Button onClick={() => handleRunVerification(true)} disabled={isRunning}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Broad Verification
                </Button>
                <Button variant="outline" onClick={() => handleRunVerification(false)} disabled={isRunning || !ticker.trim()}>
                  <Play className="mr-2 h-4 w-4" />
                  Verify Ticker
                </Button>
              </div>
            </div>

            {isRunning && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Running verification checks...
              </div>
            )}

            {error && (
              <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}
          </CardContent>
        </Card>

        {attachActiveRuns && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Activity className="h-5 w-5 text-primary" />
                Live Extraction Monitor
              </CardTitle>
              <CardDescription>
                Attached to the extraction run currently reported by the backend.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeMonitorNotice && (
                <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
                  {activeMonitorNotice}
                </div>
              )}

              {selectedRunStatuses.length > 0 ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  {selectedRunStatuses.map(({ documentId, runId, status }) => {
                    if (!runId) return null
                    return (
                      <ExtractionRunStatusCard
                        key={runId}
                        documentId={documentId}
                        runId={runId}
                        status={status}
                        title={attachedRunMetadataByDocumentId[documentId]?.title || documentId}
                        fallbackMethod={
                          attachedRunMetadataByDocumentId[documentId]?.requestedMethod || extractionMethod
                        }
                      />
                    )
                  })}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
                  Waiting for backend run metadata...
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {results && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-lg">Verification Results</CardTitle>
                  <CardDescription>
                    {passedCount} of {totalCount} checks passed
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleExportJson}>
                    <FileJson className="mr-2 h-4 w-4" />
                    Export JSON
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleExportHtml}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export HTML
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-6 grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-muted/50 p-4 text-center">
                  <p className="font-mono text-3xl font-semibold text-[oklch(0.65_0.2_145)]">{passedCount}</p>
                  <p className="text-xs text-muted-foreground">Passed</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-4 text-center">
                  <p className="font-mono text-3xl font-semibold text-[oklch(0.55_0.2_25)]">{totalCount - passedCount}</p>
                  <p className="text-xs text-muted-foreground">Failed</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-4 text-center">
                  <p className="text-3xl font-semibold text-primary">{passRate.toFixed(0)}%</p>
                  <p className="text-xs text-muted-foreground">Pass Rate</p>
                </div>
              </div>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40px]">Status</TableHead>
                    <TableHead>Metric</TableHead>
                    <TableHead className="text-right">Expected</TableHead>
                    <TableHead className="text-right">Actual</TableHead>
                    <TableHead>Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((result, i) => (
                    <TableRow key={`${result.metric}-${i}`}>
                      <TableCell>
                        {result.passed ? (
                          <CheckCircle2 className="h-4 w-4 text-[oklch(0.65_0.2_145)]" />
                        ) : (
                          <XCircle className="h-4 w-4 text-[oklch(0.55_0.2_25)]" />
                        )}
                      </TableCell>
                      <TableCell className="font-medium">{result.metric}</TableCell>
                      <TableCell className="text-right font-mono text-sm">{formatValue(result.expected)}</TableCell>
                      <TableCell className="text-right font-mono text-sm">{formatValue(result.actual)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{result.details || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Play className="h-5 w-5 text-primary" />
              Real Gold Set Evaluation
            </CardTitle>
            <CardDescription>
              Runs the current extraction pipeline against the real gold corpus in <code>financial-engine_v2/data/extraction_gold_real</code>.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-end gap-4">
              <Field className="w-[180px]">
                <FieldLabel>Doc limit</FieldLabel>
                <Input
                  value={goldLimit}
                  onChange={(e) => setGoldLimit(e.target.value)}
                  placeholder="0 = full corpus"
                  className="font-mono"
                />
              </Field>
              <div className="flex gap-2">
                <Button onClick={handleRunGoldEval} disabled={goldEvalLoading}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Gold Set
                </Button>
                <Button variant="outline" onClick={handleExportGoldEvalJson} disabled={!goldEval}>
                  <FileJson className="mr-2 h-4 w-4" />
                  Export Gold Eval
                </Button>
              </div>
            </div>

            {goldEvalLoading && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Running the current extraction pipeline across the gold set...
              </div>
            )}

            {goldEvalError && (
              <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {goldEvalError}
              </div>
            )}

            {goldSummary && goldEval && (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="rounded-lg bg-muted/50 p-4 text-center">
                    <p className="text-3xl font-semibold text-primary">{goldSummary.total_documents}</p>
                    <p className="text-xs text-muted-foreground">Documents</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-4 text-center">
                    <p className="text-3xl font-semibold text-primary">{(goldSummary.total_accuracy * 100).toFixed(1)}%</p>
                    <p className="text-xs text-muted-foreground">Metric Accuracy</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-4 text-center">
                    <p className="text-3xl font-semibold text-primary">{(goldSummary.context_accuracy * 100).toFixed(1)}%</p>
                    <p className="text-xs text-muted-foreground">Context Accuracy</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-4 text-center">
                    <p className="text-3xl font-semibold text-primary">{goldSummary.trust_matches_expected}/{goldSummary.total_documents}</p>
                    <p className="text-xs text-muted-foreground">Trust Matches</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">trusted {goldSummary.trust_distribution.trusted ?? 0}</Badge>
                  <Badge variant="outline">abstain {goldSummary.trust_distribution.abstain ?? 0}</Badge>
                  <Badge variant="outline">quarantine {goldSummary.trust_distribution.quarantine ?? 0}</Badge>
                  <Badge variant="outline">method {formatMethodLabel(goldEval.requested_method || extractionMethod)}</Badge>
                  <Badge variant="outline">strict {goldEval.strict_method ? 'yes' : 'no'}</Badge>
                  <Badge variant="outline">dataset {goldEval.dataset_dir}</Badge>
                </div>

                <div className="rounded-lg border border-border/60">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Document</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Trust</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>Metric statuses</TableHead>
                        <TableHead>Mismatch reasons</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {goldEval.documents.map((doc) => {
                        const metricStatuses = Object.entries(doc.metric_results)
                          .map(([metric, result]) => `${metric}:${result.status}`)
                          .join(', ')
                        return (
                          <TableRow key={doc.document_id}>
                            <TableCell className="font-mono text-xs">{doc.document_id}</TableCell>
                            <TableCell>
                              <Badge variant={isReviewableExtractionStatus(doc.extraction_status) ? 'default' : 'critical'}>
                                {doc.extraction_status}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={doc.trust_outcome === 'trusted' ? 'default' : doc.trust_outcome === 'quarantine' ? 'critical' : 'secondary'}>
                                {doc.trust_outcome} / {doc.expected_trust}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {formatMethodLabel(doc.method_provenance?.actual_method || doc.method_provenance?.requested_method)}
                              <div>{doc.method_provenance?.strict_method ? 'strict' : 'auto'}</div>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">{metricStatuses || '-'}</TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {doc.mismatch_reasons.length > 0 ? doc.mismatch_reasons.join('; ') : '-'}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Search className="h-5 w-5 text-primary" />
              Manual Extraction Review
            </CardTitle>
            <CardDescription>
              Review selected corpus PDFs with the latest extraction logic. Loading a review session now re-runs extraction first so you do not inspect stale metrics.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 md:grid-cols-[120px_1fr_auto]">
              <Field>
                <FieldLabel>Docs limit</FieldLabel>
                <Input value={docsLimit} onChange={(e) => setDocsLimit(e.target.value)} className="font-mono" />
              </Field>
              <Field>
                <FieldLabel>Extra document IDs</FieldLabel>
                <Input
                  value={extraDocumentIds}
                  onChange={(e) => setExtraDocumentIds(e.target.value)}
                  placeholder="Comma or space separated document IDs"
                  className="font-mono"
                />
              </Field>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={handleLoadDocuments} disabled={documentsLoading || reviewActionLoading}>
                <Search className="mr-2 h-4 w-4" />
                Load Docs
              </Button>
              <Button variant="outline" onClick={handleRunExtraction} disabled={reviewActionLoading}>
                <Play className="mr-2 h-4 w-4" />
                Run Extraction
              </Button>
              <Button onClick={handleLoadReview} disabled={reviewActionLoading}>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Run Latest + Load Review
              </Button>
              <Button variant="outline" onClick={() => void loadWrongQueue()} disabled={reviewActionLoading}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh Wrong Queue
              </Button>
              <Button variant="outline" onClick={handleExportReviewArtifacts} disabled={!reviewSession && !wrongQueue}>
                <FileJson className="mr-2 h-4 w-4" />
                Export Review Artifacts
              </Button>
            </div>

            <div className="grid gap-4 rounded-lg border border-border/60 bg-muted/10 p-4 md:grid-cols-[220px_1fr_auto_auto]">
              <Field>
                <FieldLabel>Recent runs</FieldLabel>
                <Select value={selectedRunId || undefined} onValueChange={setSelectedRunId}>
                  <SelectTrigger>
                    <SelectValue placeholder={recentRunsLoading ? 'Loading runs...' : 'Select a past run'} />
                  </SelectTrigger>
                  <SelectContent>
                    {recentRuns.map((run) => (
                      <SelectItem key={run.run_id} value={run.run_id}>
                        {`${run.created_at.slice(0, 19)} | ${run.status} | ${run.metrics_count ?? 0} metrics`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {recentRuns.length === 0 ? (
                  <span>No historical runs loaded for this ticker yet.</span>
                ) : recentRuns.slice(0, 4).map((run) => (
                  <Badge key={run.run_id} variant="outline">
                    {run.status} {run.metrics_count ?? 0}m {formatMethodLabel(run.actual_method || run.requested_method)}
                  </Badge>
                ))}
              </div>
              <Button variant="outline" onClick={handleLoadRecentRuns} disabled={recentRunsLoading || reviewActionLoading}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh Runs
              </Button>
              <Button variant="outline" onClick={handleInspectSelectedRun} disabled={!selectedRunId || reviewActionLoading}>
                <BarChart3 className="mr-2 h-4 w-4" />
                Inspect Selected Run
              </Button>
            </div>

            {reviewError && (
              <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {reviewError}
              </div>
            )}

            {reviewActionLoading && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                {reviewSessionLoadingMessage || (currentReviewItem ? 'Saving review verdict...' : 'Processing manual review action...')}
              </div>
            )}

            <div className="rounded-lg border border-border/60">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[120px]">Published</TableHead>
                    <TableHead className="w-[160px]">Document</TableHead>
                    <TableHead className="w-[120px]">Class</TableHead>
                    <TableHead>Title</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="py-6 text-center text-sm text-muted-foreground">
                        Load docs for a ticker to start a review set.
                      </TableCell>
                    </TableRow>
                  ) : documents.map((doc) => {
                    const isSelected = selectedDocumentId === doc.document_id
                    return (
                      <TableRow
                        key={doc.document_id}
                        className={isSelected ? 'bg-primary/5' : undefined}
                        onClick={() => setSelectedDocumentId(doc.document_id)}
                      >
                        <TableCell className="font-mono text-xs">{doc.published_at?.slice(0, 10) || '-'}</TableCell>
                        <TableCell className="font-mono text-xs">{doc.document_id.slice(0, 12)}</TableCell>
                        <TableCell className="text-xs">{doc.doc_class || '-'}</TableCell>
                        <TableCell className="text-sm">{doc.title || 'Untitled document'}</TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Selected review set:</span>
              {selectedReviewDocumentIds.length === 0 ? (
                <Badge variant="outline">none</Badge>
              ) : selectedReviewDocumentIds.map((id) => (
                <Badge key={id} variant="outline" className="font-mono">{id.slice(0, 12)}</Badge>
              ))}
            </div>

            {selectedRunStatuses.length > 0 && !attachActiveRuns && (
              <div className="grid gap-4 lg:grid-cols-2">
                {selectedRunStatuses.map(({ documentId, runId, status }) => {
                  if (!runId) return null
                  const doc = documents.find((entry) => entry.document_id === documentId)
                  return (
                    <ExtractionRunStatusCard
                      key={runId}
                      documentId={documentId}
                      runId={runId}
                      status={status}
                      title={doc?.title || attachedRunMetadataByDocumentId[documentId]?.title || documentId}
                      fallbackMethod={extractionMethod}
                    />
                  )
                })}
              </div>
            )}

            <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
              Use <span className="font-medium text-foreground">Run Latest + Load Review</span> to reprocess the selected PDFs with the current method, or <span className="font-medium text-foreground">Inspect Selected Run</span> to open a historical run without rerunning extraction.
            </div>
          </CardContent>
        </Card>

        {reviewSessionLoadingMessage && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Loading Review Session</CardTitle>
              <CardDescription>
                The previous evidence view has been cleared so snippet images cannot leak across sessions.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                {reviewSessionLoadingMessage}
              </div>
            </CardContent>
          </Card>
        )}

        {reviewSession && !currentReviewItem && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Review Session Status</CardTitle>
              <CardDescription>
                The selected document set loaded, but there are no review items to show yet.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">total {reviewSession.summary?.total ?? 0}</Badge>
                <Badge variant="outline">pending {reviewSession.summary?.pending ?? 0}</Badge>
                <Badge variant="outline">missing docs {reviewSession.missing_document_ids?.length ?? 0}</Badge>
                <Badge variant="outline">missing runs {reviewSession.missing_run_ids?.length ?? 0}</Badge>
              </div>
              <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                {summarizeSessionDocuments(reviewSession)}
              </div>
              {reviewSession.documents && reviewSession.documents.length > 0 && (
                <div className="rounded-lg border border-border/60">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Document</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Reason</TableHead>
                        <TableHead>Metrics</TableHead>
                        <TableHead>Method</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reviewSession.documents.map((doc) => (
                        <TableRow key={`${doc.document_id}-${doc.run_id || 'none'}`}>
                          <TableCell className="text-sm">{doc.title || doc.document_id}</TableCell>
                          <TableCell><Badge variant={doc.review_ready ? 'default' : 'outline'}>{doc.status || 'unknown'}</Badge></TableCell>
                          <TableCell className="text-xs text-muted-foreground">{doc.reason || '-'}</TableCell>
                          <TableCell className="font-mono text-xs">{doc.metrics_count ?? 0}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{formatMethodLabel(doc.actual_method || doc.requested_method)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={handleRunExtraction} disabled={reviewActionLoading}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Extraction Again
                </Button>
                <Button onClick={handleLoadReview} disabled={reviewActionLoading}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Retry Load Review
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {activeRunId && (
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-lg">Run Timeline</CardTitle>
                  <CardDescription>
                    Absolute timestamps and stage timings for run <code>{activeRunId}</code>
                  </CardDescription>
                </div>
                {runStatusLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    Loading timeline...
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {runStatus ? (
                <>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <Badge variant="outline">status {runStatus.summary.status}</Badge>
                    <Badge variant="outline">stage {runStatus.summary.stage}</Badge>
                    <Badge variant="outline">elapsed {formatDuration(runStatus.summary.elapsed_ms)}</Badge>
                    <Badge variant="outline">queue wait {formatDuration(runStatus.summary.queue_wait_ms)}</Badge>
                    <Badge variant="outline">warnings {runStatus.summary.warning_codes?.length ?? 0}</Badge>
                    <Badge variant="outline">errors {runStatus.summary.error_codes?.length ?? 0}</Badge>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Queued</p>
                      <p className="mt-1">{formatTimestamp(runStatus.summary.queued_at)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Worker started</p>
                      <p className="mt-1">{formatTimestamp(runStatus.summary.worker_started_at || runStatus.summary.started_at)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Updated</p>
                      <p className="mt-1">{formatTimestamp(runStatus.summary.updated_at)}</p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">Completed</p>
                      <p className="mt-1">{formatTimestamp(runStatus.summary.completed_at)}</p>
                    </div>
                  </div>

                  <div className="rounded-lg border border-border/60">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Stage</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Latest message</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(runStatus.summary.stage_timings_ms || {}).map(([stage, duration]) => (
                          <TableRow key={stage}>
                            <TableCell className="font-mono text-xs">{stage}</TableCell>
                            <TableCell className="font-mono text-xs">{formatDuration(duration)}</TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {[...runStatus.events].reverse().find((event) => event.stage === stage)?.message || '-'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {((runStatus.summary.warnings?.length ?? 0) > 0 || (runStatus.summary.errors?.length ?? 0) > 0) && (
                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                        <p className="mb-2 text-sm font-medium">Warnings</p>
                        <div className="space-y-2 text-xs text-muted-foreground">
                          {(runStatus.summary.warnings || []).map((warning) => (
                            <div key={`${warning.stage}-${warning.code}`} className="rounded-md border border-dashed border-border/60 p-2">
                              <div className="font-mono text-foreground">{warning.code}</div>
                              <div>{warning.message}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                        <p className="mb-2 text-sm font-medium">Errors</p>
                        <div className="space-y-2 text-xs text-muted-foreground">
                          {(runStatus.summary.errors || []).map((issue) => (
                            <div key={`${issue.stage}-${issue.code}`} className="rounded-md border border-dashed border-border/60 p-2">
                              <div className="font-mono text-foreground">{issue.code}</div>
                              <div>{issue.message}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    {runStatus.events.map((event, index) => (
                      <details key={`${event.stage}-${event.timestamp}-${index}`} className="rounded-lg border border-border/60 bg-muted/10 p-3">
                        <summary className="cursor-pointer list-none text-sm">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="outline">{event.stage}</Badge>
                            <Badge variant={event.status === 'failed' || event.status === 'blocked' ? 'critical' : event.status === 'succeeded' ? 'default' : 'outline'}>
                              {event.status}
                            </Badge>
                            <span className="text-muted-foreground">{formatTimestamp(event.timestamp)}</span>
                            <span>{event.message}</span>
                          </div>
                        </summary>
                        <pre className="mt-3 overflow-x-auto rounded-md bg-black/20 p-3 text-xs leading-5 text-muted-foreground">
                          {JSON.stringify(event.details || {}, null, 2)}
                        </pre>
                      </details>
                    ))}
                  </div>
                </>
              ) : (
                <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                  Run timeline data is not available for this run yet.
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {reviewSession && currentReviewItem && (
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-lg">Review {currentReviewIndex + 1} of {reviewItems.length}</CardTitle>
                  <CardDescription>
                    Session {reviewSession.session_id}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">pending {reviewSession.summary?.pending ?? 0}</Badge>
                  <Badge variant="default">correct {reviewSession.summary?.approved ?? 0}</Badge>
                  <Badge variant="critical">wrong {reviewSession.summary?.wrong ?? 0}</Badge>
                  <Badge variant="secondary">unsure {reviewSession.summary?.abstain ?? 0}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
                <div className="space-y-4">
                  <div className="rounded-lg border border-border/60">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-4 py-3">
                      <div>
                        <p className="text-sm font-medium">Extracted metrics</p>
                        <p className="text-xs text-muted-foreground">Click a metric to inspect its PDF evidence. Use ←/→ to move and C/W/U to record a verdict.</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => moveReviewSelection('prev')}
                          disabled={!hasPrevReviewItem}
                        >
                          Prev
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => moveReviewSelection('next')}
                          disabled={!hasNextReviewItem}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                    <div className="max-h-[720px] overflow-y-auto p-2">
                        {reviewItems.map((item) => {
                          const isActive = item.item_id === currentReviewItem.item_id
                          const itemEvidenceQuality = evidenceQualityForItem(item)
                          return (
                            <button
                            key={item.item_id}
                            type="button"
                            onClick={() => setSelectedReviewItemId(item.item_id)}
                            className={`flex w-full flex-col gap-2 rounded-md border px-3 py-3 text-left transition ${isActive ? 'border-primary bg-primary/5' : 'border-transparent hover:border-border/60 hover:bg-muted/20'}`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="text-sm font-medium">{item.metric_name}</p>
                                <p className="font-mono text-sm text-foreground">{String(item.metric_value ?? item.extracted_value ?? '-')}</p>
                              </div>
                              <div className="flex flex-col items-end gap-2">
                                <Badge variant={evidenceQualityBadgeVariant(itemEvidenceQuality)}>{evidenceQualityLabel(itemEvidenceQuality)}</Badge>
                                <Badge variant={statusVariant(item.review_status)}>{reviewStatusLabel(item.review_status)}</Badge>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                              <span>{evidenceMethodLabel(item)}</span>
                              <span>page {item.page_number ?? '?'}</span>
                              {item.table_type && <span>{item.table_type}</span>}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </div>

                <div key={currentEvidenceKey || reviewSession.session_id} className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={statusVariant(currentReviewItem.review_status)}>{reviewStatusLabel(currentReviewItem.review_status)}</Badge>
                    <Badge variant="outline">{currentReviewItem.metric_name}</Badge>
                    <Badge variant={evidenceQualityBadgeVariant(currentEvidenceQuality)}>{evidenceQualityLabel(currentEvidenceQuality)}</Badge>
                    <Badge variant="outline">page {currentReviewItem.page_number ?? '?'}</Badge>
                    <Badge variant="outline">method {evidenceMethodLabel(currentReviewItem)}</Badge>
                    <Badge variant="outline">{currentReviewItem.strict_method ? 'strict' : 'auto'}</Badge>
                    {currentReviewItem.snippet.kind && <Badge variant="outline">{currentReviewItem.snippet.kind}</Badge>}
                  </div>

                  <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Extracted value</p>
                        <p className="mt-1 font-mono text-lg">{String(currentReviewItem.metric_value ?? currentReviewItem.extracted_value ?? '-')}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Method / provider</p>
                        <p className="mt-1 text-sm">{evidenceMethodLabel(currentReviewItem)}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Period</p>
                        <p className="mt-1 font-mono text-lg">{currentReviewItem.period_type || '?'} {currentReviewItem.period_end || '?'}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Document</p>
                        <p className="mt-1 text-sm">{currentReviewItem.title || currentReviewItem.document_id}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Provenance</p>
                        <p className="mt-1 text-sm">{currentReviewItem.evidence_summary || currentReviewItem.evidence_reference || 'No provenance summary'}</p>
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Method provenance</p>
                        <p className="mt-1 text-sm">
                          actual={formatMethodLabel(currentReviewItem.actual_method)} parser={currentReviewItem.parser_id || '-'} fallback={currentReviewItem.fallback_used ? 'yes' : 'no'}
                        </p>
                      </div>
                      {currentReviewItem.model_id || currentReviewItem.runtime_id ? (
                        <div>
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Model / runtime</p>
                          <p className="mt-1 text-sm">{currentReviewItem.model_id || '-'} @ {currentReviewItem.runtime_id || '-'}</p>
                        </div>
                      ) : null}
                      {currentReviewItem.period_col ? (
                        <div>
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Period column</p>
                          <p className="mt-1 text-sm">{currentReviewItem.period_col}</p>
                        </div>
                      ) : null}
                      {currentRowRef ? (
                        <div>
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Row reference</p>
                          <p className="mt-1 text-sm">{currentRowRef}</p>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {currentReviewItem.method_warnings && currentReviewItem.method_warnings.length > 0 && (
                    <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
                      Warnings: {currentReviewItem.method_warnings.join('; ')}
                    </div>
                  )}

                  <div className="space-y-3 rounded-lg border border-border/60 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <FileImage className="h-4 w-4 text-primary" />
                      Evidence Snippet
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs">
                      <Badge variant={evidenceQualityBadgeVariant(currentEvidenceQuality)}>{evidenceQualityHeadline(currentEvidenceQuality)}</Badge>
                      <Badge variant="outline">snippet {currentReviewItem.snippet.status}</Badge>
                      <Badge variant="outline">provenance {currentReviewItem.provenance_status || 'unknown'}</Badge>
                      {currentReviewItem.error_stage && <Badge variant="outline">error {currentReviewItem.error_stage}</Badge>}
                      {currentReviewItem.source_label && <Badge variant="outline">source {currentReviewItem.source_label}</Badge>}
                    </div>

                    <div className="rounded-md border border-border/60 bg-muted/20 p-3 text-sm">
                      <p className="font-medium">{evidenceQualityHeadline(currentEvidenceQuality)}</p>
                      <p className="mt-1 text-muted-foreground">{evidenceQualityBody(currentEvidenceQuality)}</p>
                    </div>

                    {evidenceSuspendMessage ? (
                      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                        {evidenceSuspendMessage}
                      </div>
                    ) : currentSnippetUrl ? (
                      <div className="space-y-3">
                        {currentEvidenceQuality === 'approximate' && (
                          <div className="grid gap-3 rounded-md border border-border/60 bg-muted/20 p-3 text-sm md:grid-cols-3">
                            <div>
                              <p className="text-xs uppercase tracking-wide text-muted-foreground">Page</p>
                              <p className="mt-1">{currentReviewItem.page_number ?? '?'}</p>
                            </div>
                            <div>
                              <p className="text-xs uppercase tracking-wide text-muted-foreground">Table type</p>
                              <p className="mt-1">{currentReviewItem.table_type || currentReviewItem.source_label || '-'}</p>
                            </div>
                            <div>
                              <p className="text-xs uppercase tracking-wide text-muted-foreground">Method / provider</p>
                              <p className="mt-1">{evidenceMethodLabel(currentReviewItem)}</p>
                            </div>
                          </div>
                        )}
                        <div className="relative overflow-hidden rounded-md border border-border/60 bg-black/20">
                          <Image
                            key={currentSnippetRenderKey}
                            src={currentSnippetUrl}
                            alt={`Snippet for ${currentReviewItem.metric_name}`}
                            width={900}
                            height={520}
                            unoptimized
                            onLoad={handleSnippetImageLoad}
                            onError={handleSnippetImageError}
                            className={`max-h-[360px] w-full object-contain transition-opacity ${snippetImageState.status === 'ready' ? 'opacity-100' : 'opacity-0'}`}
                          />
                          {snippetImageState.status !== 'ready' && (
                            <div className="absolute inset-0 flex items-center justify-center bg-background/85 px-6 text-center text-sm text-muted-foreground">
                              <div className="space-y-3">
                                {(snippetImageState.status === 'loading' || snippetImageState.status === 'retrying') && (
                                  <div className="mx-auto h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                                )}
                                <p>
                                  {snippetImageState.message
                                    || (snippetImageState.status === 'retrying'
                                      ? 'Refreshing snippet evidence...'
                                      : 'Loading snippet evidence...')}
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{currentSnippetPath}</p>
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                        {currentReviewItem.snippet.reason || evidenceQualityHeadline(currentEvidenceQuality)}
                      </div>
                    )}

                    {snippetImageState.status === 'failed' && currentSnippetUrl && !evidenceSuspendMessage && (
                      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                        {snippetImageState.message || currentReviewItem.snippet.reason || evidenceQualityBody(currentEvidenceQuality)}
                      </div>
                    )}

                    {matchedEvidenceText && !evidenceSuspendMessage && (
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                          {currentEvidenceQuality === 'precise' ? 'Matched source line' : 'Preserved evidence text'}
                        </p>
                        <pre className="whitespace-pre-wrap rounded-md bg-muted/20 p-3 text-xs leading-5 text-foreground">
                          {matchedEvidenceText}
                        </pre>
                      </div>
                    )}

                    {!matchedEvidenceText && !evidenceSuspendMessage && (
                      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                        {currentEvidenceQuality === 'approximate'
                          ? 'Exact matched text was not preserved for this metric. Review the source preview image above for manual verification.'
                          : 'No matched text or usable visual evidence is available for this metric.'}
                      </div>
                    )}

                    {currentReviewItem.evidence_reference && !evidenceSuspendMessage && (
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Evidence reference</p>
                        <pre className="whitespace-pre-wrap rounded-md bg-muted/20 p-3 text-xs leading-5 text-muted-foreground">
                          {currentReviewItem.evidence_reference}
                        </pre>
                      </div>
                    )}

                    {currentReviewItem.snippet.ascii_preview && !evidenceSuspendMessage && (
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">ASCII preview</p>
                        <pre className="overflow-x-auto rounded-md bg-black/30 p-3 font-mono text-[10px] leading-3 text-muted-foreground">
                          {currentReviewItem.snippet.ascii_preview}
                        </pre>
                      </div>
                    )}
                    <div className="rounded-lg border border-border/60 p-4">
                      <p className="mb-3 text-sm font-medium">Verdict</p>
                      <div className="flex flex-wrap gap-2">
                        <Button onClick={() => void handleSubmitReview('correct')} disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}>
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Correct
                        </Button>
                        <Button variant="destructive" onClick={() => void handleSubmitReview('wrong')} disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}>
                          <XCircle className="mr-2 h-4 w-4" />
                          Wrong
                        </Button>
                        <Button variant="secondary" onClick={() => void handleSubmitReview('unsure')} disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}>
                          Unsure
                        </Button>
                      </div>
                    </div>

                    <div className="rounded-lg border border-border/60 bg-muted/20 p-4 text-xs text-muted-foreground">
                      Keyboard shortcuts: <span className="font-mono">C</span> correct, <span className="font-mono">W</span> wrong, <span className="font-mono">U</span> unsure.
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle className="text-lg">Extraction Wrong Queue</CardTitle>
                <CardDescription>
                  Structured failures collected for later extractor hardening.
                </CardDescription>
              </div>
              <Badge variant="outline">{wrongQueue?.count ?? 0} items</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {!wrongQueue || wrongQueue.items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-6 text-sm text-muted-foreground">
                No wrong-marked extraction items yet.
              </div>
            ) : (
              <div className="space-y-4">
                {wrongQueue.items.slice(0, 20).map((item) => (
                  <div key={item.item_id} className="rounded-lg border border-border/60 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="critical">wrong</Badge>
                      <Badge variant="outline">{item.ticker || 'UNK'}</Badge>
                      <Badge variant="outline">{item.metric_name}</Badge>
                      <Badge variant="outline">page {item.page_number ?? '?'}</Badge>
                    </div>
                    <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                      <p><span className="text-muted-foreground">Extracted:</span> <span className="font-mono">{String(item.extracted_value ?? '-')}</span></p>
                      <p><span className="text-muted-foreground">Expected:</span> <span className="font-mono">{String(item.expected_value ?? '-')}</span></p>
                      <p className="md:col-span-2"><span className="text-muted-foreground">Doc:</span> {item.document_id}</p>
                      <p className="md:col-span-2"><span className="text-muted-foreground">Evidence:</span> {item.evidence_summary || item.evidence_reference || 'No evidence summary'}</p>
                      {item.reviewer_note && <p className="md:col-span-2"><span className="text-muted-foreground">Note:</span> {item.reviewer_note}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <BarChart3 className="h-5 w-5 text-primary" />
              Visualization
            </CardTitle>
            <CardDescription>
              Interactive charts for verified data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-muted/20">
              <div className="text-center text-muted-foreground">
                <BarChart3 className="mx-auto mb-3 h-12 w-12 opacity-50" />
                <p className="text-sm">Plotly chart would render here</p>
                <p className="mt-1 text-xs">Candlestick, snapshot, or comparison charts</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Separator />
      </div>
    </ScrollArea>
  )
}
