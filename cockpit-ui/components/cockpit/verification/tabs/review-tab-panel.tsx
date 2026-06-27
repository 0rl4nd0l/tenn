import { useState, useEffect } from 'react'
import { AlertCircle, CheckCircle2, FileImage, FileJson, Play, RefreshCw, Search, XCircle, Maximize2, Minimize2, Brain, Code, TrendingUp, HelpCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type {
  ContextDocument,
  ExtractionEvidenceQuality,
  ExtractionReviewErrorQueue,
  ExtractionReviewItem,
  ExtractionReviewRunSummary,
  ExtractionReviewSessionSummary,
  ExtractionReviewSession,
} from '@/lib/cockpit-types'

import type { SnippetImageState } from '../types'
import {
  evidenceMethodLabel,
  evidenceQualityBadgeVariant,
  evidenceQualityBody,
  evidenceQualityHeadline,
  evidenceQualityLabel,
  formatMethodLabel,
  reviewStatusLabel,
  statusVariant,
  summarizeSessionDocuments,
} from '../utils'

const NO_RECENT_RUN_SELECTED = '__no_recent_run_selected__'
const NO_REVIEW_SESSION_SELECTED = '__no_review_session_selected__'

type ReviewTabPanelProps = {
  documents: ContextDocument[]
  documentsLoading: boolean
  docsLimit: string
  extraDocumentIds: string
  reviewError: string | null
  reviewActionLoading: boolean
  reviewSession: ExtractionReviewSession | null
  reviewSessionLoadingMessage: string | null
  wrongQueue: ExtractionReviewErrorQueue | null
  recentRuns: ExtractionReviewRunSummary[]
  recentRunsLoading: boolean
  recentRunsError: string | null
  recentReviewSessions: ExtractionReviewSessionSummary[]
  recentReviewSessionsLoading: boolean
  recentReviewSessionsError: string | null
  selectedRunId: string
  selectedReviewSessionId: string
  selectedDocumentId: string
  selectedReviewDocumentIds: string[]
  currentReviewItem: ExtractionReviewItem | null
  currentReviewIndex: number
  currentEvidenceQuality: ExtractionEvidenceQuality
  matchedEvidenceText: string | null
  currentSnippetPath: string | null
  currentSnippetUrl: string | null
  currentSnippetImageSrc: string | null
  currentSnippetRenderKey: string
  currentRowRef: string | null
  reviewItems: ExtractionReviewItem[]
  evidenceSuspendMessage: string | null
  snippetImageState: SnippetImageState
  hasPrevReviewItem: boolean
  hasNextReviewItem: boolean
  onDocsLimitChange: (value: string) => void
  onExtraDocumentIdsChange: (value: string) => void
  onLoadDocuments: () => void
  onRunExtraction: () => void
  onLoadReview: () => void
  onRefreshWrongQueue: () => void
  onExportReviewArtifacts: () => void
  onSelectedRunIdChange: (value: string) => void
  onLoadRecentRuns: () => void
  onInspectSelectedRun: () => void
  onSelectedReviewSessionIdChange: (value: string) => void
  onLoadReviewSessions: () => void
  onInspectSelectedReviewSession: () => void
  onSelectedDocumentIdChange: (value: string) => void
  onMoveReviewSelection: (direction: 'prev' | 'next') => void
  onSelectedReviewItemIdChange: (value: string) => void
  onSnippetImageLoad: () => void
  onSnippetImageError: () => void
  onSubmitReview: (verdict: 'correct' | 'wrong' | 'unsure') => void
}

export function ReviewTabPanel({
  documents,
  documentsLoading,
  docsLimit,
  extraDocumentIds,
  reviewError,
  reviewActionLoading,
  reviewSession,
  reviewSessionLoadingMessage,
  wrongQueue,
  recentRuns,
  recentRunsLoading,
  recentRunsError,
  recentReviewSessions,
  recentReviewSessionsLoading,
  recentReviewSessionsError,
  selectedRunId,
  selectedReviewSessionId,
  selectedDocumentId,
  selectedReviewDocumentIds,
  currentReviewItem,
  currentReviewIndex,
  currentEvidenceQuality,
  matchedEvidenceText,
  currentSnippetPath,
  currentSnippetUrl,
  currentSnippetImageSrc,
  currentSnippetRenderKey,
  reviewItems,
  evidenceSuspendMessage,
  snippetImageState,
  hasPrevReviewItem,
  hasNextReviewItem,
  onDocsLimitChange,
  onExtraDocumentIdsChange,
  onLoadDocuments,
  onRunExtraction,
  onLoadReview,
  onRefreshWrongQueue,
  onExportReviewArtifacts,
  onSelectedRunIdChange,
  onLoadRecentRuns,
  onInspectSelectedRun,
  onSelectedReviewSessionIdChange,
  onLoadReviewSessions,
  onInspectSelectedReviewSession,
  onSelectedDocumentIdChange,
  onMoveReviewSelection,
  onSelectedReviewItemIdChange,
  onSnippetImageLoad,
  onSnippetImageError,
  onSubmitReview,
}: ReviewTabPanelProps) {
  const [isZoomed, setIsZoomed] = useState(false)

  // Reset zoom when switching items
  useEffect(() => {
    setIsZoomed(false)
  }, [currentSnippetUrl, currentReviewItem?.item_id])

  const reviewStateLabel = (run: ExtractionReviewRunSummary): string => {
    if (run.review_ready) return 'review ready'
    return run.review_reason || 'not reviewable'
  }
  const sessionLabel = (session: ExtractionReviewSessionSummary): string => {
    const tickerLabel = session.tickers.length > 0 ? session.tickers.join(',') : 'BROAD'
    const title = session.titles[0] || session.session_status || session.session_id
    const itemCount = session.item_count ?? session.summary?.total ?? 0
    return `${(session.updated_at || session.created_at || '').slice(0, 16)} | ${tickerLabel} | ${itemCount} items | ${title}`
  }
  const recentRunsSelectLabel = recentRunsLoading ? 'Loading runs...' : 'Select a past run'
  const reviewSessionsSelectLabel = recentReviewSessionsLoading ? 'Loading saved reviews...' : 'Select a saved review'

  return (
    <div className="space-y-6">
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
              <Input value={docsLimit} onChange={(event) => onDocsLimitChange(event.target.value)} className="font-mono" />
            </Field>
            <Field>
              <FieldLabel>Extra document IDs</FieldLabel>
              <Input
                value={extraDocumentIds}
                onChange={(event) => onExtraDocumentIdsChange(event.target.value)}
                placeholder="Comma or space separated document IDs"
                className="font-mono"
              />
            </Field>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex -space-x-px">
                <Button variant="outline" onClick={onLoadDocuments} disabled={documentsLoading || reviewActionLoading} className="rounded-r-none border-r-0">
                  <Search className="mr-2 h-4 w-4" />
                  Load Docs
                </Button>
                <Button variant="outline" onClick={onRunExtraction} disabled={reviewActionLoading} className="rounded-none border-x-0">
                  <Play className="mr-2 h-4 w-4" />
                  Run
                </Button>
                <Button onClick={onLoadReview} disabled={reviewActionLoading} className="rounded-l-none">
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Latest + Review
                </Button>
              </div>

              <div className="flex -space-x-px">
                <Button variant="outline" onClick={onRefreshWrongQueue} disabled={reviewActionLoading} size="sm" className="rounded-r-none border-r-0">
                  <RefreshCw className="mr-1 h-3.5 w-3.5" />
                  Queue
                </Button>
                <Button variant="outline" onClick={onExportReviewArtifacts} disabled={!reviewSession && !wrongQueue} size="sm" className="rounded-l-none">
                  <FileJson className="mr-1 h-3.5 w-3.5" />
                  Export
                </Button>
              </div>
            </div>
          </div>

          <div className="grid gap-4 rounded-lg border border-border/40 bg-muted/5 p-3 md:grid-cols-[200px_1fr_auto]">
            <Field>
              <FieldLabel className="text-[10px] uppercase tracking-wider text-muted-foreground">Recent runs</FieldLabel>
              <Select
                value={selectedRunId || NO_RECENT_RUN_SELECTED}
                onValueChange={(value) => onSelectedRunIdChange(value === NO_RECENT_RUN_SELECTED ? '' : value)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_RECENT_RUN_SELECTED} className="text-xs">
                    {recentRunsSelectLabel}
                  </SelectItem>
                  {recentRuns.map((run) => (
                    <SelectItem key={run.run_id} value={run.run_id} className="text-xs">
                      {`${run.created_at.slice(0, 16)} | ${run.status} | ${run.metrics_count ?? 0}m | ${reviewStateLabel(run)}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <div className="flex flex-wrap items-center gap-1.5 pt-5">
              {recentRuns.length === 0 ? (
                <span className="text-[10px] text-muted-foreground italic">No historical runs yet.</span>
              ) : recentRuns.slice(0, 3).map((run) => (
                <Badge
                  key={run.run_id}
                  variant={run.review_ready ? 'outline' : 'secondary'}
                  className="h-5 rounded-sm px-1.5 text-[9px] font-medium uppercase"
                >
                  {run.status.slice(0, 3)} {run.metrics_count ?? 0}m {run.review_ready ? 'review' : reviewStateLabel(run).slice(0, 12)}
                </Badge>
              ))}
            </div>
            <div className="flex items-center gap-1 pt-5">
              <Button variant="ghost" onClick={onLoadRecentRuns} disabled={recentRunsLoading || reviewActionLoading} size="icon" className="h-7 w-7">
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
              <Button variant="secondary" onClick={onInspectSelectedRun} disabled={!selectedRunId || reviewActionLoading} size="sm" className="h-7 text-xs">
                Inspect
              </Button>
            </div>
          </div>
          {recentRunsError ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
              {recentRunsError}
            </div>
          ) : null}

          <div className="grid gap-4 rounded-lg border border-border/40 bg-muted/5 p-3 md:grid-cols-[minmax(220px,1fr)_auto]">
            <Field>
              <FieldLabel className="text-[10px] uppercase tracking-wider text-muted-foreground">Saved review sessions</FieldLabel>
              <Select
                value={selectedReviewSessionId || NO_REVIEW_SESSION_SELECTED}
                onValueChange={(value) => onSelectedReviewSessionIdChange(value === NO_REVIEW_SESSION_SELECTED ? '' : value)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_REVIEW_SESSION_SELECTED} className="text-xs">
                    {reviewSessionsSelectLabel}
                  </SelectItem>
                  {recentReviewSessions.map((session) => (
                    <SelectItem key={session.session_id} value={session.session_id} className="text-xs">
                      {sessionLabel(session)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {recentReviewSessions.length === 0 && !recentReviewSessionsLoading ? (
                <p className="mt-1 text-[10px] text-muted-foreground">No saved review sessions yet.</p>
              ) : null}
            </Field>
            <div className="flex items-end gap-1">
              <Button variant="ghost" onClick={onLoadReviewSessions} disabled={recentReviewSessionsLoading || reviewActionLoading} size="icon" className="h-7 w-7">
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
              <Button variant="secondary" onClick={onInspectSelectedReviewSession} disabled={!selectedReviewSessionId || reviewActionLoading} size="sm" className="h-7 text-xs">
                Open
              </Button>
            </div>
          </div>
          {recentReviewSessionsError ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
              {recentReviewSessionsError}
            </div>
          ) : null}

          {reviewError ? (
            <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {reviewError}
            </div>
          ) : null}

          {reviewActionLoading ? (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              {reviewSessionLoadingMessage || (currentReviewItem ? 'Saving review verdict...' : 'Processing manual review action...')}
            </div>
          ) : null}

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
                      onClick={() => onSelectedDocumentIdChange(doc.document_id)}
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
            Use <span className="font-medium text-foreground">Latest + Review</span> to reprocess the selected PDFs with the current method, or <span className="font-medium text-foreground">Inspect</span> to open a historical run without rerunning extraction.
          </div>
        </CardContent>
      </Card>

      {reviewSessionLoadingMessage ? (
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
      ) : null}

      {reviewSession && !currentReviewItem ? (
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
            {reviewSession.documents && reviewSession.documents.length > 0 ? (
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
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={onRunExtraction} disabled={reviewActionLoading}>
                <Play className="mr-2 h-4 w-4" />
                Run Extraction Again
              </Button>
              <Button onClick={onLoadReview} disabled={reviewActionLoading}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry Load Review
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {reviewSession && currentReviewItem ? (
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
                        onClick={() => onMoveReviewSelection('prev')}
                        disabled={!hasPrevReviewItem}
                      >
                        Prev
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => onMoveReviewSelection('next')}
                        disabled={!hasNextReviewItem}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                  <div role="listbox" aria-label="Review items" className="max-h-[720px] overflow-y-auto p-1.5">
                    {reviewItems.map((item) => {
                      const isActive = item.item_id === currentReviewItem.item_id
                      const status = item.review_status
                      const statusColor = 
                        status === 'approved' ? 'bg-emerald-500' : 
                        status === 'wrong' ? 'bg-rose-500' : 
                        status === 'abstain' ? 'bg-amber-500' : 
                        'bg-slate-300 dark:bg-slate-700'

                      return (
                        <button
                          key={item.item_id}
                          type="button"
                          role="option"
                          aria-selected={isActive}
                          onClick={() => onSelectedReviewItemIdChange(item.item_id)}
                          className={`flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left transition ${isActive ? 'border-primary bg-primary/5 shadow-sm' : 'border-transparent hover:border-border/60 hover:bg-muted/10'}`}
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-[10px] font-bold uppercase tracking-tight text-muted-foreground">{item.metric_name}</p>
                            <p className="truncate font-mono text-sm font-bold text-foreground">{String(item.metric_value ?? item.extracted_value ?? '-')}</p>
                          </div>
                          <div className={`h-2 w-2 shrink-0 rounded-full ${statusColor} shadow-[0_0_8px_rgba(0,0,0,0.1)]`} />
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>

              <div key={currentSnippetRenderKey} className="flex flex-col gap-6">
                <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/40 pb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={statusVariant(currentReviewItem.review_status)} className="rounded-sm px-1.5 py-0 text-[10px] font-bold uppercase">{reviewStatusLabel(currentReviewItem.review_status)}</Badge>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Metric Review</p>
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight">{currentReviewItem.metric_name}</h2>
                  </div>
                  <div className="flex flex-col items-end">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Extracted Value</p>
                    <div className="flex items-center gap-3">
                      {currentReviewItem.historical_value !== undefined && currentReviewItem.historical_value !== null && (
                        <div className="flex flex-col items-end mr-2">
                          <p className="text-[10px] font-bold uppercase text-muted-foreground/60 leading-none mb-1">Previous Period</p>
                          <div className="flex items-center gap-1.5">
                            <TrendingUp className="h-3 w-3 text-muted-foreground/60" />
                            <span className="font-mono text-sm font-semibold text-muted-foreground/80">{String(currentReviewItem.historical_value)}</span>
                            {(() => {
                              const currVal = currentReviewItem.metric_value ?? currentReviewItem.extracted_value
                              const prevVal = currentReviewItem.historical_value
                              if (currVal === null || currVal === undefined || prevVal === null || prevVal === undefined) return null
                              const curr = Number(currVal)
                              const prev = Number(prevVal)
                              if (isNaN(curr) || isNaN(prev) || prev === 0) return null
                              const diff = Math.abs((curr - prev) / prev)
                              if (diff > 0.5) {
                                return (
                                  <Badge variant="destructive" className="ml-1 h-4 px-1 text-[8px] font-bold leading-none uppercase">
                                    Anomaly
                                  </Badge>
                                )
                              }
                              return null
                            })()}
                          </div>
                        </div>
                      )}
                      <p className="font-mono text-3xl font-black text-primary">{String(currentReviewItem.metric_value ?? currentReviewItem.extracted_value ?? '-')}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 rounded-xl border border-border/60 bg-muted/5 p-5 shadow-sm">
                  <Tabs defaultValue="image" className="w-full">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-2 mb-2">
                      <TabsList className="h-8 bg-muted/30">
                        <TabsTrigger value="image" className="gap-1.5 text-[10px] uppercase font-bold px-3">
                          <FileImage className="h-3 w-3" />
                          Evidence Image
                        </TabsTrigger>
                        <TabsTrigger value="reasoning" className="gap-1.5 text-[10px] uppercase font-bold px-3">
                          <Brain className="h-3 w-3" />
                          Thinking
                        </TabsTrigger>
                        <TabsTrigger value="markdown" className="gap-1.5 text-[10px] uppercase font-bold px-3">
                          <Code className="h-3 w-3" />
                          Markdown
                        </TabsTrigger>
                      </TabsList>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant={evidenceQualityBadgeVariant(currentEvidenceQuality)} className="rounded-sm px-1.5 py-0 text-[10px] font-bold uppercase">{evidenceQualityLabel(currentEvidenceQuality)}</Badge>
                        <Badge variant="outline" className="rounded-sm px-1.5 py-0 text-[10px] font-bold uppercase">page {currentReviewItem.page_number ?? '?'}</Badge>
                        <Badge variant="outline" className="rounded-sm px-1.5 py-0 text-[10px] font-bold uppercase">method {evidenceMethodLabel(currentReviewItem)}</Badge>
                      </div>
                    </div>

                    <TabsContent value="image" className="space-y-4 mt-0">
                      <div className="rounded-md border border-border/40 bg-muted/20 p-3 text-xs">
                        <p className="font-bold text-foreground">{evidenceQualityHeadline(currentEvidenceQuality)}</p>
                        <p className="mt-0.5 text-muted-foreground">{evidenceQualityBody(currentEvidenceQuality)}</p>
                      </div>

                      {evidenceSuspendMessage ? (
                        <div className="rounded-md border border-dashed border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                          {evidenceSuspendMessage}
                        </div>
                      ) : currentSnippetUrl ? (
                        <div className="space-y-3">
                          <div className={`relative overflow-hidden rounded-md border border-border/60 bg-black/5 shadow-inner transition-all duration-200 ${isZoomed ? 'overflow-auto cursor-zoom-out' : 'cursor-zoom-in'}`}
                              onClick={() => setIsZoomed(!isZoomed)}>
                            {currentSnippetImageSrc ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                key={currentSnippetRenderKey}
                                src={currentSnippetImageSrc}
                                alt={`Evidence for ${currentReviewItem.metric_name}`}
                                onLoad={onSnippetImageLoad}
                                onError={onSnippetImageError}
                                className={`w-full object-top transition-all duration-300 ${isZoomed ? 'max-h-none w-[180%] max-w-none' : 'max-h-[800px]'} ${snippetImageState.status === 'ready' ? 'opacity-100' : 'opacity-0'}`}
                              />
                            ) : null}
                            
                            <div className="absolute right-4 top-4 z-10">
                              <Button
                                variant="secondary"
                                size="icon"
                                type="button"
                                className="h-8 w-8 rounded-full bg-background/80 shadow-md backdrop-blur-sm"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setIsZoomed(!isZoomed)
                                }}
                                title={isZoomed ? "Zoom out" : "Zoom in"}
                              >
                                {isZoomed ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                              </Button>
                            </div>

                            {snippetImageState.status !== 'ready' ? (
                              <div className="absolute inset-0 flex items-center justify-center bg-background/85 px-6 text-center text-sm text-muted-foreground">
                                <div className="space-y-3">
                                  {(snippetImageState.status === 'loading' || snippetImageState.status === 'retrying') ? (
                                    <div className="mx-auto h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                                  ) : null}
                                  <p>
                                    {snippetImageState.message
                                      || (snippetImageState.status === 'retrying'
                                        ? 'Refreshing snippet evidence...'
                                        : 'Loading snippet evidence...')}
                                  </p>
                                </div>
                              </div>
                            ) : null}
                          </div>
                          <p className="font-mono text-[10px] text-muted-foreground">{currentSnippetPath}</p>
                        </div>
                      ) : (
                        <div className="rounded-md border border-dashed border-border/40 bg-muted/20 p-4 text-sm text-muted-foreground">
                          {currentReviewItem.snippet.reason || evidenceQualityHeadline(currentEvidenceQuality)}
                        </div>
                      )}

                      {matchedEvidenceText && !evidenceSuspendMessage ? (
                        <div className="space-y-2 border-t border-border/40 pt-4">
                          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                            {currentEvidenceQuality === 'precise' ? 'Matched source line' : 'Preserved evidence text'}
                          </p>
                          <pre className="whitespace-pre-wrap rounded-md bg-muted/20 p-3 font-mono text-xs leading-5 text-foreground">
                            {matchedEvidenceText}
                          </pre>
                        </div>
                      ) : null}
                    </TabsContent>

                    <TabsContent value="reasoning" className="mt-0">
                      <div className="min-h-[400px] rounded-md border border-border/60 bg-black/10 p-6 shadow-inner">
                        <div className="flex items-center gap-2 mb-4 text-xs font-bold uppercase text-muted-foreground">
                          <Brain className="h-3.5 w-3.5 text-primary" />
                          Extraction Thinking Logic
                        </div>
                        {currentReviewItem.thinking ? (
                          <div className="space-y-4">
                            <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap italic font-serif">
                              &ldquo;{currentReviewItem.thinking}&rdquo;
                            </p>
                            <div className="pt-4 border-t border-border/20">
                              <p className="text-[10px] font-bold uppercase text-muted-foreground mb-2">Confidence Context</p>
                              <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="font-mono">{Math.round((currentReviewItem.confidence_metrics ?? 0) * 100)}% Confidence</Badge>
                                <span className="text-[10px] text-muted-foreground italic">Self-reported by LLM during pass 3a</span>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-20 text-center space-y-3 opacity-50">
                            <HelpCircle className="h-10 w-10 text-muted-foreground/30" />
                            <p className="text-sm text-muted-foreground">No thinking trace was recorded for this extraction.</p>
                          </div>
                        )}
                      </div>
                    </TabsContent>

                    <TabsContent value="markdown" className="mt-0">
                      <div className="min-h-[400px] max-h-[800px] overflow-auto rounded-md border border-border/60 bg-black/20 p-0 shadow-inner">
                        <div className="sticky top-0 z-10 flex items-center gap-2 p-3 border-b border-border/40 bg-background/95 backdrop-blur-sm text-xs font-bold uppercase text-muted-foreground">
                          <Code className="h-3.5 w-3.5 text-primary" />
                          Raw Table Markdown (Parser View)
                        </div>
                        {currentReviewItem.raw_markdown ? (
                          <div className="p-4">
                            <pre className="font-mono text-[11px] leading-tight text-emerald-400/90 whitespace-pre">
                              {currentReviewItem.raw_markdown}
                            </pre>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center py-20 text-center space-y-3 opacity-50">
                            <Code className="h-10 w-10 text-muted-foreground/30" />
                            <p className="text-sm text-muted-foreground">No raw table markdown was preserved.</p>
                          </div>
                        )}
                      </div>
                    </TabsContent>
                  </Tabs>
                </div>

                <div className="grid gap-x-6 gap-y-4 rounded-lg border border-border/40 bg-muted/10 p-4 text-[13px] md:grid-cols-2 lg:grid-cols-3">
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Period</p>
                    <p className="font-mono font-medium">{currentReviewItem.period_type || '?'} {currentReviewItem.period_end || '?'}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Document</p>
                    <p className="truncate font-medium" title={currentReviewItem.title || currentReviewItem.document_id}>{currentReviewItem.title || currentReviewItem.document_id}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Method Provenance</p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {formatMethodLabel(currentReviewItem.actual_method)} | {currentReviewItem.parser_id || '-'}
                    </p>
                  </div>
                  <div className="space-y-1 md:col-span-2 lg:col-span-3">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Provenance Summary</p>
                    <p className="text-muted-foreground leading-relaxed">{currentReviewItem.evidence_summary || currentReviewItem.evidence_reference || 'No provenance summary'}</p>
                  </div>
                </div>

                {currentReviewItem.method_warnings && currentReviewItem.method_warnings.length > 0 ? (
                  <div className="rounded-lg border border-dashed border-destructive/40 bg-destructive/5 p-3 text-xs text-destructive">
                    <span className="font-bold uppercase tracking-tight mr-2">Warning:</span> {currentReviewItem.method_warnings.join('; ')}
                  </div>
                ) : null}

                <div className="sticky bottom-0 z-10 -mx-1 mt-auto border-t border-border/60 bg-background/95 p-4 backdrop-blur-sm shadow-[0_-4px_12px_rgba(0,0,0,0.05)] rounded-b-lg">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-bold">Record Verdict</p>
                      <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
                        <span><kbd className="rounded border px-1 font-sans">C</kbd> Correct</span>
                        <span><kbd className="rounded border px-1 font-sans">W</kbd> Wrong</span>
                        <span><kbd className="rounded border px-1 font-sans">U</kbd> Unsure</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="lg"
                        onClick={() => onSubmitReview('correct')}
                        aria-label={`Mark ${currentReviewItem.metric_name} as correct`}
                        disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}
                        className="bg-emerald-600 hover:bg-emerald-700 h-11 px-6"
                      >
                        <CheckCircle2 className="mr-2 h-5 w-5" />
                        Correct
                      </Button>
                      <Button
                        size="lg"
                        variant="destructive"
                        onClick={() => onSubmitReview('wrong')}
                        aria-label={`Mark ${currentReviewItem.metric_name} as wrong`}
                        disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}
                        className="h-11 px-6"
                      >
                        <XCircle className="mr-2 h-5 w-5" />
                        Wrong
                      </Button>
                      <Button
                        size="lg"
                        variant="secondary"
                        onClick={() => onSubmitReview('unsure')}
                        aria-label={`Mark ${currentReviewItem.metric_name} as unsure`}
                        disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}
                        className="h-11 px-6"
                      >
                        Unsure
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

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
                    {item.reviewer_note ? <p className="md:col-span-2"><span className="text-muted-foreground">Note:</span> {item.reviewer_note}</p> : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
