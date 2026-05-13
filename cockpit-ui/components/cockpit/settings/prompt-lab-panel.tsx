'use client'

import { useEffect, useMemo, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import {
  dryRunPromptLabRoute,
  getPromptLabRoutes,
  previewPromptLabRoute,
} from '@/lib/api-client'
import type {
  PromptLabBlock,
  PromptLabDryRunResponse,
  PromptLabPreviewResponse,
  PromptLabRoute,
} from '@/lib/cockpit-types'
import {
  Beaker,
  Eye,
  FileJson,
  Lock,
  Loader2,
  MessageSquare,
  PencilLine,
  Route,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

const DEFAULT_MESSAGE = 'Summarise BHP using current evidence.'

const KIND_STYLES: Record<string, string> = {
  Agent: 'border-cyan-500/30 text-cyan-300',
  Keyword: 'border-amber-500/30 text-amber-300',
  Mode: 'border-violet-500/30 text-violet-300',
  JSON: 'border-emerald-500/30 text-emerald-300',
  Overlay: 'border-blue-500/30 text-blue-300',
  'No LLM': 'border-muted-foreground/30 text-muted-foreground',
}

function blockIcon(block: PromptLabBlock) {
  if (block.locked) return <Lock className="h-3.5 w-3.5" />
  if (block.kind === 'operator_draft') return <PencilLine className="h-3.5 w-3.5" />
  if (block.kind === 'output_contract') return <FileJson className="h-3.5 w-3.5" />
  return <ShieldCheck className="h-3.5 w-3.5" />
}

function compactText(value: unknown): string {
  if (!value || typeof value !== 'object') return ''
  return Object.entries(value as Record<string, unknown>)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join(' | ')
}

export function PromptLabPanel() {
  const [routes, setRoutes] = useState<PromptLabRoute[]>([])
  const [selectedRouteId, setSelectedRouteId] = useState('')
  const [sampleMessage, setSampleMessage] = useState(DEFAULT_MESSAGE)
  const [ticker, setTicker] = useState('BHP')
  const [mode, setMode] = useState('analysis')
  const [draftOverride, setDraftOverride] = useState('')
  const [preview, setPreview] = useState<PromptLabPreviewResponse | null>(null)
  const [dryRun, setDryRun] = useState<PromptLabDryRunResponse | null>(null)
  const [loadingRoutes, setLoadingRoutes] = useState(true)
  const [previewing, setPreviewing] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    async function loadRoutes() {
      setLoadingRoutes(true)
      setError(null)
      try {
        const response = await getPromptLabRoutes()
        if (!alive) return
        setRoutes(response.routes)
        setSelectedRouteId((current) => current || response.routes[0]?.route_id || '')
      } catch (err) {
        if (!alive) return
        setError(err instanceof Error ? err.message : 'Prompt routes unavailable')
      } finally {
        if (alive) setLoadingRoutes(false)
      }
    }
    void loadRoutes()
    return () => {
      alive = false
    }
  }, [])

  const selectedRoute = useMemo(
    () => routes.find((route) => route.route_id === selectedRouteId) ?? null,
    [routes, selectedRouteId],
  )

  const requestPayload = useMemo(() => ({
    route_id: selectedRouteId,
    message: sampleMessage,
    ticker: ticker.trim() || null,
    mode,
    draft_override: draftOverride.trim() || null,
  }), [draftOverride, mode, sampleMessage, selectedRouteId, ticker])

  useEffect(() => {
    if (!selectedRouteId) return
    let alive = true
    async function loadPreview() {
      setPreviewing(true)
      setError(null)
      try {
        const response = await previewPromptLabRoute(requestPayload)
        if (!alive) return
        setPreview(response)
        setDryRun(null)
      } catch (err) {
        if (!alive) return
        setError(err instanceof Error ? err.message : 'Prompt preview failed')
      } finally {
        if (alive) setPreviewing(false)
      }
    }
    const timer = window.setTimeout(() => void loadPreview(), 250)
    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [requestPayload, selectedRouteId])

  async function runDryRun() {
    if (!selectedRoute?.supports_dry_run) return
    setRunning(true)
    setError(null)
    try {
      const response = await dryRunPromptLabRoute(requestPayload)
      setDryRun(response)
      setPreview(response.preview)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prompt dry-run failed')
    } finally {
      setRunning(false)
    }
  }

  if (loadingRoutes) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Loading Prompt Lab
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)_320px]">
      <Card className="overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Route className="h-4 w-4 text-primary" />
            Routing Paths
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {routes.map((route) => (
            <button
              key={route.route_id}
              type="button"
              onClick={() => setSelectedRouteId(route.route_id)}
              className={cn(
                'w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                selectedRouteId === route.route_id ? 'border-primary bg-primary/10' : 'border-border',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-sm font-medium">{route.label}</span>
                <Badge variant="outline" className={cn('shrink-0 text-[10px]', KIND_STYLES[route.kind])}>
                  {route.kind}
                </Badge>
              </div>
              <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                {route.description}
              </div>
            </button>
          ))}
        </CardContent>
      </Card>

      <Card className="min-w-0 overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between gap-3 text-base">
            <span className="flex min-w-0 items-center gap-2">
              <Eye className="h-4 w-4 text-primary" />
              <span className="truncate">Prompt Stack</span>
            </span>
            {previewing && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_120px_120px]">
            <div className="space-y-1">
              <label htmlFor="prompt-lab-message" className="text-xs text-muted-foreground">
                Sample message
              </label>
              <Input
                id="prompt-lab-message"
                value={sampleMessage}
                onChange={(event) => setSampleMessage(event.target.value)}
                className="font-mono text-xs"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="prompt-lab-ticker" className="text-xs text-muted-foreground">
                Ticker
              </label>
              <Input
                id="prompt-lab-ticker"
                value={ticker}
                onChange={(event) => setTicker(event.target.value.toUpperCase())}
                className="font-mono text-xs"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Mode</label>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger className="h-9 font-mono text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="analysis">analysis</SelectItem>
                  <SelectItem value="strategy">strategy</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="prompt-lab-draft" className="flex items-center gap-2 text-xs text-muted-foreground">
              <PencilLine className="h-3.5 w-3.5" />
              Draft override
            </label>
            <Textarea
              id="prompt-lab-draft"
              value={draftOverride}
              onChange={(event) => setDraftOverride(event.target.value)}
              placeholder="Unsaved draft text appended only to preview and dry-run."
              className="min-h-24 resize-y font-mono text-xs"
            />
          </div>

          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}

          <ScrollArea className="h-[520px] pr-3">
            <div className="space-y-3">
              {preview?.blocks.map((block) => (
                <div key={block.block_id} className="rounded-md border bg-card/60">
                  <div className="flex items-center justify-between gap-3 border-b px-3 py-2">
                    <div className="flex min-w-0 items-center gap-2">
                      {blockIcon(block)}
                      <span className="truncate text-sm font-medium">{block.label}</span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={block.locked ? 'secondary' : 'default'} className="text-[10px]">
                        {block.locked ? 'LOCKED' : 'DRAFT'}
                      </Badge>
                      <Badge variant="outline" className="text-[10px]">
                        {block.kind}
                      </Badge>
                    </div>
                  </div>
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs leading-relaxed text-muted-foreground">
                    {block.content}
                  </pre>
                  <div className="border-t px-3 py-2 text-[10px] text-muted-foreground">
                    {block.source}
                    {block.warning ? ` | ${block.warning}` : ''}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Beaker className="h-4 w-4 text-primary" />
            Dry Run
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-md border p-3">
              <div className="text-[10px] uppercase text-muted-foreground">Blocks</div>
              <div className="mt-1 font-mono text-lg">{preview?.blocks.length ?? 0}</div>
            </div>
            <div className="rounded-md border p-3">
              <div className="text-[10px] uppercase text-muted-foreground">Est. tokens</div>
              <div className="mt-1 font-mono text-lg">{preview?.estimated_tokens ?? 0}</div>
            </div>
          </div>

          {selectedRoute?.warning && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              {selectedRoute.warning}
            </div>
          )}

          <Button
            className="w-full gap-2"
            disabled={!selectedRoute?.supports_dry_run || running}
            onClick={() => void runDryRun()}
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Run dry test
          </Button>

          <Separator />

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <MessageSquare className="h-4 w-4 text-primary" />
              Result
            </div>
            <ScrollArea className="h-56 rounded-md border bg-muted/20 p-3">
              <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-muted-foreground">
                {dryRun?.text || 'No dry-run result yet.'}
              </pre>
            </ScrollArea>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Route metadata</div>
            <div className="rounded-md border px-3 py-2 font-mono text-[11px] text-muted-foreground">
              {compactText(dryRun?.routing_metadata) || 'DATA_MISSING'}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
