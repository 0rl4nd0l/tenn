'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import {
  X, RefreshCw, CheckCircle2, XCircle, AlertTriangle,
  Clock, Loader2, FileText, ArrowRight,
} from 'lucide-react'
import type { OpsJobRun, OpsJobEvent, OpsJobArtifact } from '@/lib/ops-types'
import { getOpsJob, getOpsJobEvents, getOpsJobArtifacts } from '@/lib/ops-api-client'
import { stopActionJob } from '@/lib/api-client'
import { useJobStream } from '@/hooks/use-job-stream'
import { cn } from '@/lib/utils'

interface JobDetailPanelProps {
  jobId: string
  onClose: () => void
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

const EVENT_ICON: Record<string, typeof Clock> = {
  'job.created': Clock,
  'job.started': ArrowRight,
  'job.phase_changed': ArrowRight,
  'job.progress': Loader2,
  'job.item_started': ArrowRight,
  'job.item_succeeded': CheckCircle2,
  'job.item_failed': XCircle,
  'job.warning': AlertTriangle,
  'job.completed': CheckCircle2,
  'job.failed': XCircle,
  'job.cancelled': XCircle,
}

const EVENT_COLOR: Record<string, string> = {
  'job.created': 'text-blue-400',
  'job.started': 'text-green-400',
  'job.phase_changed': 'text-cyan-400',
  'job.progress': 'text-muted-foreground',
  'job.item_started': 'text-muted-foreground',
  'job.item_succeeded': 'text-green-400',
  'job.item_failed': 'text-red-400',
  'job.warning': 'text-yellow-400',
  'job.completed': 'text-green-500',
  'job.failed': 'text-red-500',
  'job.cancelled': 'text-muted-foreground',
}

function DetailSkeleton() {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="h-4 bg-muted rounded w-2/3 animate-pulse" />
        <div className="flex gap-2 mt-2">
          <div className="h-5 bg-muted rounded w-16 animate-pulse" />
          <div className="h-5 bg-muted rounded w-16 animate-pulse" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-1">
              <div className="h-4 bg-muted rounded w-12 animate-pulse" />
              <div className="h-3 bg-muted rounded w-10 animate-pulse" />
            </div>
          ))}
        </div>
        <div className="h-1.5 bg-muted rounded animate-pulse" />
        <div className="space-y-1">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-3.5 bg-muted rounded animate-pulse" style={{ width: `${70 + i * 5}%` }} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function jobSupportsCancellation(job: OpsJobRun): boolean {
  if (job.status !== 'running' && job.status !== 'pending') {
    return false
  }

  if (job.job_family === 'cockpit_action' || job.job_family === 'marketplace') {
    return true
  }

  if (
    (job.job_family === 'pipeline' || job.job_family === 'celery') &&
    (job.job_type === 'extraction' || job.job_type === 'backfill')
  ) {
    return Boolean(job.metadata?.supports_cancellation)
  }

  return false
}

