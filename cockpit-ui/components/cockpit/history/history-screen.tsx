'use client'

import { useState, useCallback, Fragment, useEffect, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { History, Play, ChevronDown, ChevronRight, Clock, CheckCircle2, XCircle, Loader2, RefreshCw } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listDocuments, getQueueStatus, rerunJob } from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import { toast } from 'sonner'
import type { Job } from '@/lib/cockpit-types'
import { cn } from '@/lib/utils'

type HistoryRowKind = 'job_execution' | 'document_inventory' | 'queue_summary'

interface HistoryRow {
  id: string
  action: string
  args: Record<string, unknown>
  status: Job['status']
  startedAt: Date | null
  completedAt?: Date | null
  output?: string
  error?: string
  kind: HistoryRowKind
  statusLabel?: string
  canRerun: boolean
}

function getStatusIcon(job: HistoryRow) {
  if (job.kind === 'document_inventory') {
    return <History className="h-4 w-4 text-muted-foreground" />
  }
  if (job.kind === 'queue_summary') {
    return <Clock className="h-4 w-4 text-muted-foreground" />
  }

  const status = job.status
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-[oklch(0.65_0.2_145)]" />
    case 'failed':
      return <XCircle className="h-4 w-4 text-[oklch(0.55_0.2_25)]" />
    case 'running':
      return <Loader2 className="h-4 w-4 text-primary animate-spin" />
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />
  }
}

function getStatusBadgeVariant(job: HistoryRow): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (job.kind !== 'job_execution') {
    return 'outline'
  }

  const status = job.status
  switch (status) {
    case 'completed':
      return 'default'
    case 'failed':
      return 'destructive'
    case 'running':
      return 'secondary'
    default:
      return 'outline'
  }
}

function formatDuration(startedAt: Date | null, completedAt?: Date | null): string {
  if (!startedAt) return 'Unknown'

  const end = completedAt || new Date()
  const durationMs = end.getTime() - startedAt.getTime()
  
  if (durationMs < 1000) return `${durationMs}ms`
  if (durationMs < 60000) return `${(durationMs / 1000).toFixed(1)}s`
  return `${Math.floor(durationMs / 60000)}m ${Math.floor((durationMs % 60000) / 1000)}s`
}

