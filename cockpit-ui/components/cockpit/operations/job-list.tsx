'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Loader2, CheckCircle2, XCircle, Clock, Ban, RefreshCw } from 'lucide-react'
import type { OpsJobRun } from '@/lib/ops-types'
import { listOpsJobs } from '@/lib/ops-api-client'
import { useJobStream } from '@/hooks/use-job-stream'
import { cn } from '@/lib/utils'

interface JobListProps {
  onSelectJob: (jobId: string) => void
  selectedJobId: string | null
}

const STATUS_CONFIG: Record<string, {
  variant: 'default' | 'secondary' | 'destructive' | 'outline'
  icon: typeof Clock
  label: string
}> = {
  pending: { variant: 'outline', icon: Clock, label: 'Pending' },
  running: { variant: 'default', icon: Loader2, label: 'Running' },
  succeeded: { variant: 'secondary', icon: CheckCircle2, label: 'Done' },
  failed: { variant: 'destructive', icon: XCircle, label: 'Failed' },
  cancelled: { variant: 'outline', icon: Ban, label: 'Cancelled' },
}

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

function JobRowSkeleton() {
  return (
    <div className="rounded-md px-3 py-2.5 animate-pulse">
      <div className="flex items-center justify-between mb-1.5">
        <div className="h-3.5 bg-muted rounded w-2/3" />
        <div className="h-4 bg-muted rounded w-16" />
      </div>
      <div className="flex items-center justify-between">
        <div className="h-3 bg-muted rounded w-1/3" />
        <div className="h-3 bg-muted rounded w-1/4" />
      </div>
    </div>
  )
}

export function JobList({ onSelectJob, selectedJobId }: JobListProps) {
  const [jobs, setJobs] = useState<OpsJobRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { activeJobs, connected } = useJobStream()

  const fetchJobs = useCallback(async () => {
    try {
      const resp = await listOpsJobs({ limit: 50 })
      setJobs(resp.items)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  // Refresh when active jobs change
  useEffect(() => {
    if (activeJobs.size > 0) {
      fetchJobs()
    }
  }, [activeJobs, fetchJobs])

  // Merge SSE updates into the job list
  const mergedJobs = jobs.map((job) => {
    const liveUpdate = activeJobs.get(job.job_id)
    return liveUpdate ?? job
  })

  const progressPct = (job: OpsJobRun): number => {
    if (job.total_items === 0) return 0
    return Math.round((job.succeeded_items / job.total_items) * 100)
  }

  const activeCount = mergedJobs.filter(
    (j) => j.status === 'running' || j.status === 'pending',
  ).length

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Jobs</CardTitle>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'inline-block h-2 w-2 rounded-full transition-colors',
                connected ? 'bg-green-500' : 'bg-muted-foreground/30',
              )}
              title={connected ? 'Live updates connected' : 'Live updates disconnected'}
              role="status"
              aria-label={connected ? 'Live updates connected' : 'Live updates disconnected'}
            />
            <Badge variant="outline" className="text-xs tabular-nums">
              {activeCount} active
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {loading && (
          <div className="space-y-1 p-2">
            <JobRowSkeleton />
            <JobRowSkeleton />
            <JobRowSkeleton />
          </div>
        )}
        {error && (
          <div className="p-4 flex flex-col items-center gap-2">
            <p className="text-xs text-destructive">{error}</p>
            <Button variant="ghost" size="sm" onClick={fetchJobs} className="h-7 text-xs gap-1.5">
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          </div>
        )}
        {!loading && !error && mergedJobs.length === 0 && (
          <div className="p-6 text-center">
            <Clock className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
            <p className="text-xs text-muted-foreground">No jobs recorded yet.</p>
            <p className="text-xs text-muted-foreground/60 mt-0.5">
              Jobs appear here when extraction or backfill runs.
            </p>
          </div>
        )}
        {!loading && !error && mergedJobs.length > 0 && (
          <ScrollArea className="h-[400px]">
            <div className="space-y-0.5 p-2" role="listbox" aria-label="Job list">
              {mergedJobs.map((job) => {
                const config = STATUS_CONFIG[job.status] ?? STATUS_CONFIG.pending
                const StatusIcon = config.icon
                const isSelected = selectedJobId === job.job_id

                return (
                  <button
                    key={job.job_id}
                    onClick={() => onSelectJob(job.job_id)}
                    role="option"
                    aria-selected={isSelected}
                    className={cn(
                      'w-full text-left rounded-md px-3 py-2.5 text-xs cursor-pointer',
                      'transition-colors duration-150',
                      'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
                      isSelected && 'bg-muted border border-border',
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium truncate mr-2">{job.title}</span>
                      <Badge variant={config.variant} className="text-[11px] shrink-0 gap-1">
                        <StatusIcon className={cn('h-3 w-3', job.status === 'running' && 'animate-spin')} />
                        {config.label}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span className="tabular-nums">
                        {job.job_type}
                        {job.ticker ? ` \u00B7 ${job.ticker}` : ''}
                      </span>
                      <span className="tabular-nums">
                        {job.status === 'running'
                          ? job.phase ?? 'running'
                          : formatElapsed(job.elapsed_ms)}{' '}
                        \u00B7 {formatTimestamp(job.queued_at)}
                      </span>
                    </div>
                    {job.status === 'running' && job.total_items > 0 && (
                      <Progress value={progressPct(job)} className="mt-1.5 h-1" />
                    )}
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
