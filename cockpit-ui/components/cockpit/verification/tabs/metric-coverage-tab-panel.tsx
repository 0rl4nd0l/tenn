import { AlertCircle, ClipboardCheck, Copy, Download, FileJson, FileSearch, RefreshCw, Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'

import type { ConfirmedMetricCoveragePacket, ConfirmedMetricCoverageRow, MetricCoverageReviewDecision } from '../types'

type MetricCoverageTabPanelProps = {
  packet: ConfirmedMetricCoveragePacket | null
  loading: boolean
  running: boolean
  error: string | null
  onLoadLatest: () => void
  onRunReview: () => void
  onExportJson: () => void
  onExportMarkdown: () => void
}

const ALL_VALUE = 'all'
const EMPTY_ROWS: ConfirmedMetricCoverageRow[] = []
const WRAPPING_BADGE_CLASS = 'max-w-full whitespace-normal break-words text-left leading-snug overflow-visible'
const REVIEW_DECISIONS: MetricCoverageReviewDecision[] = [
  'CONFIRM_SOURCE_EVIDENCE',
  'REPAIR_SOURCE_MAPPING',
  'REJECT_BAD_SOURCE_MAPPING',
  'MARK_AMBIGUOUS_OR_DERIVED',
  'KEEP_CANDIDATE_PENDING_REVIEW',
  'DATA_MISSING',
]

function uniqueOptions(rows: ConfirmedMetricCoverageRow[], reader: (row: ConfirmedMetricCoverageRow) => string | null | undefined): string[] {
  return Array.from(new Set(rows.map(reader).filter((value): value is string => Boolean(value)))).sort()
}

function formatExpected(row: ConfirmedMetricCoverageRow): string {
  if (row.expected_null) return 'Expected null'
  if (typeof row.expected_value === 'number') {
    const formatted = Math.abs(row.expected_value) >= 1_000_000
      ? row.expected_value.toLocaleString(undefined, { maximumFractionDigits: 0 })
      : row.expected_value.toLocaleString()
    return [formatted, row.currency, row.scale].filter(Boolean).join(' ')
  }
  return 'DATA_MISSING'
}

function formatOptionalNumber(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'DATA_MISSING'
  return value.toLocaleString()
}

function rowKey(row: ConfirmedMetricCoverageRow): string {
  return [
    row.fixture_id,
    row.document_id,
    row.period.period_type,
    row.period.period_end,
    row.metric_name,
  ].filter(Boolean).join(':')
}

function statusVariant(status: string): 'default' | 'secondary' | 'critical' | 'outline' {
  if (status === 'ready') return 'default'
  if (status === 'ready_with_warnings') return 'secondary'
  if (status === 'blocked' || status === 'error') return 'critical'
  return 'outline'
}

function classificationVariant(classification: string): 'default' | 'secondary' | 'critical' | 'outline' {
  if (classification === 'CONFIRMED_SOURCE_EVIDENCED') return 'default'
  if (classification === 'CANDIDATE_REVIEW_REQUIRED') return 'secondary'
  if (classification === 'AMBIGUOUS_OR_DERIVED') return 'outline'
  return 'critical'
}

function matchesText(row: ConfirmedMetricCoverageRow, query: string): boolean {
  if (!query.trim()) return true
  const haystack = [
    row.ticker,
    row.document_id,
    row.fixture,
    row.metric_name,
    row.canonical_field,
    row.recommended_action,
    row.source_pdf_path,
  ].filter(Boolean).join(' ').toLowerCase()
  return haystack.includes(query.trim().toLowerCase())
}

function firstText(...values: Array<string | null | undefined>): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}

