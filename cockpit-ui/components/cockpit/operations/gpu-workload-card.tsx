'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Flame, MemoryStick, FileSearch, ArrowRight, Loader2 } from 'lucide-react'
import type { ServiceHealth } from '@/lib/cockpit-types'
import type { OpsJobRun } from '@/lib/ops-types'
import type { GpuRecord } from '@/components/cockpit/gpu-activity-dialog'
import { withApiKey } from '@/lib/api-client'
import { listActiveOpsJobs } from '@/lib/ops-api-client'
import { cn } from '@/lib/utils'

interface GpuWorkloadCardProps {
  gpuHealth: ServiceHealth | null
  gpuProcesses: GpuRecord[]
}

interface ExtractionRun {
  runId: string | null
  documentId: string | null
  ticker: string | null
  title: string | null
  requestedMethod: string | null
}

function parseExtractionRuns(configPayload: Record<string, unknown> | null): ExtractionRun[] {
  if (!configPayload) return []
  const runs = Array.isArray(configPayload.extraction_active_runs)
    ? configPayload.extraction_active_runs
    : []
  return runs.flatMap((entry) => {
    if (!entry || typeof entry !== 'object') return []
    const run = entry as Record<string, unknown>
    return [{
      runId: typeof run.run_id === 'string' ? run.run_id : null,
      documentId: typeof run.document_id === 'string' ? run.document_id : null,
      ticker: typeof run.ticker === 'string' ? run.ticker : null,
      title: typeof run.title === 'string' ? run.title : null,
      requestedMethod: typeof run.requested_method === 'string' ? run.requested_method : null,
    }]
  })
}

