'use client'

import { useState, useEffect, useCallback } from 'react'
import { JobList } from '@/components/cockpit/operations/job-list'
import { JobDetailPanel } from '@/components/cockpit/operations/job-detail-panel'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Activity, Globe, Database, Search, Play, Eye, RefreshCw, Terminal, Cpu, ExternalLink, CalendarRange, Layers3, Flame, MemoryStick } from 'lucide-react'
import { GpuActivityDialog, getGpuProcesses, getGpuSummary } from '@/components/cockpit/gpu-activity-dialog'
import { HostActivityDialog, getHostSummary } from '@/components/cockpit/host-activity-dialog'
import { checkHealth, restartBackend, executeAction, getActionJob, getSystemStatus, loadCockpitModel, previewAction, startActionJob } from '@/lib/api-client'
import type { CockpitPreferences, ServiceHealth } from '@/lib/cockpit-types'
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

function getStatusColor(status: ServiceHealth['status']) {
  switch (status) {
    case 'healthy':
      return 'bg-[oklch(0.65_0.2_145)]'
    case 'degraded':
      return 'bg-[oklch(0.75_0.15_80)]'
    case 'down':
      return 'bg-[oklch(0.55_0.2_25)]'
    default:
      return 'bg-muted-foreground'
  }
}

function getStatusBadgeVariant(status: ServiceHealth['status']): 'default' | 'secondary' | 'destructive' | 'critical' | 'outline' {
  switch (status) {
    case 'healthy':
      return 'default'
    case 'degraded':
      return 'secondary'
    case 'down':
      return 'critical'
    default:
      return 'outline'
  }
}

function formatStatusLabel(status: ServiceHealth['status']): string {
  switch (status) {
    case 'healthy':
      return 'RUNNING'
    case 'degraded':
      return 'DEGRADED'
    case 'down':
      return 'DOWN'
    default:
      return 'UNKNOWN'
  }
}

