'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Activity, Globe, Database, Search, Play, Eye, RefreshCw, Terminal } from 'lucide-react'
import { checkHealth } from '@/lib/api-client'
import type { CockpitPreferences, ServiceHealth } from '@/lib/cockpit-types'
import { useCockpitStore } from '@/lib/cockpit-store'
import { cn } from '@/lib/utils'

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

/** Map an action ID to the endpoint path it should POST to, or null if not wired. */
function getActionEndpoint(actionId: string, ticker: string): { path: string; method: string } | null {
  const encoded = encodeURIComponent(ticker)
  switch (actionId) {
    case 'metric_extraction':
    case 'rebuild_ticker_financials':
    case 'audit_ticker_financials':
      return { path: `/api/process/ticker/${encoded}`, method: 'POST' }
    case 'daily_news_ingest':
      return { path: `/api/backfill/ticker/${encoded}`, method: 'POST' }
    default:
      return null
  }
}

const AVAILABLE_ACTIONS = [
  { id: 'daily_news_ingest', label: 'Daily News Ingest', description: 'Fetch and process news for watchlist tickers' },
  { id: 'daily_announcement_ingest', label: 'Daily Announcement Ingest', description: 'Fetch company announcements' },
  { id: 'metric_extraction', label: 'Metric Extraction', description: 'Extract financial metrics from documents' },
  { id: 'rebuild_ticker_financials', label: 'Rebuild Ticker Financials', description: 'Rebuild financial data for a ticker' },
  { id: 'audit_ticker_financials', label: 'Audit Ticker Financials', description: 'Audit financial data integrity' },
  { id: 'show_candlestick', label: 'Show Candlestick', description: 'Generate candlestick chart' },
  { id: 'historical_news_ingest', label: 'Historical News Ingest', description: 'Backfill historical news data' },
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

export function OperationsScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker, preferences, updatePreferences } = useCockpitStore()
  
  const [selectedAction, setSelectedAction] = useState<string>('')
  const [actionArgs, setActionArgs] = useState(activeTicker || '')
  const [actionLog, setActionLog] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [backendHealth, setBackendHealth] = useState<ServiceHealth>({
    name: 'Backend API',
    status: 'unknown',
    endpoint: '/api/health',
    lastChecked: new Date(),
  })

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
      await checkHealth()
      const elapsed = Math.round(performance.now() - start)
      setBackendHealth({
        name: 'Backend API',
        status: 'healthy',
        endpoint: '/api/health',
        responseTimeMs: elapsed,
        lastChecked: new Date(),
      })
    } catch {
      setBackendHealth({
        name: 'Backend API',
        status: 'down',
        endpoint: '/api/health',
        lastChecked: new Date(),
        error: 'Unreachable',
      })
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

  if (!hasHydrated) return null

  const handlePreview = () => {
    const action = AVAILABLE_ACTIONS.find(a => a.id === selectedAction)
    if (action) {
      setActionLog(prev => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Preview: ${action.label}`,
        `  Ticker: ${actionArgs || '(none)'}`,
        `  Description: ${action.description}`,
        ''
      ])
    }
  }

  const handleExecute = async () => {
    const action = AVAILABLE_ACTIONS.find(a => a.id === selectedAction)
    if (!action) return

    const ticker = actionArgs.trim()
    const endpoint = getActionEndpoint(action.id, ticker)

    if (!endpoint) {
      setActionLog(prev => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Action not yet wired: ${action.label}`,
        ''
      ])
      return
    }

    if (!ticker) {
      setActionLog(prev => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Error: Ticker is required for ${action.label}`,
        ''
      ])
      return
    }

    setIsRunning(true)
    const start = performance.now()
    setActionLog(prev => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] Executing: ${action.label}`,
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
        setActionLog(prev => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] Completed: ${action.label}`,
          `  Status: ${res.status} OK`,
          `  Duration: ${elapsed}s`,
          body ? `  Response: ${JSON.stringify(body).slice(0, 200)}` : '',
          ''
        ])
      } else {
        const errText = await res.text().catch(() => res.statusText)
        setActionLog(prev => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] Failed: ${action.label}`,
          `  Status: ${res.status} ${res.statusText}`,
          `  Error: ${errText.slice(0, 200)}`,
          `  Duration: ${elapsed}s`,
          ''
        ])
      }
    } catch (err: unknown) {
      const elapsed = ((performance.now() - start) / 1000).toFixed(1)
      const message = err instanceof Error ? err.message : 'Unknown error'
      setActionLog(prev => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Error: ${action.label}`,
        `  ${message}`,
        `  Duration: ${elapsed}s`,
        ''
      ])
    } finally {
      setIsRunning(false)
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
              <Button variant="outline" size="sm" onClick={fetchHealth}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
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
                    {backendHealth.lastChecked
                      ? backendHealth.lastChecked.toLocaleTimeString('en-AU', {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                          hour12: false,
                        })
                      : '--:--:--'}
                  </p>
                </div>
              </div>
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
                placeholder="Ticker (e.g. BHP)"
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
      </div>
    </ScrollArea>
  )
}
