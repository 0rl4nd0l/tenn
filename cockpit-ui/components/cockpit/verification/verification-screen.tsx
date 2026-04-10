'use client'

import Image from 'next/image'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileImage,
  FileJson,
  FileText,
  Play,
  RefreshCw,
  Search,
  SkipForward,
  XCircle,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import {
  createExtractionReviewSession,
  getExtractionReviewErrors,
  getTickerDocuments,
  processDocument,
  submitExtractionReviewDecision,
} from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import type {
  ContextDocument,
  ExtractionReviewErrorQueue,
  ExtractionReviewItem,
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
}

type RealGoldEvalResponse = {
  dataset_dir: string
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

function summarizeSessionDocuments(session: ExtractionReviewSession | null): string {
  if (!session?.documents || session.documents.length === 0) {
    return 'No review session diagnostics available yet.'
  }
  return session.documents
    .map((doc) => {
      const label = doc.title || doc.document_id
      const status = doc.status || 'unknown'
      const count = typeof doc.items_count === 'number' ? doc.items_count : 0
      return `${label}: ${status}${count > 0 ? ` (${count} item${count === 1 ? '' : 's'})` : ''}`
    })
    .join(' | ')
}

export function VerificationScreen() {
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
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewActionLoading, setReviewActionLoading] = useState(false)
  const [reviewSession, setReviewSession] = useState<ExtractionReviewSession | null>(null)
  const [reviewIndex, setReviewIndex] = useState(0)
  const [expectedValue, setExpectedValue] = useState('')
  const [reviewerNote, setReviewerNote] = useState('')
  const [wrongQueue, setWrongQueue] = useState<ExtractionReviewErrorQueue | null>(null)
  const [goldLimit, setGoldLimit] = useState('10')
  const [goldEvalLoading, setGoldEvalLoading] = useState(false)
  const [goldEvalError, setGoldEvalError] = useState<string | null>(null)
  const [goldEval, setGoldEval] = useState<RealGoldEvalResponse | null>(null)

  useEffect(() => {
    setHasHydrated(true)
  }, [])

  useEffect(() => {
    if (activeTicker) {
      setTicker(activeTicker)
    }
  }, [activeTicker])

  const reviewItems = useMemo(() => reviewSession?.items ?? [], [reviewSession])
  const currentReviewItem = reviewItems[reviewIndex] ?? null
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
    const cleanTicker = ticker.trim().toUpperCase()
    if (!cleanTicker) {
      setReviewError('Ticker is required to load review documents.')
      return
    }

    setReviewError(null)
    setDocumentsLoading(true)
    try {
      const parsedLimit = Number.parseInt(docsLimit, 10)
      const docs = await getTickerDocuments(cleanTicker, Number.isFinite(parsedLimit) ? parsedLimit : 10)
      setDocuments(docs)
      const defaultDoc = docs[0]?.document_id ?? ''
      setSelectedDocumentId((current) => current || defaultDoc)
      toast.success(`Loaded ${docs.length} document(s) for ${cleanTicker}`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load documents'
      setReviewError(message)
      toast.error(message)
    } finally {
      setDocumentsLoading(false)
    }
  }

  const handleRunExtraction = async () => {
    if (selectedReviewDocumentIds.length === 0) {
      setReviewError('Select one document or enter document IDs first.')
      return
    }

    setReviewError(null)
    setReviewActionLoading(true)
    try {
      const queuedIds: string[] = []
      const failedRuns: string[] = []
      for (const documentId of selectedReviewDocumentIds) {
        const result = await processDocument(documentId)
        const mode = String(result.mode ?? '')
        const extractionStatus = String(result.extraction_status ?? '')
        if (mode === 'celery') {
          queuedIds.push(documentId)
          continue
        }
        if (!isReviewableExtractionStatus(extractionStatus)) {
          failedRuns.push(`${documentId.slice(0, 12)}:${extractionStatus || 'unknown'}`)
        }
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
      toast.success(`Extraction requested for ${selectedReviewDocumentIds.length} document(s)`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to run extraction'
      setReviewError(message)
      toast.error(message)
    } finally {
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

  const handleLoadReview = async () => {
    if (selectedReviewDocumentIds.length === 0) {
      setReviewError('Select one document or enter document IDs first.')
      return
    }

    setReviewError(null)
    setReviewActionLoading(true)
    try {
      const queuedIds: string[] = []
      const failedRuns: string[] = []
      for (const documentId of selectedReviewDocumentIds) {
        const result = await processDocument(documentId)
        const mode = String(result.mode ?? '')
        const extractionStatus = String(result.extraction_status ?? '')
        if (mode === 'celery') {
          queuedIds.push(documentId)
          continue
        }
        if (!isReviewableExtractionStatus(extractionStatus)) {
          failedRuns.push(`${documentId.slice(0, 12)}:${extractionStatus || 'unknown'}`)
        }
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

      const session = await createExtractionReviewSession(selectedReviewDocumentIds)

      setReviewSession(session)
      setReviewIndex(0)
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
      toast.success(`Gold set evaluation finished for ${data.summary.total_documents} document(s)`)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to run gold set evaluation'
      setGoldEvalError(message)
      toast.error(message)
    } finally {
      setGoldEvalLoading(false)
    }
  }

  const handleSubmitReview = useCallback(async (status: 'approved' | 'wrong' | 'abstain') => {
    if (!reviewSession || !currentReviewItem) return

    setReviewError(null)
    setReviewActionLoading(true)
    try {
      const result = await submitExtractionReviewDecision({
        sessionId: reviewSession.session_id,
        itemId: currentReviewItem.item_id,
        status,
        expectedValue: expectedValue.trim() || null,
        reviewerNote: reviewerNote.trim() || null,
      })

      const nextItems = [...reviewItems]
      nextItems[reviewIndex] = result.item
      const nextSession: ExtractionReviewSession = {
        ...reviewSession,
        items: nextItems,
        summary: result.summary,
      }
      setReviewSession(nextSession)
      await loadWrongQueue()
      toast.success(`${currentReviewItem.metric_name} marked ${status}`)
      if (reviewIndex < nextItems.length - 1) {
        setReviewIndex(reviewIndex + 1)
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save review decision'
      setReviewError(message)
      toast.error(message)
    } finally {
      setReviewActionLoading(false)
    }
  }, [currentReviewItem, expectedValue, reviewerNote, reviewIndex, reviewItems, reviewSession])

  useEffect(() => {
    if (!currentReviewItem) return
    setExpectedValue(currentReviewItem.expected_value == null ? '' : String(currentReviewItem.expected_value))
    setReviewerNote(currentReviewItem.reviewer_note ?? '')
  }, [currentReviewItem])

  useEffect(() => {
    if (!currentReviewItem) return

    const onKeyDown = (event: KeyboardEvent) => {
      const tagName = (event.target as HTMLElement | null)?.tagName?.toLowerCase()
      if (tagName === 'input' || tagName === 'textarea') return
      if (reviewActionLoading) return

      if (event.key === 'a' || event.key === 'A') {
        event.preventDefault()
        void handleSubmitReview('approved')
      } else if (event.key === 'w' || event.key === 'W') {
        event.preventDefault()
        void handleSubmitReview('wrong')
      } else if (event.key === 'u' || event.key === 'U') {
        event.preventDefault()
        void handleSubmitReview('abstain')
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault()
        setReviewIndex((value) => Math.max(0, value - 1))
      } else if (event.key === 'ArrowRight') {
        event.preventDefault()
        setReviewIndex((value) => Math.min(reviewItems.length - 1, value + 1))
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [currentReviewItem, handleSubmitReview, reviewActionLoading, reviewItems.length])

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
              <Field className="w-[220px]">
                <FieldLabel>Ticker (optional)</FieldLabel>
                <Input
                  placeholder="Leave empty for broad check"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="font-mono"
                />
              </Field>

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
                  <Badge variant="outline">dataset {goldEval.dataset_dir}</Badge>
                </div>

                <div className="rounded-lg border border-border/60">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Document</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Trust</TableHead>
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
            <div className="grid gap-4 md:grid-cols-[220px_120px_1fr]">
              <Field>
                <FieldLabel>Ticker</FieldLabel>
                <Input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} className="font-mono" />
              </Field>
              <Field>
                <FieldLabel>Docs</FieldLabel>
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

            {reviewError && (
              <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {reviewError}
              </div>
            )}

            {reviewActionLoading && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Processing manual review action...
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

            <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
              The review loader always reprocesses the selected PDFs first. If the latest extraction fails or queues in Celery mode, the screen stops instead of silently showing an older successful run.
            </div>
          </CardContent>
        </Card>

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
              </div>
              <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                {summarizeSessionDocuments(reviewSession)}
              </div>
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

        {reviewSession && currentReviewItem && (
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-lg">Review {reviewIndex + 1} of {reviewItems.length}</CardTitle>
                  <CardDescription>
                    Session {reviewSession.session_id}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">pending {reviewSession.summary?.pending ?? 0}</Badge>
                  <Badge variant="default">approved {reviewSession.summary?.approved ?? 0}</Badge>
                  <Badge variant="critical">wrong {reviewSession.summary?.wrong ?? 0}</Badge>
                  <Badge variant="secondary">skip {reviewSession.summary?.abstain ?? 0}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={statusVariant(currentReviewItem.review_status)}>{currentReviewItem.review_status}</Badge>
                    <Badge variant="outline">{currentReviewItem.metric_name}</Badge>
                    <Badge variant="outline">page {currentReviewItem.page_number ?? '?'}</Badge>
                    {currentReviewItem.snippet.kind && <Badge variant="outline">{currentReviewItem.snippet.kind}</Badge>}
                  </div>

                  <div className="rounded-lg border border-border/60 bg-muted/20 p-4">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Extracted value</p>
                        <p className="mt-1 font-mono text-lg">{String(currentReviewItem.extracted_value ?? '-')}</p>
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
                    </div>
                  </div>

                  <div className="space-y-3 rounded-lg border border-border/60 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <FileImage className="h-4 w-4 text-primary" />
                      Evidence Snippet
                    </div>

                    {currentReviewItem.snippet.image_url ? (
                      <div className="space-y-3">
                        <Image
                          src={currentReviewItem.snippet.image_url}
                          alt={`Snippet for ${currentReviewItem.metric_name}`}
                          width={900}
                          height={520}
                          unoptimized
                          className="max-h-[360px] w-full rounded-md border border-border/60 bg-black/20 object-contain"
                        />
                        <p className="text-xs text-muted-foreground">{currentReviewItem.snippet.image_path}</p>
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                        {currentReviewItem.snippet.reason || 'Image snippet unavailable. Falling back to text evidence.'}
                      </div>
                    )}

                    {(currentReviewItem.snippet.matched_text || currentReviewItem.evidence_text) && (
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Matched text</p>
                        <pre className="whitespace-pre-wrap rounded-md bg-muted/20 p-3 text-xs leading-5 text-foreground">
                          {currentReviewItem.snippet.matched_text || currentReviewItem.evidence_text}
                        </pre>
                      </div>
                    )}

                    {currentReviewItem.snippet.ascii_preview && (
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">ASCII preview</p>
                        <pre className="overflow-x-auto rounded-md bg-black/30 p-3 font-mono text-[10px] leading-3 text-muted-foreground">
                          {currentReviewItem.snippet.ascii_preview}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-lg border border-border/60 p-4">
                    <p className="mb-3 text-sm font-medium">Review decision</p>
                    <div className="space-y-3">
                      <Field>
                        <FieldLabel>Correct / expected value</FieldLabel>
                        <Input value={expectedValue} onChange={(e) => setExpectedValue(e.target.value)} placeholder="Optional corrected value" className="font-mono" />
                      </Field>
                      <Field>
                        <FieldLabel>Reviewer note</FieldLabel>
                        <Textarea value={reviewerNote} onChange={(e) => setReviewerNote(e.target.value)} placeholder="Why is this wrong or uncertain?" className="min-h-[120px]" />
                      </Field>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={() => setReviewIndex((value) => Math.max(0, value - 1))} disabled={reviewIndex === 0 || reviewActionLoading}>
                      <ChevronLeft className="mr-2 h-4 w-4" />
                      Prev
                    </Button>
                    <Button onClick={() => void handleSubmitReview('approved')} disabled={reviewActionLoading}>
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Approve
                    </Button>
                    <Button variant="destructive" onClick={() => void handleSubmitReview('wrong')} disabled={reviewActionLoading}>
                      <XCircle className="mr-2 h-4 w-4" />
                      Wrong
                    </Button>
                    <Button variant="secondary" onClick={() => void handleSubmitReview('abstain')} disabled={reviewActionLoading}>
                      <SkipForward className="mr-2 h-4 w-4" />
                      Skip / Unsure
                    </Button>
                    <Button variant="outline" onClick={() => setReviewIndex((value) => Math.min(reviewItems.length - 1, value + 1))} disabled={reviewIndex >= reviewItems.length - 1 || reviewActionLoading}>
                      Next
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>

                  <div className="rounded-lg border border-border/60 bg-muted/20 p-4 text-xs text-muted-foreground">
                    Keyboard shortcuts: <span className="font-mono">A</span> approve, <span className="font-mono">W</span> wrong, <span className="font-mono">U</span> skip, <span className="font-mono">←</span>/<span className="font-mono">→</span> navigate.
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
