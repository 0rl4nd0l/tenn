'use client'

import { useState, useEffect, useCallback } from 'react'
import { JobList } from '@/components/cockpit/operations/job-list'
import { JobDetailPanel } from '@/components/cockpit/operations/job-detail-panel'
import { GpuWorkloadCard } from '@/components/cockpit/operations/gpu-workload-card'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Play, Eye, RefreshCw, Terminal, CalendarRange, Layers3 } from 'lucide-react'
import { getGpuProcesses } from '@/components/cockpit/gpu-activity-dialog'
import { checkHealth, executeAction, restartBackend, getActionJob, getSystemStatus, loadCockpitModel, previewAction, startActionJob } from '@/lib/api-client'
import type { ServiceHealth } from '@/lib/cockpit-types'
import { useCockpitStore } from '@/lib/cockpit-store'
import { cn } from '@/lib/utils'

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''
const JOB_POLL_INTERVAL_MS = 1500

/** Map an action ID to the endpoint path it should POST to, or null if not wired. */
function getActionEndpoint(actionId: string, ticker: string): { path: string; method: string } | null {
  const encoded = encodeURIComponent(ticker)
  switch (actionId) {
    case 'metric_extraction':
    case 'rebuild_ticker_financials':
    case 'audit_ticker_financials':
      return { path: `/api/process/ticker/${encoded}`, method: 'POST' }
    default:
      return null
  }
}

function buildActionArgs(actionId: string, ticker: string): Record<string, unknown> {
  const normalizedTicker = ticker.trim()
  if (!normalizedTicker) {
    return {}
  }

  if (actionId === 'daily_news_ingest' || actionId === 'historical_news_ingest') {
    return { tickers: normalizedTicker }
  }

  return { ticker: normalizedTicker }
}

/** Whether the action requires a ticker argument. */
type ActionDef = {
  id: string
  label: string
  description: string
  requiresTicker: boolean
}

const AVAILABLE_ACTIONS: readonly ActionDef[] = [
  { id: 'daily_news_ingest', label: 'Daily News Ingest', description: 'Fetch and process news for watchlist tickers', requiresTicker: false },
  { id: 'historical_news_ingest', label: 'Historical News Ingest', description: 'Backfill historical news data', requiresTicker: false },
  { id: 'daily_announcement_ingest', label: 'Daily Announcement Ingest', description: 'Fetch company announcements (market-wide)', requiresTicker: false },
  { id: 'metric_extraction', label: 'Metric Extraction', description: 'Extract financial metrics from documents', requiresTicker: true },
  { id: 'rebuild_ticker_financials', label: 'Rebuild Ticker Financials', description: 'Rebuild financial data for a ticker', requiresTicker: true },
  { id: 'audit_ticker_financials', label: 'Audit Ticker Financials', description: 'Audit financial data integrity', requiresTicker: true },
  { id: 'single_ticker_announcement_backfill', label: 'Single Ticker Backfill', description: 'Backfill announcements for a single ticker', requiresTicker: true },
  { id: 'show_candlestick', label: 'Show Candlestick', description: 'Generate candlestick chart', requiresTicker: true },
]

