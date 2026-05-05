import { AlertCircle, ClipboardCheck, Download, FileJson, RefreshCw, Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

import type { ConfirmedMetricCoveragePacket, ConfirmedMetricCoverageRow } from '../types'

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
          {summary?.generated_at ? <Badge variant="outline">generated {new Date(summary.generated_at).toLocaleString()}</Badge> : null}
          {summary?.head ? <Badge variant="outline">head {summary.head}</Badge> : null}
          {summary?.canonical_labels_mutated === false ? <Badge variant="outline">canonical labels unchanged</Badge> : null}
        </div>

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

        {packet?.warnings?.length ? (
          <div className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">
            {packet.warnings.join(' ')}
          </div>
        ) : null}

        {rows.length > 0 ? (
          <div className="space-y-3">
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

            <div className="overflow-x-auto rounded-lg border border-border/60">
              <Table className="min-w-[1180px] table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[70px]">Ticker</TableHead>
                    <TableHead className="w-[190px]">Document</TableHead>
                    <TableHead className="w-[120px]">Period</TableHead>
                    <TableHead className="w-[145px]">Metric</TableHead>
                    <TableHead className="w-[135px]">Expected</TableHead>
                    <TableHead className="w-[190px]">Classification</TableHead>
                    <TableHead className="w-[270px]">Source evidence</TableHead>
                    <TableHead className="w-[260px]">Recommendation</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRows.map((row) => (
                    <TableRow key={`${row.fixture_id}:${row.metric_name}`}>
                      <TableCell className="whitespace-normal align-top font-mono text-xs">{row.ticker || '-'}</TableCell>
                      <TableCell className="whitespace-normal break-all align-top font-mono text-xs" title={row.document_id}>{row.fixture || row.document_id}</TableCell>
                      <TableCell className="whitespace-normal align-top text-xs text-muted-foreground">
                        {row.period.period_type || '-'} {row.period.period_end || ''}
                      </TableCell>
                      <TableCell className="whitespace-normal break-words align-top font-mono text-xs">{row.metric_name}</TableCell>
                      <TableCell className="whitespace-normal break-words align-top text-xs">{formatExpected(row)}</TableCell>
                      <TableCell className="whitespace-normal align-top">
                        <Badge className={WRAPPING_BADGE_CLASS} variant={classificationVariant(row.classification)}>{row.classification}</Badge>
                      </TableCell>
                      <TableCell className="whitespace-normal break-words align-top text-xs text-muted-foreground">
                        <div className="flex flex-wrap gap-1">
                          <Badge className={WRAPPING_BADGE_CLASS} variant={row.source_pdf_status === 'present' ? 'outline' : 'critical'}>{row.source_pdf_status}</Badge>
                          <Badge className={WRAPPING_BADGE_CLASS} variant="outline">{row.source_evidence_status}</Badge>
                          {row.source_page ? <Badge className={WRAPPING_BADGE_CLASS} variant="outline">p{row.source_page}</Badge> : null}
                          {row.source_table ? <Badge className={WRAPPING_BADGE_CLASS} variant="outline">table {row.source_table}</Badge> : null}
                        </div>
                        {row.source_pdf_path ? <div className="mt-1 break-all font-mono" title={row.source_pdf_path}>{row.source_pdf_path}</div> : null}
                        {row.source_row ? <div className="mt-1 whitespace-normal break-words" title={row.source_row}>{row.source_row}</div> : null}
                      </TableCell>
                      <TableCell className="whitespace-normal break-words align-top text-xs text-muted-foreground">
                        <div className="break-words font-mono">{row.recommended_action}</div>
                        <div className="break-words">{row.review_status} / {row.production_metric_tier}</div>
                        {row.ambiguity_reason ? <div className="break-words">ambiguity: {row.ambiguity_reason}</div> : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