function formatClock(time: Date | undefined): string {
  return time
    ? time.toLocaleTimeString('en-AU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    : '--:--:--'
}

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

export function OperationsScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker, preferences, updatePreferences, setApiDefaultEnabled } = useCockpitStore()
  
  const [selectedAction, setSelectedAction] = useState<string>('')
  const [actionArgs, setActionArgs] = useState(activeTicker || '')
  const [actionLog, setActionLog] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [isRestartingBackend, setIsRestartingBackend] = useState(false)
  const [backendHealth, setBackendHealth] = useState<ServiceHealth>({
    name: 'Backend API',
    status: 'unknown',
    endpoint: '/api/health',
    lastChecked: new Date(),
  })
  const [gpuHealth, setGpuHealth] = useState<ServiceHealth | null>(null)
  const [hostHealth, setHostHealth] = useState<ServiceHealth | null>(null)
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
    const start = performance.now()
    try {
      const health = await checkHealth()
      const elapsed = Math.round(performance.now() - start)
      const backendService = health.services?.find((service) => service.name === 'backend')
      const gpuService = health.services?.find((service) => service.name === 'gpu') ?? null
      const hostService = health.services?.find((service) => service.name === 'host') ?? null
      setBackendHealth({
        name: backendService?.name ?? 'Backend API',
        status: backendService?.status ?? 'healthy',
        endpoint: backendService?.endpoint ?? '/api/health',
        responseTimeMs: backendService?.responseTimeMs ?? elapsed,
        lastChecked: new Date(),
        error: backendService?.error,
        details: backendService?.details,
      })
      setGpuHealth(
        gpuService
          ? {
              ...gpuService,
              lastChecked: new Date(),
            }
          : null,
      )
      setHostHealth(
        hostService
          ? {
              ...hostService,
              lastChecked: new Date(),
            }
          : null,
      )
    } catch {
      setBackendHealth({
        name: 'Backend API',
        status: 'down',
        endpoint: '/api/health',
        lastChecked: new Date(),
        error: 'Unreachable',
      })
      setGpuHealth(null)
      setHostHealth(null)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 30_000)
    return () => clearInterval(interval)
  }, [fetchHealth])

  const togglePreference = (key: keyof CockpitPreferences) => {
    updatePreferences({ [key]: !preferences[key] })
  }

  const appendActionLog = useCallback((lines: string[]) => {
    setActionLog(prev => [...prev, ...lines])
  }, [])

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
      `  Dispatch: cockpit action registry`,
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
      let lastJobUpdate = ''
      appendActionLog([
        `[${formatLogTimestamp()}] Queued: ${queuedJob.job_id}`,
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
  }, [appendActionLog, setApiDefaultEnabled, universeBackfillYears, universeProcessDocuments])

  if (!hasHydrated) return null

  const gpuSummary = getGpuSummary(gpuHealth)
  const gpuProcesses = getGpuProcesses(gpuHealth)
  const hostSummary = getHostSummary(hostHealth)
  const hostCpu = hostHealth?.details?.cpu as Record<string, unknown> | undefined
  const hostMemory = hostHealth?.details?.memory as Record<string, unknown> | undefined
  const hostDisks = Array.isArray(hostHealth?.details?.disks)
    ? (hostHealth?.details?.disks as Array<Record<string, unknown>>)
    : []

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
      // Cockpit action registry path (subprocess dispatch)
      const args = buildActionArgs(action.id, ticker)

      appendActionLog([
        `[${formatLogTimestamp()}] Executing: ${action.label}`,
        ticker ? `  Ticker: ${ticker}` : '  Scope: market-wide',
        `  Dispatch: cockpit action registry`,
      ])

      try {
        const result = await executeAction({ actionId: action.id, args })
        const elapsed = ((performance.now() - start) / 1000).toFixed(1)
        appendActionLog([
          `[${formatLogTimestamp()}] Completed: ${action.label}`,
          `  Duration: ${elapsed}s`,
          `  Output: ${(result.result || '').slice(0, 300)}`,
          ''
        ])
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

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-6xl mx-auto">
        {/* Feature Toggles */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Feature Toggles
            </CardTitle>
            <CardDescription>Enable or disable cockpit features</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Web Search</p>
                  <p className="text-xs text-muted-foreground">Enable web search augmentation</p>
                </div>
              </div>
              <Switch 
                checked={preferences.webSearchEnabled}
                onCheckedChange={() => togglePreference('webSearchEnabled')}
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Search className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">RAG</p>
                  <p className="text-xs text-muted-foreground">Enable retrieval augmented generation</p>
                </div>
              </div>
              <Switch 
                checked={preferences.ragEnabled}
                onCheckedChange={() => togglePreference('ragEnabled')}
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Database className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">DB Diagnostics</p>
                  <p className="text-xs text-muted-foreground">Enable database diagnostic queries</p>
                </div>
              </div>
              <Switch 
                checked={preferences.dbDiagnosticsEnabled}
                onCheckedChange={() => togglePreference('dbDiagnosticsEnabled')}
              />
            </div>
          </CardContent>
        </Card>

        {/* Service Health */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Activity className="h-5 w-5 text-primary" />
                  Service Health
                </CardTitle>
                <CardDescription>Monitor connected services (auto-refresh every 30s)</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={fetchHealth}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
                <Button variant="outline" size="sm" onClick={handleRestartBackend} disabled={isRestartingBackend}>
                  <RefreshCw className={cn('h-4 w-4 mr-2', isRestartingBackend && 'animate-spin')} />
                  {isRestartingBackend ? 'Restarting...' : 'Restart Backend'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              <div
                className="flex items-center justify-between p-3 rounded-lg border border-border bg-card"
              >
                <div className="flex items-center gap-3">
                  <span className={cn(
                    'h-3 w-3 rounded-full',
                    getStatusColor(backendHealth.status)
                  )} />
                  <div>
                    <p className="text-sm font-medium">{backendHealth.name}</p>
                    <p className="text-xs text-muted-foreground font-mono">{backendHealth.endpoint}</p>
                  </div>
                  </div>
                  <div className="text-right">
                  <Badge variant={getStatusBadgeVariant(backendHealth.status)} className="text-[10px] font-mono">
                    {formatStatusLabel(backendHealth.status)}
                  </Badge>
                  {backendHealth.responseTimeMs && (
                    <p className="text-[10px] text-muted-foreground font-mono mt-1">
                      {backendHealth.responseTimeMs}ms
                    </p>
                  )}
                  <p className="text-[10px] text-muted-foreground font-mono mt-1">
                    {formatClock(backendHealth.lastChecked)}
                  </p>
                </div>
              </div>

              <GpuActivityDialog gpuHealth={gpuHealth}>
                  <button
                    type="button"
                    className="flex items-center justify-between rounded-lg border border-border bg-card p-3 text-left transition-colors hover:border-primary/50 hover:bg-accent/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  >
                    <div className="flex items-center gap-3">
                      <span className={cn(
                        'h-3 w-3 rounded-full',
                        getStatusColor(gpuHealth?.status ?? 'unknown')
                      )} />
                      <div>
                        <p className="text-sm font-medium flex items-center gap-2">
                          <Cpu className="h-4 w-4 text-primary" />
                          GPU Activity
                        </p>
                        <p className="text-xs text-muted-foreground font-mono break-words">{gpuSummary}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={getStatusBadgeVariant(gpuHealth?.status ?? 'unknown')} className="text-[10px] font-mono">
                        {formatStatusLabel(gpuHealth?.status ?? 'unknown')}
                      </Badge>
                      <p className="mt-1 flex items-center justify-end gap-1 text-[10px] text-muted-foreground font-mono">
                        details
                        <ExternalLink className="h-3 w-3" />
                      </p>
                      <p className="text-[10px] text-muted-foreground font-mono mt-1">
                        {gpuProcesses.length} proc{gpuProcesses.length === 1 ? '' : 's'}
                      </p>
                    </div>
                  </button>
              </GpuActivityDialog>

              <HostActivityDialog hostHealth={hostHealth}>
                <button
                  type="button"
                  className="flex items-center justify-between rounded-lg border border-border bg-card p-3 text-left transition-colors hover:border-primary/50 hover:bg-accent/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      'h-3 w-3 rounded-full',
                      getStatusColor(hostHealth?.status ?? 'unknown')
                    )} />
                    <div>
                      <p className="text-sm font-medium flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-primary" />
                        Host Resources
                      </p>
                      <p className="text-xs text-muted-foreground font-mono break-words">{hostSummary}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={getStatusBadgeVariant(hostHealth?.status ?? 'unknown')} className="text-[10px] font-mono">
                      {formatStatusLabel(hostHealth?.status ?? 'unknown')}
                    </Badge>
                    <p className="mt-1 flex items-center justify-end gap-1 text-[10px] text-muted-foreground font-mono">
                      details
                      <ExternalLink className="h-3 w-3" />
                    </p>
                    <p className="text-[10px] text-muted-foreground font-mono mt-1">
                      {hostDisks.length} disk{hostDisks.length === 1 ? '' : 's'}
                    </p>
                  </div>
                </button>
              </HostActivityDialog>
            </div>
          </CardContent>
        </Card>

        {/* GPU Activity Breakdown — auto-visible when GPU is active */}
        {(() => {
          const gpus = Array.isArray(gpuHealth?.details?.gpus)
            ? (gpuHealth!.details!.gpus as Array<Record<string, unknown>>)
            : []
          const firstGpu = gpus[0]
          const utilPct = typeof firstGpu?.util_percent === 'number' ? firstGpu.util_percent : null
          const memUsed = typeof firstGpu?.mem_used_mib === 'number' ? Math.round(firstGpu.mem_used_mib as number) : null
          const memTotal = typeof firstGpu?.mem_total_mib === 'number' ? Math.round(firstGpu.mem_total_mib as number) : null
          const showPanel = (utilPct !== null && utilPct > 0) || gpuProcesses.length > 0

          if (!showPanel) return null

          return (
            <Card className={cn(
              'border-l-4',
              utilPct !== null && utilPct >= 90
                ? 'border-l-red-500 bg-red-500/5'
                : utilPct !== null && utilPct >= 50
                  ? 'border-l-yellow-500 bg-yellow-500/5'
                  : 'border-l-green-500 bg-green-500/5'
            )}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Flame className={cn(
                    'h-4 w-4',
                    utilPct !== null && utilPct >= 90 ? 'text-red-500' :
                    utilPct !== null && utilPct >= 50 ? 'text-yellow-500' : 'text-green-500'
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
              <CardContent className="pt-0">
                {gpuProcesses.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    GPU is active but no compute processes were reported by nvidia-smi.
                  </p>
                ) : (
                  <div className="space-y-2">
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
                          className="rounded-md border border-border/60 bg-background/60 p-2.5 font-mono text-xs"
                        >
                          <div className="flex items-center gap-2 mb-1">
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
                            <p className="text-[11px] text-muted-foreground/70 break-all line-clamp-2">
                              {command}
                            </p>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })()}

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Cpu className="h-5 w-5 text-primary" />
              Hardware Status
            </CardTitle>
            <CardDescription>Live host CPU, RAM, and storage usage from the Cockpit health probe</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-xs font-medium text-muted-foreground">CPU Load</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">
                  {typeof hostCpu?.normalized_load_percent === 'number' ? `${hostCpu.normalized_load_percent}%` : 'n/a'}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {typeof hostCpu?.core_count === 'number' ? `${hostCpu.core_count} cores` : 'core count unavailable'}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {typeof hostCpu?.load_1m === 'number' ? `1m ${hostCpu.load_1m}` : '1m n/a'}
                  {typeof hostCpu?.load_5m === 'number' ? ` | 5m ${hostCpu.load_5m}` : ''}
                </p>
              </div>

              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-xs font-medium text-muted-foreground">RAM Usage</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">
                  {typeof hostMemory?.used_percent === 'number' ? `${hostMemory.used_percent}%` : 'n/a'}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {typeof hostMemory?.used_gib === 'number' && typeof hostMemory?.total_gib === 'number'
                    ? `${hostMemory.used_gib} / ${hostMemory.total_gib} GiB`
                    : 'memory unavailable'}
                </p>
              </div>

              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-xs font-medium text-muted-foreground">Storage</p>
                <p className="mt-2 text-2xl font-semibold text-foreground">
                  {hostDisks.length > 0 && typeof hostDisks[0]?.used_percent === 'number'
                    ? `${hostDisks[0].used_percent}%`
                    : 'n/a'}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {hostDisks.length > 0 ? `Primary ${String(hostDisks[0]?.mount ?? '/')}` : 'disk data unavailable'}
                </p>
                <p className="mt-1 text-xs font-mono text-muted-foreground">
                  {hostDisks.length > 1 && typeof hostDisks[1]?.used_percent === 'number'
                    ? `${String(hostDisks[1]?.mount ?? '/home')} ${hostDisks[1].used_percent}%`
                    : hostDisks.length > 1
                      ? String(hostDisks[1]?.mount ?? '/home')
                      : 'additional mounts unavailable'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

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
                <Badge variant="outline" className="font-mono">
                  Job {universeJobId}
                </Badge>
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
            <CardDescription>Run cockpit actions directly</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Select value={selectedAction} onValueChange={setSelectedAction}>
                <SelectTrigger className="w-[300px]">
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
