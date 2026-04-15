'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useCockpitStore } from '@/lib/cockpit-store'
import { parseCockpitConfig, resolveRuntimeModel } from '@/lib/cockpit-config'
import { cn } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'

interface CockpitStatusBarProps {
  backendHealthy: boolean
  backendLastHealthyAt: Date | null
  backendError: string | null
}

function formatClock(time: Date | null): string {
  if (!time) return 'unknown'
  return time.toLocaleTimeString('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export function CockpitStatusBar({
  backendHealthy,
  backendLastHealthyAt,
  backendError,
}: CockpitStatusBarProps) {
  const {
    sessionStats,
    chatModel,
    apiDefaultEnabled,
    activeSource,
    setApiDefaultEnabled,
  } = useCockpitStore()
  const { data: configData, error: configError } = useQuery({
    queryKey: ['cockpit-config-status'],
    queryFn: async () => {
      const response = await fetch('/api/cockpit/config', { cache: 'no-store' })
      if (!response.ok) {
        throw new Error(`Config unavailable (${response.status})`)
      }
      return (await response.json()) as Record<string, unknown>
    },
    refetchInterval: 30000,
    retry: 1,
  })

  const config = parseCockpitConfig(configData)
  const apiOverrideAvailable = config.anthropicKeyConfigured
  const apiOverrideForced = config.extractionActive === true && apiOverrideAvailable
  const activeRuntimeModel = resolveRuntimeModel(sessionStats.activeModel, config.model) || '--'
  const configAuthFailure = configError instanceof Error && /(401|403)/.test(configError.message)
  const extractionLabel = config.extractionActive === true
    ? 'running'
    : config.extractionActive === false
      ? 'idle'
      : '--'
  const extractionVariant = config.extractionActive === true
    ? 'default'
    : config.extractionActive === false
      ? 'outline'
      : 'secondary'
  const extractionTitle = config.extractionActive === true
    ? `Extraction running${config.extractionSource ? ` via ${config.extractionSource}` : ''}${config.extractionActivityExpiresInSeconds !== null ? `, ttl ${config.extractionActivityExpiresInSeconds}s` : ''}`
    : config.extractionActive === false
      ? 'Extraction idle'
      : 'Extraction status unavailable'
  const extractionHref = config.extractionActive === true && config.activeRuns.length > 0
    ? '/verification?attach=active'
    : null
  const routeLabel = activeSource === 'anthropic'
    ? 'Claude API'
    : activeSource === 'local'
      ? 'local'
      : '--'
  const routeVariant = activeSource === 'anthropic'
    ? 'default'
    : activeSource === 'local'
      ? 'outline'
      : 'secondary'

  useEffect(() => {
    if (!apiOverrideAvailable && apiDefaultEnabled) {
      setApiDefaultEnabled(false)
    }
  }, [apiDefaultEnabled, apiOverrideAvailable, setApiDefaultEnabled])

  useEffect(() => {
    if (apiOverrideForced && !apiDefaultEnabled) {
      setApiDefaultEnabled(true)
      toast.success('Extraction is running. Claude API has been pinned as the default chat route.')
    }
  }, [apiDefaultEnabled, apiOverrideForced, setApiDefaultEnabled])

  const handleApiOverrideToggle = () => {
    if (!apiOverrideAvailable) {
      toast.error('Claude API is not configured for this cockpit session.')
      return
    }
    if (apiOverrideForced && apiDefaultEnabled) {
      toast.error('Claude API routing is locked while extraction is running.')
      return
    }
    const nextEnabled = !apiDefaultEnabled
    setApiDefaultEnabled(nextEnabled)
    toast.success(
      nextEnabled
        ? 'Claude API pinned as the default chat route.'
        : 'Adaptive model routing restored.'
    )
  }

  return (
    <footer className="shrink-0 border-t border-border bg-card/95 px-4 py-1 text-xs terminal-panel">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            Selected: {chatModel}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            Active: {activeRuntimeModel}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            {config.maxTokens ? `max ${config.maxTokens}` : 'max --'}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            {config.temperature !== null ? `temp ${config.temperature.toFixed(2)}` : 'temp --'}
          </Badge>
          <Badge variant={routeVariant} className="h-5 text-[10px] font-mono">
            Source: {routeLabel}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono hidden lg:inline-flex">
            profile: {config.profile ?? '--'}
          </Badge>
          <Badge asChild variant={apiOverrideAvailable ? 'outline' : 'critical'} className="hidden h-5 px-1.5 text-[10px] font-mono xl:inline-flex">
            <button
              type="button"
              onClick={handleApiOverrideToggle}
              aria-pressed={apiDefaultEnabled}
              title={
                apiOverrideForced
                  ? 'Claude API routing is locked while extraction is running.'
                  : apiOverrideAvailable
                  ? apiDefaultEnabled
                    ? 'Claude API pinned as the default chat route. Click to restore adaptive routing.'
                    : 'Claude API available. Click to pin cloud routing as the default.'
                  : 'Claude API key missing for this cockpit session.'
              }
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-1 py-0.5 transition-colors',
                apiOverrideAvailable ? 'cursor-pointer hover:bg-[oklch(0.22_0.02_255)]' : 'cursor-not-allowed opacity-80',
                apiDefaultEnabled && 'border border-[oklch(0.72_0.16_210)]/70 api-default-override-badge'
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'h-2 w-2 rounded-full',
                  apiDefaultEnabled
                    ? 'api-default-override-dot api-default-override-pulse'
                    : apiOverrideAvailable
                      ? 'bg-[oklch(0.68_0.18_245)]'
                      : 'bg-destructive'
                )}
              />
              <span>
                API: {apiOverrideAvailable ? (apiOverrideForced ? 'forced' : apiDefaultEnabled ? 'default' : 'set') : 'missing'}
              </span>
            </button>
          </Badge>
          {extractionHref ? (
            <Badge asChild variant={extractionVariant} className="h-5 text-[10px] font-mono" title={extractionTitle}>
              <Link href={extractionHref}>Extract: {extractionLabel}</Link>
            </Badge>
          ) : (
            <Badge variant={extractionVariant} className="h-5 text-[10px] font-mono" title={extractionTitle}>
              Extract: {extractionLabel}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-muted-foreground">
            latency: {sessionStats.lastLatencyMs}ms
          </span>
          <span className={`h-2 w-2 rounded-full ${backendHealthy ? 'bg-[oklch(0.69_0.22_145)] status-dot-running' : 'bg-destructive'}`} />
          <span className="font-mono text-muted-foreground">
            {backendHealthy ? 'backend running' : 'backend down'}
          </span>
          <span className="font-mono text-muted-foreground hidden xl:inline">
            last healthy: {formatClock(backendLastHealthyAt)}
          </span>
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            Session: ${sessionStats.totalCostUsd.toFixed(4)}
          </Badge>
          {!backendHealthy && (
            <Badge variant="critical" className="h-5 text-[10px] font-mono">
              CRITICAL
            </Badge>
          )}
          {configAuthFailure && (
            <Badge variant="critical" className="h-5 text-[10px] font-mono">
              AUTH
            </Badge>
          )}
        </div>
      </div>

      {(backendError || configError) && (
        <div className={`mt-1 flex items-center gap-2 border-t border-border/70 pt-1 text-[10px] font-mono ${
          !backendHealthy || configAuthFailure
            ? 'text-destructive'
            : 'text-[oklch(0.78_0.17_80)]'
        }`}>
          <AlertTriangle className="h-3 w-3 shrink-0" />
          <span className="truncate">
            {!backendHealthy && backendError
              ? `backend critical: ${backendError}`
              : configError instanceof Error
                ? `${configAuthFailure ? 'config auth failure' : 'config warning'}: ${configError.message} (using last known values)`
                : 'config warning: unknown error'}
          </span>
        </div>
      )}
    </footer>
  )
}