function sourceEvidenceClipboardText(row: ConfirmedMetricCoverageRow): string {
  return [
    `ticker: ${row.ticker || 'DATA_MISSING'}`,
    `document_id: ${row.document_id || 'DATA_MISSING'}`,
    `fixture: ${row.fixture || 'DATA_MISSING'}`,
    `period: ${row.period.period_type || 'DATA_MISSING'} ${row.period.period_end || 'DATA_MISSING'}`,
    `metric: ${row.metric_name || 'DATA_MISSING'}`,
    `source_pdf_path: ${row.source_pdf_path || 'DATA_MISSING'}`,
    `source_page: ${row.source_page ?? 'DATA_MISSING'}`,
    `source_table: ${row.source_table || 'DATA_MISSING'}`,
    `source_row: ${row.source_row || 'DATA_MISSING'}`,
    `classification: ${row.classification || 'DATA_MISSING'}`,
    `recommended_action: ${row.recommended_action || 'DATA_MISSING'}`,
  ].join('\n')
}

function sourceOpenUnavailableReason(row: ConfirmedMetricCoverageRow): string | null {
  const path = row.source_pdf_path?.trim()
  if (!path) return 'DATA_MISSING: source PDF path is unavailable for this row.'
  if (row.source_pdf_status !== 'present' || row.source_pdf_present === false) {
    return `DATA_MISSING: source PDF is ${row.source_pdf_status || 'unavailable'}.`
  }
  if (!path.toLowerCase().endsWith('.pdf')) {
    return 'DATA_MISSING: source path is not a PDF.'
  }
  if (path.includes('\\') || path.split('/').includes('..') || /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(path)) {
    return 'DATA_MISSING: source PDF path is not eligible for browser opening.'
  }
  return null
}

function sourceOpenUrl(row: ConfirmedMetricCoverageRow): string | null {
  if (sourceOpenUnavailableReason(row)) return null
  const params = new URLSearchParams({ path: row.source_pdf_path?.trim() || '' })
  if (typeof row.source_page === 'number' && Number.isFinite(row.source_page)) {
    params.set('page', String(row.source_page))
    return `/api/extraction-eval/confirmed-metric-coverage/source?${params.toString()}#page=${row.source_page}`
  }
  return `/api/extraction-eval/confirmed-metric-coverage/source?${params.toString()}`
}

function DetailField({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string | number | null | undefined
  mono?: boolean
}) {
  const displayValue = value === null || value === undefined || value === '' ? 'DATA_MISSING' : String(value)
  return (
    <div className="space-y-1">
      <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={cn('break-words text-sm text-foreground', mono ? 'font-mono text-xs' : '')}>{displayValue}</dd>
    </div>
  )
}

