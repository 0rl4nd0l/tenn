import Image from 'next/image'
import { AlertCircle, CheckCircle2, FileImage, FileJson, Play, RefreshCw, Search, XCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type {
  ContextDocument,
  ExtractionEvidenceQuality,
  ExtractionReviewErrorQueue,
  ExtractionReviewItem,
  ExtractionReviewRunSummary,
  ExtractionReviewSession,
} from '@/lib/cockpit-types'

import type { SnippetImageState } from '../types'
import {
  evidenceMethodLabel,
  evidenceQualityBadgeVariant,
  evidenceQualityBody,
  evidenceQualityForItem,
  evidenceQualityHeadline,
  evidenceQualityLabel,
  formatMethodLabel,
  reviewStatusLabel,
  statusVariant,
  summarizeSessionDocuments,
} from '../utils'

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
  selectedRunId: string
  selectedDocumentId: string
  selectedReviewDocumentIds: string[]
  currentReviewItem: ExtractionReviewItem | null
  currentReviewIndex: number
  currentEvidenceQuality: ExtractionEvidenceQuality
  matchedEvidenceText: string | null
  currentSnippetPath: string | null
  currentSnippetUrl: string | null
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
  selectedRunId,
  selectedDocumentId,
  selectedReviewDocumentIds,
  currentReviewItem,
  currentReviewIndex,
  currentEvidenceQuality,
  matchedEvidenceText,
  currentSnippetPath,
  currentSnippetUrl,
  currentSnippetRenderKey,
  currentRowRef,
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
  onSelectedDocumentIdChange,
  onMoveReviewSelection,
  onSelectedReviewItemIdChange,
  onSnippetImageLoad,
  onSnippetImageError,
  onSubmitReview,
}: ReviewTabPanelProps) {
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

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={onLoadDocuments} disabled={documentsLoading || reviewActionLoading}>
              <Search className="mr-2 h-4 w-4" />
              Load Docs
            </Button>
            <Button variant="outline" onClick={onRunExtraction} disabled={reviewActionLoading}>
              <Play className="mr-2 h-4 w-4" />
              Run Extraction
            </Button>
            <Button onClick={onLoadReview} disabled={reviewActionLoading}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Run Latest + Load Review
            </Button>
            <Button variant="outline" onClick={onRefreshWrongQueue} disabled={reviewActionLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh Wrong Queue
            </Button>
            <Button variant="outline" onClick={onExportReviewArtifacts} disabled={!reviewSession && !wrongQueue}>
              <FileJson className="mr-2 h-4 w-4" />
              Export Review Artifacts
            </Button>
          </div>

          <div className="grid gap-4 rounded-lg border border-border/60 bg-muted/10 p-4 md:grid-cols-[220px_1fr_auto_auto]">
            <Field>
              <FieldLabel>Recent runs</FieldLabel>
              <Select value={selectedRunId || undefined} onValueChange={onSelectedRunIdChange}>
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
            <Button variant="outline" onClick={onLoadRecentRuns} disabled={recentRunsLoading || reviewActionLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh Runs
            </Button>
            <Button variant="outline" onClick={onInspectSelectedRun} disabled={!selectedRunId || reviewActionLoading}>
              <Search className="mr-2 h-4 w-4" />
              Inspect Selected Run
            </Button>
          </div>

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
            Use <span className="font-medium text-foreground">Run Latest + Load Review</span> to reprocess the selected PDFs with the current method, or <span className="font-medium text-foreground">Inspect Selected Run</span> to open a historical run without rerunning extraction.
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
                  <div role="listbox" aria-label="Review items" className="max-h-[720px] overflow-y-auto p-2">
                    {reviewItems.map((item) => {
                      const isActive = item.item_id === currentReviewItem.item_id
                      const itemEvidenceQuality = evidenceQualityForItem(item)
                      return (
                        <button
                          key={item.item_id}
                          type="button"
                          role="option"
                          aria-selected={isActive}
                          onClick={() => onSelectedReviewItemIdChange(item.item_id)}
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
                            {item.table_type ? <span>{item.table_type}</span> : null}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>

              <div key={currentSnippetRenderKey} className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant(currentReviewItem.review_status)}>{reviewStatusLabel(currentReviewItem.review_status)}</Badge>
                  <Badge variant="outline">{currentReviewItem.metric_name}</Badge>
                  <Badge variant={evidenceQualityBadgeVariant(currentEvidenceQuality)}>{evidenceQualityLabel(currentEvidenceQuality)}</Badge>
                  <Badge variant="outline">page {currentReviewItem.page_number ?? '?'}</Badge>
                  <Badge variant="outline">method {evidenceMethodLabel(currentReviewItem)}</Badge>
                  <Badge variant="outline">{currentReviewItem.strict_method ? 'strict' : 'auto'}</Badge>
                  {currentReviewItem.snippet.kind ? <Badge variant="outline">{currentReviewItem.snippet.kind}</Badge> : null}
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

                {currentReviewItem.method_warnings && currentReviewItem.method_warnings.length > 0 ? (
                  <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-xs text-muted-foreground">
                    Warnings: {currentReviewItem.method_warnings.join('; ')}
                  </div>
                ) : null}

                <div className="space-y-3 rounded-lg border border-border/60 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <FileImage className="h-4 w-4 text-primary" />
                    Evidence Snippet
                  </div>

                  <div className="flex flex-wrap gap-2 text-xs">
                    <Badge variant={evidenceQualityBadgeVariant(currentEvidenceQuality)}>{evidenceQualityHeadline(currentEvidenceQuality)}</Badge>
                    <Badge variant="outline">snippet {currentReviewItem.snippet.status}</Badge>
                    <Badge variant="outline">provenance {currentReviewItem.provenance_status || 'unknown'}</Badge>
                    {currentReviewItem.error_stage ? <Badge variant="outline">error {currentReviewItem.error_stage}</Badge> : null}
                    {currentReviewItem.source_label ? <Badge variant="outline">source {currentReviewItem.source_label}</Badge> : null}
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
                      {currentEvidenceQuality === 'approximate' ? (
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
                      ) : null}

                      <div className="relative overflow-hidden rounded-md border border-border/60 bg-black/20">
                        <Image
                          key={currentSnippetRenderKey}
                          src={currentSnippetUrl}
                          alt={`Snippet for ${currentReviewItem.metric_name}`}
                          width={900}
                          height={520}
                          unoptimized
                          onLoad={onSnippetImageLoad}
                          onError={onSnippetImageError}
                          className={`max-h-[360px] w-full object-contain transition-opacity ${snippetImageState.status === 'ready' ? 'opacity-100' : 'opacity-0'}`}
                        />
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

                      <p className="text-xs text-muted-foreground">{currentSnippetPath}</p>
                    </div>
                  ) : (
                    <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                      {currentReviewItem.snippet.reason || evidenceQualityHeadline(currentEvidenceQuality)}
                    </div>
                  )}

                  {snippetImageState.status === 'failed' && currentSnippetUrl && !evidenceSuspendMessage ? (
                    <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                      {snippetImageState.message || currentReviewItem.snippet.reason || evidenceQualityBody(currentEvidenceQuality)}
                    </div>
                  ) : null}

                  {matchedEvidenceText && !evidenceSuspendMessage ? (
                    <div>
                      <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                        {currentEvidenceQuality === 'precise' ? 'Matched source line' : 'Preserved evidence text'}
                      </p>
                      <pre className="whitespace-pre-wrap rounded-md bg-muted/20 p-3 text-xs leading-5 text-foreground">
                        {matchedEvidenceText}
                      </pre>
                    </div>
                  ) : null}

                  {!matchedEvidenceText && !evidenceSuspendMessage ? (
                    <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                      {currentEvidenceQuality === 'approximate'
                        ? 'Exact matched text was not preserved for this metric. Review the source preview image above for manual verification.'
                        : 'No matched text or usable visual evidence is available for this metric.'}
                    </div>
                  ) : null}

                  {currentReviewItem.evidence_reference && !evidenceSuspendMessage ? (
                    <div>
                      <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">Evidence reference</p>
                      <pre className="whitespace-pre-wrap rounded-md bg-muted/20 p-3 text-xs leading-5 text-muted-foreground">
                        {currentReviewItem.evidence_reference}
                      </pre>
                    </div>
                  ) : null}

                  {currentReviewItem.snippet.ascii_preview && !evidenceSuspendMessage ? (
                    <details className="rounded-md border border-border/60 bg-muted/20 p-3">
                      <summary className="cursor-pointer text-xs uppercase tracking-wide text-muted-foreground">ASCII preview</summary>
                      <pre className="mt-3 overflow-x-auto rounded-md bg-black/30 p-3 font-mono text-[10px] leading-3 text-muted-foreground">
                        {currentReviewItem.snippet.ascii_preview}
                      </pre>
                    </details>
                  ) : null}

                  <div className="rounded-lg border border-border/60 p-4">
                    <p className="mb-3 text-sm font-medium">Verdict</p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => onSubmitReview('correct')}
                        aria-label={`Mark ${currentReviewItem.metric_name} as correct`}
                        disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}
                      >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Correct
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => onSubmitReview('wrong')}
                        aria-label={`Mark ${currentReviewItem.metric_name} as wrong`}
                        disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        Wrong
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => onSubmitReview('unsure')}
                        aria-label={`Mark ${currentReviewItem.metric_name} as unsure`}
                        disabled={reviewActionLoading || Boolean(evidenceSuspendMessage)}
                      >
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