export function GpuWorkloadCard({ gpuHealth, gpuProcesses }: GpuWorkloadCardProps) {
  const [activeJobs, setActiveJobs] = useState<OpsJobRun[]>([])
  const [extractionRuns, setExtractionRuns] = useState<ExtractionRun[]>([])

  const gpus = Array.isArray(gpuHealth?.details?.gpus)
    ? (gpuHealth!.details!.gpus as Array<Record<string, unknown>>)
    : []
  const firstGpu = gpus[0]
  const utilPct = typeof firstGpu?.util_percent === 'number' ? firstGpu.util_percent : null
  const memUsed = typeof firstGpu?.mem_used_mib === 'number' ? Math.round(firstGpu.mem_used_mib as number) : null
  const memTotal = typeof firstGpu?.mem_total_mib === 'number' ? Math.round(firstGpu.mem_total_mib as number) : null
  const showPanel = (utilPct !== null && utilPct > 0) || gpuProcesses.length > 0

  const fetchWorkloadContext = useCallback(async () => {
    // Fetch both active ops jobs and extraction activity in parallel
    const [opsResult, configResult] = await Promise.allSettled([
      listActiveOpsJobs(),
      fetch('/api/cockpit/config', {
        cache: 'no-store',
        headers: withApiKey(),
      }).then((r) =>
        r.ok ? (r.json() as Promise<Record<string, unknown>>) : null,
      ),
    ])

    if (opsResult.status === 'fulfilled') {
      setActiveJobs(opsResult.value.items)
    }
    if (configResult.status === 'fulfilled' && configResult.value) {
      setExtractionRuns(parseExtractionRuns(configResult.value))
    }
  }, [])

  // Fetch workload context when GPU becomes active
  useEffect(() => {
    if (showPanel) {
      fetchWorkloadContext()
      const interval = setInterval(fetchWorkloadContext, 10_000)
      return () => clearInterval(interval)
    }
  }, [showPanel, fetchWorkloadContext])

  if (!showPanel) return null

  // Identify GPU-bound jobs (extraction, backfill with extraction, embedding)
  const gpuJobs = activeJobs.filter(
    (j) => j.status === 'running' && ['extraction', 'backfill', 'embedding'].includes(j.job_type),
  )

  // Merge: extraction activity runs that don't match an ops job (covers untracked runs)
  const trackedRunIds = new Set(gpuJobs.map((j) => j.job_id))
  const untrackedRuns = extractionRuns.filter((r) => r.runId && !trackedRunIds.has(r.runId))

  const hasWorkload = gpuJobs.length > 0 || untrackedRuns.length > 0

  return (
    <Card className={cn(
      'border-l-4',
      utilPct !== null && utilPct >= 90
        ? 'border-l-red-500 bg-red-500/5'
        : utilPct !== null && utilPct >= 50
          ? 'border-l-yellow-500 bg-yellow-500/5'
          : 'border-l-green-500 bg-green-500/5',
    )}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Flame className={cn(
            'h-4 w-4',
            utilPct !== null && utilPct >= 90 ? 'text-red-500' :
            utilPct !== null && utilPct >= 50 ? 'text-yellow-500' : 'text-green-500',
          )} />
          GPU Activity
          {utilPct !== null && (
            <Badge
              variant={utilPct >= 90 ? 'destructive' : 'outline'}
              className="text-xs tabular-nums font-mono ml-auto"
            >
              {Math.round(utilPct)}% util
            </Badge>
          )}
          {memUsed !== null && memTotal !== null && (
            <Badge variant="outline" className="text-xs tabular-nums font-mono gap-1">
              <MemoryStick className="h-3 w-3" />
              {memUsed}/{memTotal} MiB
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        {/* Active workload — what jobs are driving the GPU */}
        {hasWorkload && (
          <div>
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5 font-medium">
              Active Workload
            </p>
            <div className="space-y-1.5">
              {gpuJobs.map((job) => (
                <div
                  key={job.job_id}
                  className="rounded-md border border-border/60 bg-background/60 p-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                    <Badge variant="secondary" className="text-[10px] uppercase tracking-wider shrink-0">
                      {job.job_type}
                    </Badge>
                    <span className="font-medium truncate">{job.title}</span>
                    {job.ticker && (
                      <Badge variant="outline" className="text-[10px] shrink-0">{job.ticker}</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-muted-foreground">
                    {job.phase && (
                      <span className="flex items-center gap-1">
                        <ArrowRight className="h-3 w-3" />
                        {job.phase}
                      </span>
                    )}
                    {job.total_items > 0 && (
                      <span className="tabular-nums">
                        {job.succeeded_items}/{job.total_items} items
                      </span>
                    )}
                    {job.current_item_label && (
                      <span className="truncate">{job.current_item_label}</span>
                    )}
                  </div>
                </div>
              ))}
              {untrackedRuns.map((run) => (
                <div
                  key={run.runId}
                  className="rounded-md border border-border/60 bg-background/60 p-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                    <Badge variant="secondary" className="text-[10px] uppercase tracking-wider shrink-0">
                      extraction
                    </Badge>
                    <span className="font-medium truncate">
                      {run.title || run.documentId || 'Extraction run'}
                    </span>
                    {run.ticker && (
                      <Badge variant="outline" className="text-[10px] shrink-0">{run.ticker}</Badge>
                    )}
                  </div>
                  {run.requestedMethod && (
                    <div className="flex items-center gap-2 mt-1 text-muted-foreground">
                      <FileSearch className="h-3 w-3" />
                      <span>{run.requestedMethod}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GPU processes — system-level view */}
        {gpuProcesses.length > 0 && (
          <>
            {hasWorkload && <Separator />}
            <div>
              <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5 font-medium">
                GPU Processes
              </p>
              <div className="space-y-1.5">
                {gpuProcesses.map((proc, idx) => {
                  const taskLabel = typeof proc.task_label === 'string' ? proc.task_label : 'GPU task'
                  const processName = typeof proc.process_name === 'string' ? proc.process_name : 'process'
                  const command = typeof proc.command === 'string' ? proc.command : null
                  const pid = typeof proc.pid === 'number' ? proc.pid : null
                  const procMem = typeof proc.used_gpu_memory_mib === 'number'
                    ? `${Math.round(proc.used_gpu_memory_mib as number)} MiB`
                    : null

                  return (
                    <div
                      key={`${pid ?? idx}`}
                      className="rounded-md border border-border/60 bg-background/60 p-2 font-mono text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-[10px] uppercase tracking-wider">
                          {taskLabel}
                        </Badge>
                        <span className="text-foreground font-medium">{processName}</span>
                        {pid !== null && (
                          <span className="text-muted-foreground">PID {pid}</span>
                        )}
                        {procMem && (
                          <span className="text-muted-foreground ml-auto tabular-nums">{procMem}</span>
                        )}
                      </div>
                      {command && (
                        <p className="text-[11px] text-muted-foreground/70 break-all line-clamp-2 mt-1">
                          {command}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}

        {gpuProcesses.length === 0 && !hasWorkload && (
          <p className="text-xs text-muted-foreground">
            GPU is active but no compute processes or tracked jobs were found.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