function formatTimeAgo(date: Date | null): string {
  if (!date) return 'DATA_MISSING'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  
  if (diffMs < 60000) return 'Just now'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`
  return `${Math.floor(diffMs / 86400000)}d ago`
}

interface JobRowProps {
  job: HistoryRow
  isOpen: boolean
  onToggle: () => void
  onRerun: (job: HistoryRow) => void
}

function JobRow({ job, isOpen, onToggle, onRerun }: JobRowProps) {
  return (
    <Fragment>
      <TableRow 
        className={cn(
          'cursor-pointer hover:bg-muted/50',
          isOpen && 'bg-muted/30'
        )}
        onClick={onToggle}
      >
        <TableCell>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
            {isOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        </TableCell>
        <TableCell className="font-mono text-xs truncate max-w-[100px]" title={job.id}>{job.id}</TableCell>
        <TableCell className="truncate max-w-[150px]" title={job.action}>{job.action}</TableCell>
        <TableCell className="font-mono text-xs text-muted-foreground truncate max-w-[200px]" title={JSON.stringify(job.args)}>
          {JSON.stringify(job.args)}
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-2">
            {getStatusIcon(job)}
            <Badge variant={getStatusBadgeVariant(job)} className="text-[10px]">
              {job.statusLabel ?? job.status}
            </Badge>
          </div>
        </TableCell>
        <TableCell className="text-muted-foreground text-sm">
          {formatTimeAgo(job.startedAt)}
        </TableCell>
        <TableCell className="font-mono text-sm">
          {formatDuration(job.startedAt, job.completedAt)}
        </TableCell>
        <TableCell>
          {job.canRerun ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={(e) => { e.stopPropagation(); onRerun(job); }}
            >
              <Play className="h-3 w-3 mr-1" />
              Re-run
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">Read-only</span>
          )}
        </TableCell>
      </TableRow>
      {isOpen && (
        <TableRow>
          <TableCell colSpan={8} className="bg-muted/20 p-0">
            <div className="p-4 space-y-3">
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Full Arguments</p>
                <pre className="text-xs font-mono bg-muted p-2 rounded overflow-x-auto">
                  {JSON.stringify(job.args, null, 2)}
                </pre>
              </div>
              {job.output && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Output</p>
                  <pre className="text-xs font-mono bg-muted p-2 rounded overflow-x-auto text-[oklch(0.65_0.2_145)]">
                    {job.output}
                  </pre>
                </div>
              )}
              {job.error && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Error</p>
                  <pre className="text-xs font-mono bg-muted p-2 rounded overflow-x-auto text-[oklch(0.55_0.2_25)]">
                    {job.error}
                  </pre>
                </div>
              )}
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>Execution time: {job.startedAt ? job.startedAt.toLocaleString() : 'DATA_MISSING'}</span>
                {job.completedAt && (
                  <span>Completed: {job.completedAt.toLocaleString()}</span>
                )}
              </div>
            </div>
          </TableCell>
        </TableRow>
      )}
    </Fragment>
  )
}

function mapDocumentToHistoryRow(doc: Record<string, unknown>, index: number): HistoryRow {
  const id = (doc.id as string) ?? `doc-${index}`
  const title = (doc.title as string) ?? (doc.filename as string) ?? 'Unknown document'
  const executionTimestamp = doc.created_at ?? doc.createdAt ?? doc.uploaded_at
  const startedAt = parseTimestamp(executionTimestamp)
  const docStatus = (doc.status as string) ?? 'completed'
  const baseArgs = {
    title,
    filename: doc.filename ?? title,
    published_at: doc.published_at ?? null,
    execution_timestamp: startedAt ? executionTimestamp : 'DATA_MISSING',
  }

  if (!startedAt) {
    return {
      id: String(id),
      action: 'Document Inventory',
      args: baseArgs,
      status: 'pending',
      startedAt: null,
      completedAt: null,
      output: `Document inventory only: ${title}. Execution timestamp DATA_MISSING.`,
      kind: 'document_inventory',
      statusLabel: 'inventory',
      canRerun: false,
    }
  }

  let status: Job['status'] = 'completed'
  if (docStatus === 'failed' || docStatus === 'error') {
    status = 'failed'
  } else if (docStatus === 'processing' || docStatus === 'running' || docStatus === 'pending') {
    status = 'running'
  } else if (docStatus === 'queued') {
    status = 'pending'
  }

  return {
    id: String(id),
    action: 'document_ingestion',
    args: baseArgs,
    status,
    startedAt,
    completedAt: status === 'completed' || status === 'failed' ? startedAt : undefined,
    output: status === 'completed' ? `Ingested: ${title}` : undefined,
    error: status === 'failed' ? (doc.error as string) ?? 'Processing failed' : undefined,
    kind: 'job_execution',
    canRerun: true,
  }
}

function parseTimestamp(value: unknown): Date | null {
  if (typeof value !== 'string' && typeof value !== 'number') return null

  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function HistoryScreen() {
  const { preferences } = useCockpitStore()
  const isIPhoneScale = preferences.iphoneScale
  const [hasHydrated, setHasHydrated] = useState(false)
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null)

  // Wait for hydration to avoid SSR/CSR mismatch
  useEffect(() => {
    setHasHydrated(true)
  }, [])

  const { 
    data: docs, 
    isLoading: isLoadingDocs, 
    isError: isErrorDocs,
    refetch: refetchDocs 
  } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
  })

  const { 
    data: queueStatus, 
    isLoading: isLoadingQueue,
    refetch: refetchQueue
  } = useQuery({
    queryKey: ['queue-status'],
    queryFn: getQueueStatus,
    refetchInterval: 5000,
  })

  const jobs = useMemo(() => {
    const docJobs: HistoryRow[] = Array.isArray(docs)
      ? docs.map((d, i) => mapDocumentToHistoryRow(d as Record<string, unknown>, i))
      : []

    // Merge queue-level counts as a summary row when no document-level data exists
    if (queueStatus && docJobs.length === 0) {
      const qs = queueStatus
      if (qs.pending > 0 || qs.active > 0 || qs.completed > 0 || qs.failed > 0) {
        docJobs.push({
          id: 'queue-summary',
          action: 'Queue Snapshot',
          args: { pending: qs.pending, active: qs.active, completed: qs.completed, failed: qs.failed },
          status: qs.active > 0 ? 'running' : 'pending',
          startedAt: null,
          completedAt: null,
          output: `Queue snapshot: ${qs.pending} pending, ${qs.active} active, ${qs.completed} completed, ${qs.failed} failed`,
          kind: 'queue_summary',
          statusLabel: qs.active > 0 ? 'active queue' : 'queue snapshot',
          canRerun: false,
        })
      }
    }
    return docJobs
  }, [docs, queueStatus])

  const loading = isLoadingDocs || isLoadingQueue
  const fetchError = isErrorDocs ? 'Failed to load document history.' : null

  const executionJobs = jobs.filter(j => j.kind === 'job_execution')
  const runningJobs = executionJobs.filter(j => j.status === 'running')
  const completedJobs = executionJobs.filter(j => j.status === 'completed')
  const failedJobs = executionJobs.filter(j => j.status === 'failed')

  const toggleJob = (jobId: string) => {
    setExpandedJobId(prev => prev === jobId ? null : jobId)
  }

  const handleRerun = useCallback(async (job: HistoryRow) => {
    if (!job.canRerun) return

    try {
      toast.info(`Re-running job "${job.action}"...`)
      await rerunJob({
        jobId: job.id,
        action: job.action,
        args: job.args,
      })
      toast.success(`Job "${job.action}" re-triggered successfully`)
      refetchDocs()
      refetchQueue()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Failed to re-run job: ${errorMsg}`)
    }
  }, [refetchDocs, refetchQueue])

  const handleRefresh = useCallback(() => {
    refetchDocs()
    refetchQueue()
  }, [refetchDocs, refetchQueue])

  if (!hasHydrated) return null

  return (
    <ScrollArea className="h-full">
      <div className={cn(
        "max-w-6xl mx-auto",
        isIPhoneScale ? "p-3 space-y-3" : "p-6 space-y-6"
      )}>
        {/* Summary Stats */}
        <div className={cn(
          "grid gap-4",
          isIPhoneScale ? "grid-cols-2" : "grid-cols-4"
        )}>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-mono font-semibold">{jobs.length}</p>
                <p className="text-xs text-muted-foreground">History Rows</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-mono font-semibold text-primary">{runningJobs.length}</p>
                <p className="text-xs text-muted-foreground">Running Jobs</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-mono font-semibold text-[oklch(0.65_0.2_145)]">{completedJobs.length}</p>
                <p className="text-xs text-muted-foreground">Completed Jobs</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-mono font-semibold text-[oklch(0.55_0.2_25)]">{failedJobs.length}</p>
                <p className="text-xs text-muted-foreground">Failed Jobs</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Jobs Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <History className="h-5 w-5 text-primary" />
                  History
                </CardTitle>
                <CardDescription>
                  View job executions and document inventory without inferred timestamps
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center gap-2"
              >
                <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {fetchError && jobs.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <History className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">{fetchError}</p>
              </div>
            ) : jobs.length === 0 && !loading ? (
              <div className="text-center py-12 text-muted-foreground">
                <History className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">No execution or document history is available yet.</p>
                <Button variant="outline" size="sm" className="mt-4" onClick={handleRefresh}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Load History
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[40px]"></TableHead>
                      <TableHead className="w-[100px]">Record ID</TableHead>
                      <TableHead>Record</TableHead>
                      <TableHead>Arguments</TableHead>
                      <TableHead className="w-[120px]">Status</TableHead>
                      <TableHead className="w-[100px]">Execution Time</TableHead>
                      <TableHead className="w-[100px]">Duration</TableHead>
                      <TableHead className="w-[80px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job) => (
                      <JobRow
                        key={job.id}
                        job={job}
                        isOpen={expandedJobId === job.id}
                        onToggle={() => toggleJob(job.id)}
                        onRerun={handleRerun}
                      />
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}