export function MetricCoverageTabPanel({
  packet,
  loading,
  running,
  error,
  onLoadLatest,
  onRunReview,
  onExportJson,
  onExportMarkdown,
}: MetricCoverageTabPanelProps) {
  const rows = packet?.rows ?? EMPTY_ROWS
  const summary = packet?.summary ?? null
  const [classificationFilter, setClassificationFilter] = useState(ALL_VALUE)
  const [metricFilter, setMetricFilter] = useState(ALL_VALUE)
  const [tickerFilter, setTickerFilter] = useState(ALL_VALUE)
  const [recommendationFilter, setRecommendationFilter] = useState(ALL_VALUE)
  const [tierFilter, setTierFilter] = useState(ALL_VALUE)
  const [reviewStatusFilter, setReviewStatusFilter] = useState(ALL_VALUE)
  const [searchText, setSearchText] = useState('')
  const [selectedRow, setSelectedRow] = useState<ConfirmedMetricCoverageRow | null>(null)
  const [draftDecisions, setDraftDecisions] = useState<Record<string, MetricCoverageReviewDecision>>({})
  const [copiedRowKey, setCopiedRowKey] = useState<string | null>(null)

  const metricOptions = useMemo(() => uniqueOptions(rows, (row) => row.metric_name), [rows])
  const tickerOptions = useMemo(() => uniqueOptions(rows, (row) => row.ticker), [rows])
  const recommendationOptions = useMemo(() => uniqueOptions(rows, (row) => row.recommended_action), [rows])
  const tierOptions = useMemo(() => uniqueOptions(rows, (row) => row.production_metric_tier), [rows])
  const reviewStatusOptions = useMemo(() => uniqueOptions(rows, (row) => row.review_status), [rows])
  const classificationOptions = useMemo(() => uniqueOptions(rows, (row) => row.classification), [rows])

  const filteredRows = useMemo(() => rows.filter((row) => {
    if (classificationFilter !== ALL_VALUE && row.classification !== classificationFilter) return false
    if (metricFilter !== ALL_VALUE && row.metric_name !== metricFilter) return false
    if (tickerFilter !== ALL_VALUE && row.ticker !== tickerFilter) return false
    if (recommendationFilter !== ALL_VALUE && row.recommended_action !== recommendationFilter) return false
    if (tierFilter !== ALL_VALUE && row.production_metric_tier !== tierFilter) return false
    if (reviewStatusFilter !== ALL_VALUE && row.review_status !== reviewStatusFilter) return false
    return matchesText(row, searchText)
  }), [
    classificationFilter,
    metricFilter,
    recommendationFilter,
    reviewStatusFilter,
    rows,
    searchText,
    tickerFilter,
    tierFilter,
  ])

  const status = running ? 'running' : (packet?.status || 'not_generated')
  const artifacts = packet?.artifacts ?? null
  const generatedAt = firstText(summary?.generated_at, packet?.generated_at)
  const gitAvailable = summary?.git_available ?? packet?.git_available ?? null
  const gitHead = firstText(summary?.git_head_short, packet?.git_head_short, summary?.head, packet?.head)
  const gitBranch = firstText(summary?.git_branch, packet?.git_branch, summary?.branch, packet?.branch)
  const gitDirty = summary?.git_dirty ?? packet?.git_dirty ?? null
  const gitStatusSummary = summary?.git_status_short_summary ?? packet?.git_status_short_summary ?? null
  const gitUnavailableReason = firstText(summary?.git_unavailable_reason, packet?.git_unavailable_reason)
  const hasGitIdentity = gitAvailable !== false && Boolean(gitHead || gitBranch)
  const fixtureDir = firstText(summary?.fixture_dir, packet?.fixture_dir, packet?.fixtures_dir)
  const artifactPath = firstText(summary?.artifact_path, packet?.artifact_path, artifacts?.json_path)
  const reviewWarnings = Array.from(new Set([
    'This review does not run extraction.',
    'Candidate rows are not confirmed.',
    'Canonical trust semantics are unchanged.',
    ...(packet?.warnings ?? []),
  ]))
  const selectedRowKey = selectedRow ? rowKey(selectedRow) : null
  const selectedDraftDecision = selectedRowKey ? draftDecisions[selectedRowKey] : undefined
  const selectedSourceOpenUrl = selectedRow ? sourceOpenUrl(selectedRow) : null
  const selectedSourceUnavailableReason = selectedRow ? sourceOpenUnavailableReason(selectedRow) : null
  const canCopySelectedSource = Boolean(
    selectedRow?.source_pdf_path
    || selectedRow?.source_page
    || selectedRow?.source_table
    || selectedRow?.source_row,
  )

  const copySelectedSourceEvidence = async () => {
    if (!selectedRow || !canCopySelectedSource) return
    if (!navigator.clipboard?.writeText) {
      setCopiedRowKey(null)
      return
    }
    try {
      await navigator.clipboard.writeText(sourceEvidenceClipboardText(selectedRow))
      setCopiedRowKey(rowKey(selectedRow))
    } catch {
      setCopiedRowKey(null)
    }
  }

  const openSelectedSource = () => {
    if (!selectedSourceOpenUrl) return
    window.open(selectedSourceOpenUrl, '_blank', 'noopener,noreferrer')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <ClipboardCheck className="h-5 w-5 text-primary" />
          Confirmed Metric Coverage Review
        </CardTitle>
        <CardDescription>
          This review does not run extraction. Candidate metrics require human source-evidence review before production scoring. Canonical trust semantics are unchanged.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={statusVariant(status)}>{status}</Badge>
          {generatedAt ? <Badge variant="outline">generated {new Date(generatedAt).toLocaleString()}</Badge> : null}
          {hasGitIdentity && gitHead ? <Badge variant="outline">head {gitHead}</Badge> : null}
          {hasGitIdentity && gitBranch ? <Badge variant="outline">branch {gitBranch}</Badge> : null}
          {!hasGitIdentity && (summary || packet) ? <Badge variant="critical">git DATA_MISSING</Badge> : null}
          {summary?.canonical_labels_mutated === false ? <Badge variant="outline">canonical labels unchanged</Badge> : null}
        </div>

        {summary || packet ? (
          <div className="grid min-w-0 gap-3 lg:grid-cols-2">
            <div className="min-w-0 space-y-1 rounded-lg border border-border/60 p-3 text-xs text-muted-foreground">
              <div className="font-medium text-foreground">Provenance</div>
              {generatedAt ? (
                <div className="min-w-0">
                  generated_at: <span className="font-mono break-all">{generatedAt}</span>
                </div>
              ) : null}
              {hasGitIdentity ? (
                <>
                  <div className="min-w-0">
                    git: <span className="font-mono break-all">{gitHead || 'DATA_MISSING'} / {gitBranch || 'DATA_MISSING'}</span>
                  </div>
                  {gitDirty !== null ? (
                    <div className="min-w-0">
                      working tree:{' '}
                      <span className="font-mono break-all">
                        {gitDirty ? `dirty (${gitStatusSummary?.line_count ?? 0})` : 'clean'}
                      </span>
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="min-w-0">
                  git:{' '}
                  <span className="font-mono break-all">
                    DATA_MISSING{gitUnavailableReason ? `: ${gitUnavailableReason}` : ''}
                  </span>
                </div>
              )}
              {fixtureDir ? (
                <div className="min-w-0">
                  fixture_dir: <span className="font-mono break-all">{fixtureDir}</span>
                </div>
              ) : null}
              {artifactPath ? (
                <div className="min-w-0">
                  artifact_path: <span className="font-mono break-all">{artifactPath}</span>
                </div>
              ) : null}
            </div>
            <div className="min-w-0 space-y-1 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
              <div className="font-medium text-amber-900 dark:text-amber-100">Warnings</div>
              {reviewWarnings.map((warning) => (
                <div key={warning}>{warning}</div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button onClick={onRunReview} disabled={running}>
            <RefreshCw className="mr-2 h-4 w-4" />
            {packet?.summary ? 'Refresh review' : 'Run review'}
          </Button>
          <Button variant="outline" onClick={onLoadLatest} disabled={loading || running}>
            <Search className="mr-2 h-4 w-4" />
            Load latest
          </Button>
          <Button variant="outline" onClick={onExportJson} disabled={!packet?.rows?.length}>
            <FileJson className="mr-2 h-4 w-4" />
            Export JSON
          </Button>
          <Button variant="outline" onClick={onExportMarkdown} disabled={!packet?.rows?.length}>
            <Download className="mr-2 h-4 w-4" />
            Export MD
          </Button>
        </div>

        {loading || running ? (
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            {running ? 'Generating read-only review artifacts...' : 'Loading latest review artifacts...'}
          </div>
        ) : null}

        {error ? (
          <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        ) : null}

        {!summary && !loading && !running ? (
          <div className="rounded-lg border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
            No confirmed metric coverage artifact has been generated yet. Run review to create a read-only packet under reports.
          </div>
        ) : null}

        {summary ? (
          <div className="grid gap-3 md:grid-cols-6">
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-semibold text-primary">{summary.fixture_count}</p>
              <p className="text-xs text-muted-foreground">Fixtures</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-semibold text-primary">{summary.total_expectations}</p>
              <p className="text-xs text-muted-foreground">Expectations</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-semibold text-primary">{summary.scored_count}</p>
              <p className="text-xs text-muted-foreground">Scored</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-semibold text-primary">{summary.candidate_review_required_count}</p>
              <p className="text-xs text-muted-foreground">Candidates</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-semibold text-primary">{summary.ambiguous_count}</p>
              <p className="text-xs text-muted-foreground">Ambiguous</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-semibold text-primary">{summary.unsupported_count}</p>
              <p className="text-xs text-muted-foreground">Unsupported</p>
            </div>
          </div>
        ) : null}

        {artifacts ? (
          <div className="space-y-1 rounded-lg border border-border/60 p-3 text-xs text-muted-foreground">
            <div className="font-medium text-foreground">Artifacts</div>
            {artifacts.artifact_dir ? <div className="break-all font-mono">dir: {artifacts.artifact_dir}</div> : null}
            {artifacts.json_path ? <div className="break-all font-mono">json: {artifacts.json_path}</div> : null}
            {artifacts.markdown_path ? <div className="break-all font-mono">md: {artifacts.markdown_path}</div> : null}
          </div>
        ) : null}

        {rows.length > 0 ? (
          <div className="space-y-3 min-w-0">
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Field>
                <FieldLabel>Classification</FieldLabel>
                <Select value={classificationFilter} onValueChange={setClassificationFilter}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {classificationOptions.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Metric</FieldLabel>
                <Select value={metricFilter} onValueChange={setMetricFilter}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {metricOptions.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Ticker</FieldLabel>
                <Select value={tickerFilter} onValueChange={setTickerFilter}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {tickerOptions.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Recommendation</FieldLabel>
                <Select value={recommendationFilter} onValueChange={setRecommendationFilter}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {recommendationOptions.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Tier</FieldLabel>
                <Select value={tierFilter} onValueChange={setTierFilter}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {tierOptions.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Review status</FieldLabel>
                <Select value={reviewStatusFilter} onValueChange={setReviewStatusFilter}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_VALUE}>All</SelectItem>
                    {reviewStatusOptions.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <Field>
              <FieldLabel>Search ticker, document, metric, source</FieldLabel>
              <Input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="BHP revenue page 44" />
            </Field>

            <div className="text-xs text-muted-foreground">
              Showing {filteredRows.length} of {rows.length} metric expectation row(s).
            </div>

            <div className="rounded-lg border border-border/60 pb-2 overflow-x-auto">
              <Table className="min-w-[900px] table-fixed w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">Ticker</TableHead>
                    <TableHead className="w-[140px]">Document</TableHead>
                    <TableHead className="w-[100px]">Period</TableHead>
                    <TableHead className="w-[180px]">Metric</TableHead>
                    <TableHead className="w-[110px]">Expected</TableHead>
                    <TableHead className="w-[130px]">Status</TableHead>
                    <TableHead className="w-[140px]">Evidence</TableHead>
                    <TableHead className="w-[40px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRows.map((row) => (
                    <TableRow
                      key={rowKey(row)}
                      role="button"
                      tabIndex={0}
                      aria-label={`Open source evidence for ${row.ticker || 'unknown'} ${row.metric_name}`}
                      className={cn(
                        'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        selectedRowKey === rowKey(row) ? 'bg-muted/60' : 'hover:bg-muted/40',
                      )}
                      onClick={() => setSelectedRow(row)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          setSelectedRow(row)
                        }
                      }}
                    >
                      <TableCell className="align-top font-mono text-xs truncate whitespace-nowrap" title={row.ticker ?? undefined}>{row.ticker || '-'}</TableCell>
                      <TableCell className="align-top font-mono text-xs truncate whitespace-nowrap" title={(row.fixture || row.document_id) ?? undefined}>{row.fixture || row.document_id}</TableCell>
                      <TableCell className="align-top text-xs text-muted-foreground truncate whitespace-nowrap" title={`${row.period.period_type || '-'} ${row.period.period_end || ''}`}>
                        {row.period.period_type || '-'} {row.period.period_end || ''}
                      </TableCell>
                      <TableCell className="align-top font-mono text-xs truncate whitespace-nowrap" title={row.metric_name ?? undefined}>{row.metric_name}</TableCell>
                      <TableCell className="align-top text-xs truncate whitespace-nowrap" title={formatExpected(row)}>{formatExpected(row)}</TableCell>
                      <TableCell className="align-top">
                        <Badge className="max-w-full truncate whitespace-nowrap text-[10px]" variant={classificationVariant(row.classification)} title={row.classification ?? undefined}>
                          {row.classification}
                        </Badge>
                      </TableCell>
                      <TableCell className="align-top text-xs text-muted-foreground">
                        <div className="flex flex-wrap gap-1">
                          {row.source_pdf_status === 'present' ? (
                            <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 uppercase font-medium">PDF</Badge>
                          ) : (
                            <Badge variant="critical" className="text-[9px] px-1 py-0 h-3.5 uppercase font-medium">NO PDF</Badge>
                          )}
                          <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 uppercase font-medium">{row.source_evidence_status}</Badge>
                        </div>
                      </TableCell>
                      <TableCell className="align-top text-right pr-4">
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <FileSearch className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}

        <Sheet open={Boolean(selectedRow)} onOpenChange={(open) => {
          if (!open) setSelectedRow(null)
        }}>
          <SheetContent className="w-full overflow-y-auto sm:max-w-xl lg:max-w-2xl">
            {selectedRow ? (
              <>
                <SheetHeader className="border-b border-border/60">
                  <SheetTitle className="pr-8">
                    {selectedRow.ticker || 'DATA_MISSING'} {selectedRow.metric_name}
                  </SheetTitle>
                  <SheetDescription>
                    Source evidence review is local draft state only. It does not mutate canonical labels or financial truth.
                  </SheetDescription>
                </SheetHeader>

                <div className="space-y-5 p-4">
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-200">
                    Review-only workflow. Decisions in this panel are not submitted to the backend, do not update labels, and do not write financial rows.
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Badge variant={classificationVariant(selectedRow.classification)}>{selectedRow.classification}</Badge>
                    <Badge variant={selectedRow.source_pdf_status === 'present' ? 'outline' : 'critical'}>{selectedRow.source_pdf_status}</Badge>
                    <Badge variant="outline">{selectedRow.source_evidence_status}</Badge>
                    {selectedRow.evaluation_status ? <Badge variant="outline">status {selectedRow.evaluation_status}</Badge> : null}
                    {typeof selectedRow.score === 'number' ? <Badge variant="outline">score {selectedRow.score}</Badge> : null}
                  </div>

                  <dl className="grid gap-4 rounded-lg border border-border/60 bg-muted/10 p-4 md:grid-cols-2">
                    <DetailField label="Ticker" value={selectedRow.ticker} mono />
                    <DetailField label="Document / Fixture ID" value={selectedRow.fixture || selectedRow.document_id} mono />
                    <DetailField label="Document ID" value={selectedRow.document_id} mono />
                    <DetailField label="Period" value={`${selectedRow.period.period_type || 'DATA_MISSING'} ${selectedRow.period.period_end || 'DATA_MISSING'}`} mono />
                    <DetailField label="Metric" value={selectedRow.metric_name} mono />
                    <DetailField label="Canonical Field" value={selectedRow.canonical_field} mono />
                    <DetailField label="Expected Value" value={formatExpected(selectedRow)} mono />
                    <DetailField label="Actual Extracted Value" value={formatOptionalNumber(selectedRow.actual_value)} mono />
                    <DetailField label="Evaluation Status" value={selectedRow.evaluation_status} mono />
                    <DetailField label="Score" value={formatOptionalNumber(selectedRow.score)} mono />
                    <DetailField label="Classification" value={selectedRow.classification} mono />
                    <DetailField label="Recommended Action" value={selectedRow.recommended_action} mono />
                    <DetailField label="Review Status" value={selectedRow.review_status} mono />
                    <DetailField label="Production Metric Tier" value={selectedRow.production_metric_tier} mono />
                    <DetailField label="Ambiguity Reason" value={selectedRow.ambiguity_reason} />
                    <DetailField label="Reason" value={selectedRow.reason} />
                  </dl>

                  <div className="space-y-3 rounded-lg border border-border/60 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold">Source Evidence</h3>
                        <p className="text-xs text-muted-foreground">PDF path, page, table, and source row from the review artifact.</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" variant="outline" onClick={openSelectedSource} disabled={!selectedSourceOpenUrl}>
                          <FileSearch className="mr-2 h-4 w-4" />
                          Open source page
                        </Button>
                        <Button size="sm" variant="secondary" onClick={copySelectedSourceEvidence} disabled={!canCopySelectedSource}>
                          <Copy className="mr-2 h-4 w-4" />
                          {copiedRowKey === selectedRowKey ? 'Copied evidence' : 'Copy source evidence'}
                        </Button>
                      </div>
                    </div>

                    {selectedSourceUnavailableReason ? (
                      <div className="rounded-md border border-dashed border-border/70 bg-muted/20 p-3 text-xs text-muted-foreground">
                        {selectedSourceUnavailableReason}
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-border/70 bg-muted/20 p-3 text-xs text-muted-foreground">
                        Source opens through the backend allowlisted PDF route. Page hints are passed to the browser PDF viewer when available.
                      </div>
                    )}

                    <dl className="grid gap-4 md:grid-cols-2">
                      <DetailField label="Source PDF Path" value={selectedRow.source_pdf_path} mono />
                      <DetailField label="Source Page" value={selectedRow.source_page ?? null} mono />
                      <DetailField label="Source Table" value={selectedRow.source_table} mono />
                      <DetailField label="Source Row" value={selectedRow.source_row} />
                    </dl>

                    <div className="flex flex-wrap gap-1">
                      <Badge className={WRAPPING_BADGE_CLASS} variant={selectedRow.source_pdf_present ? 'outline' : 'critical'}>{selectedRow.source_pdf_present ? 'pdf present' : 'pdf missing'}</Badge>
                      <Badge className={WRAPPING_BADGE_CLASS} variant={selectedRow.source_page_present ? 'outline' : 'critical'}>{selectedRow.source_page_present ? 'page present' : 'page missing'}</Badge>
                      <Badge className={WRAPPING_BADGE_CLASS} variant={selectedRow.source_table_present ? 'outline' : 'secondary'}>{selectedRow.source_table_present ? 'table present' : 'table missing'}</Badge>
                      <Badge className={WRAPPING_BADGE_CLASS} variant={selectedRow.source_row_present ? 'outline' : 'critical'}>{selectedRow.source_row_present ? 'row present' : 'row missing'}</Badge>
                      <Badge className={WRAPPING_BADGE_CLASS} variant={selectedRow.precise_source_evidence ? 'default' : 'outline'}>{selectedRow.precise_source_evidence ? 'precise evidence' : 'evidence not precise'}</Badge>
                      {selectedRow.broad_or_suspect_source_evidence ? <Badge className={WRAPPING_BADGE_CLASS} variant="secondary">broad/suspect</Badge> : null}
                      {selectedRow.human_review_required ? <Badge className={WRAPPING_BADGE_CLASS} variant="secondary">human review</Badge> : null}
                      {selectedRow.blocked_ambiguous ? <Badge className={WRAPPING_BADGE_CLASS} variant="critical">blocked ambiguous</Badge> : null}
                    </div>
                  </div>

                  <div className="space-y-3 rounded-lg border border-border/60 p-4">
                    <div>
                      <h3 className="text-sm font-semibold">Manual Review Decision</h3>
                      <p className="text-xs text-muted-foreground">Draft-only selection for analyst triage. No backend mutation is performed.</p>
                    </div>
                    <Select
                      value={selectedDraftDecision || ''}
                      onValueChange={(value) => {
                        if (!selectedRowKey) return
                        setDraftDecisions((current) => ({
                          ...current,
                          [selectedRowKey]: value as MetricCoverageReviewDecision,
                        }))
                      }}
                    >
                      <SelectTrigger aria-label="Draft review decision">
                        <SelectValue placeholder="Select draft decision" />
                      </SelectTrigger>
                      <SelectContent>
                        {REVIEW_DECISIONS.map((decision) => (
                          <SelectItem key={decision} value={decision}>{decision}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="rounded-md border border-dashed border-border/70 bg-muted/20 p-3 text-xs text-muted-foreground">
                      Current draft decision: <span className="font-mono text-foreground">{selectedDraftDecision || 'DATA_MISSING'}</span>. Canonical labels remain unchanged.
                    </div>
                  </div>
                </div>
              </>
            ) : null}
          </SheetContent>
        </Sheet>
      </CardContent>
    </Card>
  )
}
