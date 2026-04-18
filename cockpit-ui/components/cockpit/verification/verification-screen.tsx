'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'

import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent } from '@/components/ui/tabs'
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
import type {
  ContextDocument,
  ExtractionReviewErrorQueue,
  ExtractionReviewRunStatusResponse,
  ExtractionReviewRunSummary,
  ExtractionReviewSession,
  VerificationResult,
} from '@/lib/cockpit-types'

import { ACTIVE_RUNS_STORAGE_KEY } from './constants'
import { GoldEvalTabPanel } from './tabs/gold-eval-tab-panel'
import { ReviewTabPanel } from './tabs/review-tab-panel'
import { RunsTabPanel } from './tabs/runs-tab-panel'
import { VerifyTabPanel } from './tabs/verify-tab-panel'
import { VerificationSidebar } from './verification-sidebar'
import type { ActiveExtractionMonitorRun, ProcessDocumentResponse, RealGoldEvalResponse, VerificationTab } from './types'
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

export function VerificationScreen() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { activeTicker } = useCockpitStore()

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

  const handleLoadDocuments = useCallback(async () => {
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
  }, [docsLimit, ticker])

  const handleLoadRecentRuns = useCallback(async (filterTicker?: string) => {
    if (recentRunsLoadLockRef.current) return
    
    // If no ticker provided, we use the current component state ticker if it exists
    const targetTicker = filterTicker !== undefined ? filterTicker : ticker.trim().toUpperCase()
    
    recentRunsLoadLockRef.current = true
    setRecentRunsLoading(true)
    try {
      // Fetch recent runs (optional ticker filter)
      const payload = await getExtractionReviewRuns(targetTicker, 50)
      setRecentRuns(payload.items)
      
      // If we are filtering by a specific ticker, also update the selected run
      if (targetTicker) {
        setSelectedRunId((current) => 
          payload.items.some((run) => run.run_id === current) ? current : (payload.items[0]?.run_id || '')
        )
      }
    } catch (err: unknown) {
      console.error('Failed to load recent runs:', err)
      if (targetTicker) {
        const message = err instanceof Error ? err.message : 'Failed to load recent runs'
        setReviewError(message)
        toast.error(message)
      }
    } finally {
      recentRunsLoadLockRef.current = false
      setRecentRunsLoading(false)
    }
  }, [ticker])

  const handleSelectHistoryTicker = useCallback((historyTicker: string) => {
    setTicker(historyTicker)
    // Switching ticker should trigger a document load for that company
    setTimeout(() => {
      void handleLoadDocuments()
    }, 10)
  }, [handleLoadDocuments])

  const handleSelectHistoryRun = useCallback((runId: string) => {
    setSelectedRunId(runId)
    updateTab('runs')
  }, [updateTab])

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

  const {
    snippetImageState,
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
    onSessionRefresh: (session, itemId) => {
      setReviewSession(session)
      setSelectedReviewItemId((current) => (
        itemId && session.items.some((item) => item.item_id === itemId) ? itemId : current
      ))
    },
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
    const url = queryTicker
      ? `/api/context/verification?ticker=${encodeURIComponent(queryTicker)}`
      : '/api/context/verification'

    try {
      const response = await fetch(url)
      if (!response.ok) {
        const text = await response.text().catch(() => '')
        throw new Error(text || `Verification failed (HTTP ${response.status})`)
      }

      const data: unknown = await response.json()
      setResults(mapResponseToResults(data))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unexpected error during verification'
      setError(message)
    } finally {
      setIsRunning(false)
    }
  }, [ticker])

  const failedChecksCount = useMemo(() => results?.filter((r) => !r.passed).length ?? 0, [results])

  const runSelectedDocumentExtractions = useCallback(async (): Promise<{
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
  }, [extractionMethod, selectedReviewDocumentIds, strictMethod])

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
      const { queuedIds, failedRuns, results: extractionResults, runIdsByDocumentId } = await runSelectedDocumentExtractions()
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
      const methodSummary = extractionResults[0]?.method_provenance
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
  }, [
    activeRunIdsByDocumentId,
    extractionMethod,
    persistActiveRuns,
    refreshRunStatuses,
    runSelectedDocumentExtractions,
    selectedReviewDocumentIds.length,
    strictMethod,
  ])

  const loadWrongQueue = useCallback(async () => {
    try {
      const payload = await getExtractionReviewErrors(200)
      setWrongQueue(payload)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load wrong queue'
      setReviewError(message)
    }
  }, [])

  useEffect(() => {
    // Initial global load for discovery - we pass empty string to ensure global fetch
    void handleLoadRecentRuns('')
    void loadWrongQueue()
  }, [handleLoadRecentRuns, loadWrongQueue])

  const handleInspectSelectedRun = useCallback(async () => {
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
  }, [beginReviewSessionSwap, loadWrongQueue, selectedRunId])

  const handleLoadReview = useCallback(async () => {
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
        setReviewError(`No reviewable extracted metrics were available for the selected document set. ${diagnostic}`)
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
  }, [
    activeRunIdsByDocumentId,
    beginReviewSessionSwap,
    loadWrongQueue,
    persistActiveRuns,
    refreshRunStatuses,
    runSelectedDocumentExtractions,
    selectedReviewDocumentIds.length,
  ])

  const handleInspectResult = useCallback((result: VerificationResult) => {
    updateTab('review')

    if (result.document_id) {
      setSelectedDocumentId(result.document_id)

      // If the document is not in our current review items, we should trigger a load.
      const isDocInSession = reviewSession?.document_ids?.includes(result.document_id)
        || reviewItems.some((item) => item.document_id === result.document_id)

      if (!isDocInSession) {
        setExtraDocumentIds((current) => {
          const existing = parseDocumentIds(current)
          if (existing.includes(result.document_id!)) return current
          return existing.length > 0 ? `${current}, ${result.document_id}` : result.document_id!
        })
        // Delay slightly to allow state to propagate before loading the review session.
        setTimeout(() => {
          void handleLoadReview()
        }, 50)
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
  }, [handleLoadReview, reviewItems, reviewSession, updateTab])

  const handleRunGoldEval = useCallback(async () => {
    setGoldEvalLoading(true)
    setGoldEvalError(null)
    try {
      const parsedLimit = Number.parseInt(goldLimit, 10)
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (BROWSER_API_KEY) {
        headers['X-API-Key'] = BROWSER_API_KEY
      }

      const response = await fetch('/api/extraction-eval/real-gold', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          limit: Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : 0,
          method: extractionMethod,
          strict_method: strictMethod,
        }),
      })

      if (!response.ok) {
        let detail = `Gold set evaluation failed (HTTP ${response.status})`
        try {
          const body = await response.json()
          if (body && typeof body === 'object' && 'detail' in body) {
            detail = String((body as { detail: unknown }).detail)
          }
        } catch {
          const text = await response.text().catch(() => '')
          if (text) detail = text
        }
        throw new Error(detail)
      }

      const data = await response.json() as RealGoldEvalResponse
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
  }, [extractionMethod, goldLimit, strictMethod])

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
      const session = await getExtractionReviewSession(sessionId)
      setReviewSession(session)
      setSelectedRunId(session.run_ids?.[0] || '')
      setSelectedReviewItemId(session.items[0]?.item_id ?? null)
      setReviewSessionLoadingMessage(null)
      updateTab('review')
      await loadWrongQueue()
      toast.success(`Loaded backend review session for ${session.document_ids[0] || 'gold-eval document'}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load backend review session'
      setReviewError(message)
      toast.error(message)
    } finally {
      setReviewSessionLoadingMessage(null)
      reviewActionLockRef.current = false
      setReviewActionLoading(false)
    }
  }, [beginReviewSessionSwap, loadWrongQueue, updateTab])

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
  }, [currentReviewIndex, currentReviewItem, loadWrongQueue, reviewItems, reviewSession])

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
    <div className="flex h-full min-h-0 w-full gap-6 p-6">
      <Tabs value={activeTab} onValueChange={updateTab} className="flex min-w-0 flex-1 flex-col gap-4">
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

        <VerificationTabBar
          wrongQueueCount={wrongQueue?.count ?? 0}
          pendingCount={reviewSession?.summary?.pending ?? 0}
          failedChecksCount={failedChecksCount}
        />

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
                  selectedRunId={selectedRunId}
                  selectedDocumentId={selectedDocumentId}
                  selectedReviewDocumentIds={selectedReviewDocumentIds}
                  currentReviewItem={currentReviewItem}
                  currentReviewIndex={currentReviewIndex}
                  currentEvidenceQuality={currentEvidenceQuality}
                  matchedEvidenceText={matchedEvidenceText}
                  currentSnippetPath={currentSnippetPath}
                  currentSnippetUrl={currentSnippetUrl}
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
              <div className="pr-4">
                <RunsTabPanel
                  attachActiveRuns={attachActiveRuns}
                  activeMonitorNotice={activeMonitorNotice}
                  statusCards={runStatusCards}
                  runStatusLoading={runStatusLoading}
                  activeRunId={activeRunId}
                  runStatus={runStatus}
                />
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

          <TabsContent value="verify" className="m-0 h-full min-h-0 outline-none data-[state=active]:flex">
            <ScrollArea className="h-full w-full">
              <div className="pr-4">
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

      <aside className="w-80 shrink-0 border-l border-border/40 pl-6">
        <VerificationSidebar
          recentRuns={recentRuns}
          loading={recentRunsLoading}
          onSelectTicker={handleSelectHistoryTicker}
          onSelectRun={handleSelectHistoryRun}
          activeTicker={ticker}
        />
      </aside>
    </div>
  )

}
