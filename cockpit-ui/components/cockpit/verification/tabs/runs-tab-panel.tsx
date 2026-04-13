import { Activity, BarChart3 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { ExtractionReviewRunStatusResponse } from '@/lib/cockpit-types'

import { ExtractionRunStatusCard } from '../extraction-run-status-card'
import { formatDuration, formatTimestamp, runStatusVariant } from '../utils'

type RunStatusCardEntry = {
  documentId: string
  runId: string
  status?: ExtractionReviewRunStatusResponse
  title?: string | null
  fallbackMethod: string
}

type RunsTabPanelProps = {
  attachActiveRuns: boolean
  activeMonitorNotice: string | null
  statusCards: RunStatusCardEntry[]
  runStatusLoading: boolean
  activeRunId: string
  runStatus: ExtractionReviewRunStatusResponse | null
}

export function RunsTabPanel({
  attachActiveRuns,
  activeMonitorNotice,
  statusCards,
  runStatusLoading,
  activeRunId,
  runStatus,
}: RunsTabPanelProps) {
  return (
    <div className="space-y-6">
      {attachActiveRuns ? (
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
            {activeMonitorNotice ? (
              <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
                {activeMonitorNotice}
              </div>
            ) : null}

            {statusCards.length > 0 ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {statusCards.map((card) => (
                  <ExtractionRunStatusCard
                    key={card.runId}
                    documentId={card.documentId}
                    runId={card.runId}
                    status={card.status}
                    title={card.title}
                    fallbackMethod={card.fallbackMethod}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-3 text-sm text-muted-foreground">
                Waiting for backend run metadata...
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {!attachActiveRuns && statusCards.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Selected Run Status</CardTitle>
            <CardDescription>
              Current extraction status for the review set and selected historical run.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 lg:grid-cols-2">
              {statusCards.map((card) => (
                <ExtractionRunStatusCard
                  key={card.runId}
                  documentId={card.documentId}
                  runId={card.runId}
                  status={card.status}
                  title={card.title}
                  fallbackMethod={card.fallbackMethod}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {activeRunId ? (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  Run Timeline
                </CardTitle>
                <CardDescription>
                  Absolute timestamps and stage timings for run <code>{activeRunId}</code>
                </CardDescription>
              </div>
              {runStatusLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  Loading timeline...
                </div>
              ) : null}
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

                {((runStatus.summary.warnings?.length ?? 0) > 0 || (runStatus.summary.errors?.length ?? 0) > 0) ? (
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
                ) : null}

                <div className="space-y-2">
                  {runStatus.events.map((event, index) => (
                    <details key={`${event.stage}-${event.timestamp}-${index}`} className="rounded-lg border border-border/60 bg-muted/10 p-3">
                      <summary className="cursor-pointer list-none text-sm">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline">{event.stage}</Badge>
                          <Badge variant={runStatusVariant(event.status)}>
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
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Run Timeline</CardTitle>
            <CardDescription>
              Load a review session or inspect a historical run to see stage timings, warnings, and errors here.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
              No active run timeline is available yet.
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
