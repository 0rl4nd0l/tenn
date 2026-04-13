import type { ExtractionReviewRunStatusResponse } from '@/lib/cockpit-types'
import { Badge } from '@/components/ui/badge'

import { formatDuration, formatMethodLabel, runStatusVariant } from './utils'

type ExtractionRunStatusCardProps = {
  documentId: string
  runId: string
  status?: ExtractionReviewRunStatusResponse
  title?: string | null
  fallbackMethod: string
}

export function ExtractionRunStatusCard({
  documentId,
  runId,
  status,
  title,
  fallbackMethod,
}: ExtractionRunStatusCardProps) {
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