function formatLogTimestamp(): string {
  return new Date().toLocaleTimeString('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function buildUniverseBackfillArgs(years: string, processDocuments: boolean): Record<string, unknown> {
  const yearsInt = Number.parseInt(years, 10)
  const sanitizedYears = Number.isFinite(yearsInt) && yearsInt > 0 ? yearsInt : 5
  return {
    total_days_back: sanitizedYears * 365,
    process_documents: processDocuments,
  }
}

function normalizeModelId(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .replace(/^model:/i, '')
    .toLowerCase()
}

function actionUsesQueuedJob(actionId: string): boolean {
  return actionId !== 'show_candlestick'
}

export function OperationsScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker, setApiDefaultEnabled } = useCockpitStore()
  
  const [selectedAction, setSelectedAction] = useState<string>('')
  const [actionArgs, setActionArgs] = useState(activeTicker || '')
  const [actionLog, setActionLog] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [isRestartingBackend, setIsRestartingBackend] = useState(false)
  const [gpuHealth, setGpuHealth] = useState<ServiceHealth | null>(null)
  const [universeBackfillYears, setUniverseBackfillYears] = useState('5')
  const [universeProcessDocuments, setUniverseProcessDocuments] = useState(true)
  const [isUniverseRunning, setIsUniverseRunning] = useState(false)
  const [universeJobId, setUniverseJobId] = useState<string | null>(null)
  const [selectedOpsJobId, setSelectedOpsJobId] = useState<string | null>(null)

  // Wait for hydration to finish to avoid SSR/CSR mismatch with Zustand
  useEffect(() => {
    setHasHydrated(true)
  }, [])

  // Update actionArgs when activeTicker changes, if actionArgs is empty or matches previous activeTicker
  useEffect(() => {
    if (activeTicker) {
      setActionArgs(activeTicker)
    }
  }, [activeTicker])

  const fetchHealth = useCallback(async () => {
    try {
      const health = await checkHealth()
      const gpuService = health.services?.find((service) => service.name === 'gpu') ?? null
      setGpuHealth(
        gpuService
          ? {
              ...gpuService,
              lastChecked: new Date(),
            }
          : null,
      )
    } catch {
      setGpuHealth(null)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 30_000)
    return () => clearInterval(interval)
  }, [fetchHealth])

  const appendActionLog = useCallback((lines: string[]) => {
    setActionLog(prev => [...prev, ...lines])
  }, [])

  const focusBackendOpsJob = useCallback((jobId: string, actionLabel: string, scopeLabel: string) => {
    setSelectedOpsJobId(jobId)
    appendActionLog([
      `[${formatLogTimestamp()}] Tracking backend ops job: ${jobId}`,
      `  Action: ${actionLabel}`,
      `  Scope: ${scopeLabel}`,
      '  Open the Job Status panel for live progress and job details.',
    ])
  }, [appendActionLog])

  const handleRestartBackend = useCallback(async () => {
    setIsRestartingBackend(true)
    appendActionLog([
      `[${formatLogTimestamp()}] Restarting backend...`,
    ])
    try {
      const result = await restartBackend()
      appendActionLog([
        `[${formatLogTimestamp()}] ${result.message || 'Backend restart complete.'}`,
        '',
      ])
      await fetchHealth()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown restart error'
      appendActionLog([
        `[${formatLogTimestamp()}] Backend restart failed`,
        `  ${message}`,
        '',
      ])
    } finally {
      setIsRestartingBackend(false)
    }
  }, [appendActionLog, fetchHealth])

  const handlePreviewUniverseBackfill = useCallback(async () => {
    const args = buildUniverseBackfillArgs(universeBackfillYears, universeProcessDocuments)

    appendActionLog([
      `[${formatLogTimestamp()}] Preview: ASX Universe Announcement Backfill`,
    ])

    try {
      const preview = await previewAction({
        actionId: 'universe_announcement_enrichment_backfill',
        args,
      })
      appendActionLog([
        `  Command: ${preview.command.join(' ')}`,
        `  Impact: ${preview.estimated_impact}`,
        `  Timeout: ${preview.timeout_seconds}s`,
        preview.guard_message ? `  Guard: ${preview.guard_message}` : '',
        '',
      ].filter(Boolean))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      appendActionLog([
        `  Preview failed: ${message}`,
        '',
      ])
    }
  }, [appendActionLog, universeBackfillYears, universeProcessDocuments])

  const handleRunUniverseBackfill = useCallback(async () => {
    const args = buildUniverseBackfillArgs(universeBackfillYears, universeProcessDocuments)
    const yearsLabel = Number.parseInt(universeBackfillYears, 10) || 5

    setIsUniverseRunning(true)
    setUniverseJobId(null)
    appendActionLog([
      `[${formatLogTimestamp()}] Executing: ASX Universe Announcement Backfill`,
      `  Scope: all ASX tickers`,
      `  Years: ${yearsLabel}`,
      `  Process documents: ${universeProcessDocuments ? 'yes' : 'no'}`,
      `  Dispatch: backend ops queue`,
      '  Open the Job Status panel for live progress and job details.',
    ])

    try {
      if (universeProcessDocuments) {
        const systemStatus = await getSystemStatus()
        const extractionEnabled = Boolean(systemStatus.features?.extraction)
        const apiRuntimeAvailable = systemStatus.anthropic_key_configured === true
        const loadedModel = String(systemStatus.llm_model || '').trim() || null
        const requiredExtractModel = String(systemStatus.extract_model || '').trim() || null

        if (!extractionEnabled) {
          appendActionLog([
            `[${formatLogTimestamp()}] Blocked: extraction is disabled in backend runtime`,
            '  Disable "Process documents after discovery" to run announcement discovery only.',
            '',
          ])
          return
        }

        const extractionModelNeedsLoad =
          Boolean(requiredExtractModel) &&
          normalizeModelId(loadedModel) !== normalizeModelId(requiredExtractModel)

        if (extractionModelNeedsLoad) {
          const confirmed = window.confirm(
            [
              `Extraction model "${requiredExtractModel}" is not loaded.`,
              '',
              'Load it now and continue the backfill?',
            ].join('\n')
          )
          if (!confirmed) {
            appendActionLog([
              `[${formatLogTimestamp()}] Cancelled: extraction model load declined`,
              '',
            ])
            return
          }

          appendActionLog([
            `[${formatLogTimestamp()}] Loading extraction model`,
            `  Required: ${requiredExtractModel}`,
            loadedModel ? `  Loaded: ${loadedModel}` : '  Loaded: none',
          ])
          const loadResult = await loadCockpitModel(requiredExtractModel ?? undefined)
          appendActionLog([
            `[${formatLogTimestamp()}] ${loadResult.message}`,
            loadResult.runtime_url ? `  Runtime: ${loadResult.runtime_url}` : '',
          ].filter(Boolean))
        }

        if (apiRuntimeAvailable) {
          setApiDefaultEnabled(true)
          appendActionLog([
            `[${formatLogTimestamp()}] Chat runtime pinned to Claude API`,
          ])
        } else {
          appendActionLog([
            `[${formatLogTimestamp()}] Claude API not configured; chat runtime unchanged`,
          ])
        }
      }

      const queuedJob = await startActionJob({
        actionId: 'universe_announcement_enrichment_backfill',
        args,
      })
      setUniverseJobId(queuedJob.job_id)
      focusBackendOpsJob(queuedJob.job_id, 'ASX Universe Announcement Backfill', 'all ASX tickers')
      let lastJobUpdate = ''
      appendActionLog([
        `[${formatLogTimestamp()}] Queued backend ops job: ${queuedJob.job_id}`,
      ])

      while (true) {
        const job = await getActionJob(queuedJob.job_id)
        const stage = String(job.progress_stage || job.status || 'running')
        const detail = String(job.result || '')
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
          .at(-1) || ''
        const updateLine = `[${formatLogTimestamp()}] ${detail ? `${stage}: ${detail}` : stage}`

        if (updateLine !== lastJobUpdate) {
          appendActionLog([updateLine])
          lastJobUpdate = updateLine
        }

        if (job.status === 'success') {
          appendActionLog([
            `[${formatLogTimestamp()}] Completed: ASX Universe Announcement Backfill`,
            `  Job: ${queuedJob.job_id}`,
            '',
          ])
          break
        }

        if (job.status === 'failed') {
          throw new Error(String(job.result || `Job ${queuedJob.job_id} failed`))
        }

        await new Promise((resolve) => setTimeout(resolve, JOB_POLL_INTERVAL_MS))
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      appendActionLog([
        `[${formatLogTimestamp()}] Error: ASX Universe Announcement Backfill`,
        `  ${message}`,
        '',
      ])
    } finally {
      setIsUniverseRunning(false)
    }
  }, [appendActionLog, focusBackendOpsJob, setApiDefaultEnabled, universeBackfillYears, universeProcessDocuments])

  if (!hasHydrated) return null

  const handlePreview = async () => {
    const action = AVAILABLE_ACTIONS.find(a => a.id === selectedAction)
    if (!action) return

    const ticker = actionArgs.trim()
    const args = buildActionArgs(action.id, ticker)

    appendActionLog([
      `[${formatLogTimestamp()}] Preview: ${action.label}`,
    ])

    try {
      const preview = await previewAction({ actionId: action.id, args })
      appendActionLog([
        `  Command: ${preview.command.join(' ')}`,
        `  Impact: ${preview.estimated_impact}`,
        `  Timeout: ${preview.timeout_seconds}s`,
        preview.guard_message ? `  Guard: ${preview.guard_message}` : '',
        ''
      ].filter(Boolean))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      appendActionLog([
        `  Preview failed: ${message}`,
        ''
      ])
    }
  }

  const handleExecute = async () => {
    const action = AVAILABLE_ACTIONS.find(a => a.id === selectedAction)
    if (!action) return

    const ticker = actionArgs.trim()

    if (action.requiresTicker && !ticker) {
      appendActionLog([
        `[${formatLogTimestamp()}] Error: Ticker is required for ${action.label}`,
        ''
      ])
      return
    }

    setIsRunning(true)
    const start = performance.now()
    const endpoint = getActionEndpoint(action.id, ticker)

    if (endpoint) {
      // Direct REST endpoint path (pipeline actions)
      appendActionLog([
        `[${formatLogTimestamp()}] Executing: ${action.label}`,
        `  Ticker: ${ticker}`,
        `  Endpoint: ${endpoint.method} ${endpoint.path}`,
        '  Check the Job Status panel if the backend fans this into document work.',
      ])

      try {
        const headers: Record<string, string> = { 'Content-Type': 'application/json' }
        if (API_KEY) {
          headers['X-API-Key'] = API_KEY
        }
        const res = await fetch(endpoint.path, { method: endpoint.method, headers })
        const elapsed = ((performance.now() - start) / 1000).toFixed(1)

        if (res.ok) {
          const body = await res.json().catch(() => null)
          appendActionLog([
            `[${formatLogTimestamp()}] Completed: ${action.label}`,
            `  Status: ${res.status} OK`,
            `  Duration: ${elapsed}s`,
            body ? `  Response: ${JSON.stringify(body).slice(0, 200)}` : '',
            ''
          ])
        } else {
          const errText = await res.text().catch(() => res.statusText)
          appendActionLog([
            `[${formatLogTimestamp()}] Failed: ${action.label}`,
            `  Status: ${res.status} ${res.statusText}`,
            `  Error: ${errText.slice(0, 200)}`,
            `  Duration: ${elapsed}s`,
            ''
          ])
        }
      } catch (err: unknown) {
        const elapsed = ((performance.now() - start) / 1000).toFixed(1)
        const message = err instanceof Error ? err.message : 'Unknown error'
        appendActionLog([
          `[${formatLogTimestamp()}] Error: ${action.label}`,
          `  ${message}`,
          `  Duration: ${elapsed}s`,
          ''
        ])
      } finally {
        setIsRunning(false)
      }
    } else {
      // Cockpit actions prefer the backend ops panel when they run as queued jobs.
      const args = buildActionArgs(action.id, ticker)
      const usesQueuedJob = actionUsesQueuedJob(action.id)

      appendActionLog([
        `[${formatLogTimestamp()}] Executing: ${action.label}`,
        ticker ? `  Ticker: ${ticker}` : '  Scope: market-wide',
        usesQueuedJob ? '  Dispatch: backend ops queue' : '  Dispatch: synchronous action execution',
        usesQueuedJob ? '  Open the Job Status panel for live progress and job details.' : '',
      ].filter(Boolean))

      try {
        if (usesQueuedJob) {
          const queuedJob = await startActionJob({ actionId: action.id, args })
          focusBackendOpsJob(queuedJob.job_id, action.label, ticker || 'market-wide')
          appendActionLog([
            `[${formatLogTimestamp()}] Queued backend ops job: ${queuedJob.job_id}`,
          ])

          let lastJobUpdate = ''
          while (true) {
            const job = await getActionJob(queuedJob.job_id)
            const stage = String(job.progress_stage || job.status || 'running')
            const detail = String(job.result || '')
              .split('\n')
              .map((line) => line.trim())
              .filter(Boolean)
              .at(-1) || ''
            const updateLine = `[${formatLogTimestamp()}] ${detail ? `${stage}: ${detail}` : stage}`

            if (updateLine !== lastJobUpdate) {
              appendActionLog([updateLine])
              lastJobUpdate = updateLine
            }

            if (job.status === 'success') {
              appendActionLog([
                `[${formatLogTimestamp()}] Completed: ${action.label}`,
                `  Job: ${queuedJob.job_id}`,
                '',
              ])
              break
            }

            if (job.status === 'failed') {
              throw new Error(String(job.result || `Job ${queuedJob.job_id} failed`))
            }

            await new Promise((resolve) => setTimeout(resolve, JOB_POLL_INTERVAL_MS))
          }
        } else {
          const result = await executeAction({ actionId: action.id, args })
          const elapsed = ((performance.now() - start) / 1000).toFixed(1)
          appendActionLog([
            `[${formatLogTimestamp()}] Completed: ${action.label}`,
            `  Duration: ${elapsed}s`,
            `  Output: ${(result.result || '').slice(0, 300)}`,
            '',
          ])
        }
      } catch (err: unknown) {
        const elapsed = ((performance.now() - start) / 1000).toFixed(1)
        const message = err instanceof Error ? err.message : 'Unknown error'
        appendActionLog([
          `[${formatLogTimestamp()}] Error: ${action.label}`,
          `  ${message}`,
          `  Duration: ${elapsed}s`,
          ''
        ])
      } finally {
        setIsRunning(false)
      }
    }
  }

  const isIPhoneScale = preferences.iphoneScale

  return (
    <ScrollArea className="h-full">
      <div className={cn(
        "space-y-6 max-w-6xl mx-auto",
        isIPhoneScale ? "p-4" : "p-6"
      )}>
        <div className={cn(
          "flex items-center justify-between",
          isIPhoneScale && "flex-col items-start gap-2"
        )}>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Operations</h1>
            <p className="text-muted-foreground">Manage backend actions, ingestion, and system maintenance.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleRestartBackend} disabled={isRestartingBackend}>
              <RefreshCw className={cn('h-4 w-4 mr-2', isRestartingBackend && 'animate-spin')} />
              {isRestartingBackend ? 'Restarting...' : 'Restart Backend'}
            </Button>
          </div>
        </div>

        {/* GPU Workload — auto-visible when GPU is active, shows driving jobs */}
        <GpuWorkloadCard gpuHealth={gpuHealth} gpuProcesses={getGpuProcesses(gpuHealth)} />

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Layers3 className="h-5 w-5 text-primary" />
              ASX Universe Announcement Backfill
            </CardTitle>
            <CardDescription>
              Ingest all ASX ticker announcements across a selected history window using the existing chunked backfill action.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-[180px_minmax(0,1fr)]">
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">History Window</p>
                <Select value={universeBackfillYears} onValueChange={setUniverseBackfillYears}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 year</SelectItem>
                    <SelectItem value="3">3 years</SelectItem>
                    <SelectItem value="5">5 years</SelectItem>
                    <SelectItem value="10">10 years</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3">
                <div className="flex items-center gap-3">
                  <CalendarRange className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Process documents after discovery</p>
                    <p className="text-xs text-muted-foreground">
                      Keep enabled to download PDFs and run downstream document processing during the bulk ingest.
                    </p>
                  </div>
                </div>
                <Switch
                  checked={universeProcessDocuments}
                  onCheckedChange={setUniverseProcessDocuments}
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button variant="outline" onClick={handlePreviewUniverseBackfill} disabled={isUniverseRunning}>
                <Eye className="h-4 w-4 mr-2" />
                Preview Run
              </Button>
              <Button onClick={handleRunUniverseBackfill} disabled={isUniverseRunning || isRunning}>
                <Play className="h-4 w-4 mr-2" />
                {isUniverseRunning ? 'Running Backfill...' : 'Run Backfill'}
              </Button>
              {universeJobId ? (
                <button type="button" onClick={() => setSelectedOpsJobId(universeJobId)}>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    Backend ops job {universeJobId}
                  </Badge>
                </button>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {/* Action Executor */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Terminal className="h-5 w-5 text-primary" />
              Action Executor
            </CardTitle>
            <CardDescription>Run cockpit actions and follow queued work in the backend ops panel</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className={cn(
              "flex gap-3",
              isIPhoneScale && "flex-col"
            )}>
              <Select value={selectedAction} onValueChange={setSelectedAction}>
                <SelectTrigger className={cn(
                  isIPhoneScale ? "w-full" : "w-[300px]"
                )}>
                  <SelectValue placeholder="Select action..." />
                </SelectTrigger>
                <SelectContent>
                  {AVAILABLE_ACTIONS.map(action => (
                    <SelectItem key={action.id} value={action.id}>
                      <div>
                        <span>{action.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                placeholder={
                  selectedAction
                    ? AVAILABLE_ACTIONS.find(a => a.id === selectedAction)?.requiresTicker
                      ? 'Ticker (e.g. BHP)'
                      : 'Ticker (optional — runs market-wide if empty)'
                    : 'Ticker (e.g. BHP)'
                }
                value={actionArgs}
                onChange={(e) => setActionArgs(e.target.value)}
                className="flex-1 font-mono text-sm"
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handlePreview} disabled={!selectedAction}>
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </Button>
              <Button onClick={handleExecute} disabled={!selectedAction || isRunning}>
                <Play className="h-4 w-4 mr-2" />
                {isRunning ? 'Running...' : 'Execute'}
              </Button>
            </div>

            {/* Action Log */}
            {actionLog.length > 0 && (
              <div className="mt-4 p-3 rounded-lg bg-muted/50 border border-border">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-medium text-muted-foreground">Execution Log</p>
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setActionLog([])}>
                    Clear
                  </Button>
                </div>
                <pre className="text-xs font-mono text-foreground overflow-x-auto max-h-48 overflow-y-auto">
                  {actionLog.join('\n')}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Job Status Panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Layers3 className="h-5 w-5 text-primary" />
              Job Status
            </CardTitle>
            <CardDescription>Backend operational job tracking</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <JobList
                onSelectJob={setSelectedOpsJobId}
                selectedJobId={selectedOpsJobId}
              />
              {selectedOpsJobId ? (
                <JobDetailPanel
                  jobId={selectedOpsJobId}
                  onClose={() => setSelectedOpsJobId(null)}
                />
              ) : (
                <Card className="h-full flex items-center justify-center">
                  <p className="text-xs text-muted-foreground p-8">
                    Select a job to view details
                  </p>
                </Card>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  )
}