export function JobDetailPanel({ jobId, onClose }: JobDetailPanelProps) {
  const [job, setJob] = useState<OpsJobRun | null>(null)
  const [events, setEvents] = useState<OpsJobEvent[]>([])
  const [artifacts, setArtifacts] = useState<OpsJobArtifact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cancelMessage, setCancelMessage] = useState<string | null>(null)
  const [isCancelling, setIsCancelling] = useState(false)
  const eventsEndRef = useRef<HTMLDivElement>(null)

  const { recentEvents } = useJobStream({
    jobId,
    enabled: job?.status === 'running' || job?.status === 'pending',
  })

  const fetchData = useCallback(async () => {
    try {
      const [jobData, eventsData, artifactsData] = await Promise.all([
        getOpsJob(jobId),
        getOpsJobEvents(jobId),
        getOpsJobArtifacts(jobId),
      ])
      setJob(jobData)
      setEvents(eventsData.items)
      setArtifacts(artifactsData.items)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load job')
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    setCancelMessage(null)
    setIsCancelling(false)
  }, [jobId])

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events, recentEvents])

  // Refresh when we get SSE events for this job
  useEffect(() => {
    if (recentEvents.length > 0) {
      fetchData()
    }
  }, [recentEvents, fetchData])
  const canCancel = job ? jobSupportsCancellation(job) : false

  const handleCancel = useCallback(async () => {
    if (!job || !canCancel || isCancelling) {
      return
    }

    setIsCancelling(true)
    setCancelMessage(null)
    try {
      const response = await stopActionJob(job.job_id)
      setCancelMessage(
        response.status === 'cancelling'
          ? 'Cancellation requested. The operation will stop at the next safe checkpoint.'
          : `Operation status: ${response.status}`,
      )
      setJob((prev) => (
        prev
          ? {
              ...prev,
              phase: response.status === 'cancelling' ? 'cancelling' : prev.phase,
            }
          : prev
      ))
      await fetchData()
    } catch (err: unknown) {
      setCancelMessage(err instanceof Error ? err.message : 'Failed to cancel operation')
    } finally {
      setIsCancelling(false)
    }
  }, [canCancel, fetchData, isCancelling, job])

  if (loading) return <DetailSkeleton />

  if (error || !job) {
    return (
      <Card className="h-full">
        <CardContent className="flex flex-col items-center justify-center h-full gap-2 p-8">
          <XCircle className="h-8 w-8 text-destructive/60" />
          <p className="text-xs text-destructive">{error ?? 'Job not found'}</p>
          <Button variant="ghost" size="sm" onClick={fetchData} className="h-7 text-xs gap-1.5">
            <RefreshCw className="h-3 w-3" />
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  const progressPct = job.total_items > 0
    ? Math.round((job.succeeded_items / job.total_items) * 100)
    : 0

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2 shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium truncate">{job.title}</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-7 w-7 shrink-0"
            aria-label="Close job details"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-1">
          <Badge variant="outline" className="text-[11px]">{job.job_type}</Badge>
          <Badge
            variant={
              job.status === 'succeeded' ? 'secondary' :
              job.status === 'failed' ? 'destructive' :
              job.status === 'running' ? 'default' : 'outline'
            }
            className="text-[11px] gap-1"
          >
            {job.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
            {job.status === 'succeeded' && <CheckCircle2 className="h-3 w-3" />}
            {job.status === 'failed' && <XCircle className="h-3 w-3" />}
            {job.status}
          </Badge>
          {job.ticker && <Badge variant="outline" className="text-[11px]">{job.ticker}</Badge>}
          {job.phase && job.status === 'running' && (
            <Badge variant="outline" className="text-[11px]">{job.phase}</Badge>
          )}
        </div>
        {canCancel && (
          <div className="mt-2 flex items-center gap-2">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              disabled={isCancelling}
              className="h-7 text-xs"
            >
              {isCancelling ? 'Cancelling…' : 'Cancel Operation'}
            </Button>
            {cancelMessage && (
              <p className="text-[11px] text-muted-foreground">{cancelMessage}</p>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden flex flex-col gap-3 pt-2">
        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground shrink-0">
          <div>
            <span className="block font-medium text-foreground tabular-nums">
              {formatElapsed(job.elapsed_ms)}
            </span>
            elapsed
          </div>
          <div>
            <span className="block font-medium text-foreground tabular-nums">
              {job.succeeded_items}/{job.total_items}
            </span>
            completed
          </div>
          <div>
            <span className="block font-medium text-foreground tabular-nums">
              {job.failed_items > 0 ? (
                <span className="text-destructive">{job.failed_items}</span>
              ) : (
                '0'
              )}
              {job.warning_count > 0 && (
                <span className="text-yellow-500 ml-1">
                  <AlertTriangle className="inline h-3 w-3 mr-0.5" />
                  {job.warning_count}
                </span>
              )}
            </span>
            failed
          </div>
        </div>

        {/* Progress bar */}
        {job.total_items > 0 && (
          <div className="shrink-0">
            <Progress value={progressPct} className="h-1.5" />
            <div className="flex justify-between text-[11px] text-muted-foreground mt-0.5 tabular-nums">
              <span>{progressPct}%</span>
              {job.current_item_label && (
                <span className="truncate ml-2">{job.current_item_label}</span>
              )}
            </div>
          </div>
        )}

        {/* Summary */}
        {job.summary && (
          <div className="text-xs p-2 rounded bg-muted shrink-0 border border-border/50">
            {job.summary}
          </div>
        )}

        {/* Events timeline */}
        <div className="flex-1 overflow-hidden">
          <h4 className="text-xs font-medium mb-1">Events</h4>
          <ScrollArea className="h-[250px]">
            <div className="space-y-0.5 font-mono text-[11px]" role="log" aria-label="Job events">
              {events.map((ev) => {
                const EvIcon = EVENT_ICON[ev.event_type] ?? ArrowRight
                const color = EVENT_COLOR[ev.event_type] ?? 'text-muted-foreground'
                return (
                  <div key={ev.event_id} className="flex items-start gap-1.5 py-0.5">
                    <span className="text-muted-foreground shrink-0 w-[3.5rem] tabular-nums">
                      {formatTimestamp(ev.timestamp)}
                    </span>
                    <EvIcon className={cn('h-3 w-3 shrink-0 mt-0.5', color)} aria-hidden />
                    <span className={cn('shrink-0 w-28', color)}>
                      {ev.event_type.replace('job.', '')}
                    </span>
                    <span className="truncate text-muted-foreground">{ev.message}</span>
                  </div>
                )
              })}
              <div ref={eventsEndRef} />
            </div>
          </ScrollArea>
        </div>

        {/* Artifacts */}
        {artifacts.length > 0 && (
          <div className="shrink-0">
            <h4 className="text-xs font-medium mb-1">Artifacts</h4>
            <div className="space-y-1">
              {artifacts.map((art) => (
                <div key={art.artifact_id} className="text-xs flex items-center gap-2">
                  <FileText className="h-3 w-3 text-muted-foreground shrink-0" aria-hidden />
                  <Badge variant="outline" className="text-[11px]">{art.artifact_type}</Badge>
                  <span className="truncate">{art.artifact_label}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
