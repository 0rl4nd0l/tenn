import { AlertCircle, FileJson, Play } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { ExtractionMethod } from '@/lib/cockpit-types'

import type { RealGoldEvalResponse } from '../types'
import { formatMethodLabel, isReviewableExtractionStatus } from '../utils'

type GoldEvalTabPanelProps = {
  goldLimit: string
  goldEvalLoading: boolean
  goldEvalError: string | null
  goldEval: RealGoldEvalResponse | null
  extractionMethod: ExtractionMethod
  onGoldLimitChange: (value: string) => void
  onRunGoldEval: () => void
  onExportGoldEvalJson: () => void
  onOpenReviewSession: (sessionId: string) => void
}

export function GoldEvalTabPanel({
  goldLimit,
  goldEvalLoading,
  goldEvalError,
  goldEval,
  extractionMethod,
  onGoldLimitChange,
  onRunGoldEval,
  onExportGoldEvalJson,
  onOpenReviewSession,
}: GoldEvalTabPanelProps) {
  const summary = goldEval?.summary ?? null

  return (
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
              onChange={(event) => onGoldLimitChange(event.target.value)}
              placeholder="0 = full corpus"
              className="font-mono"
            />
          </Field>
          <div className="flex gap-2">
            <Button onClick={onRunGoldEval} disabled={goldEvalLoading}>
              <Play className="mr-2 h-4 w-4" />
              Run Gold Set
            </Button>
            <Button variant="outline" onClick={onExportGoldEvalJson} disabled={!goldEval}>
              <FileJson className="mr-2 h-4 w-4" />
              Export Gold Eval
            </Button>
          </div>
        </div>

        {goldEvalLoading ? (
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            Real-Gold evaluation is running in the backend. Watch the progress log for task status and polling updates.
          </div>
        ) : null}

        {goldEvalError ? (
          <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {goldEvalError}
          </div>
        ) : null}

        {summary && goldEval ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="text-3xl font-semibold text-primary">{summary.total_documents}</p>
                <p className="text-xs text-muted-foreground">Documents</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="text-3xl font-semibold text-primary">{(summary.total_accuracy * 100).toFixed(1)}%</p>
                <p className="text-xs text-muted-foreground">Metric Accuracy</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="text-3xl font-semibold text-primary">{(summary.context_accuracy * 100).toFixed(1)}%</p>
                <p className="text-xs text-muted-foreground">Context Accuracy</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="text-3xl font-semibold text-primary">{summary.trust_matches_expected}/{summary.total_documents}</p>
                <p className="text-xs text-muted-foreground">Trust Matches</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              <Badge variant="outline">trusted {summary.trust_distribution.trusted ?? 0}</Badge>
              <Badge variant="outline">abstain {summary.trust_distribution.abstain ?? 0}</Badge>
              <Badge variant="outline">quarantine {summary.trust_distribution.quarantine ?? 0}</Badge>
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
                    <TableHead>Review</TableHead>
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
                        <TableCell className="text-xs text-muted-foreground">
                          {doc.review_session_id ? (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => onOpenReviewSession(doc.review_session_id!)}
                            >
                              Open Review{doc.review_item_count ? ` (${doc.review_item_count})` : ''}
                            </Button>
                          ) : (
                            doc.review_reason || 'No flagged metric review session'
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
