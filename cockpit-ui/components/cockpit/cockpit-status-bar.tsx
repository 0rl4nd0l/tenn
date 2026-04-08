'use client'

import { AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useCockpitStore, AVAILABLE_CHAT_MODELS } from '@/lib/cockpit-store'
import { useQuery } from '@tanstack/react-query'

interface CockpitStatusBarProps {
  backendHealthy: boolean
  backendLastHealthyAt: Date | null
  backendError: string | null
}

interface ConfigSnapshot {
  model: string | null
  maxTokens: number | null
  temperature: number | null
  profile: string | null
}

function readNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function readString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function parseConfig(payload: Record<string, unknown> | undefined): ConfigSnapshot {
  return {
    model: readString(payload?.llm_model) ?? readString(payload?.model),
    maxTokens: readNumber(payload?.max_tokens),
    temperature: readNumber(payload?.temperature),
    profile: readString(payload?.profile),
  }
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
  const { sessionStats, chatModel } = useCockpitStore()
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

  const config = parseConfig(configData)
  const configModel = config.model ?? chatModel
  const modelLabel = AVAILABLE_CHAT_MODELS.find((m) => m.id === configModel)?.label ?? configModel
  const configAuthFailure = configError instanceof Error && /(401|403)/.test(configError.message)

  return (
    <footer className="shrink-0 border-t border-border bg-card/95 px-4 py-1 text-xs terminal-panel">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            Model: {modelLabel}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            {config.maxTokens ? `max ${config.maxTokens}` : 'max --'}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono">
            {config.temperature !== null ? `temp ${config.temperature.toFixed(2)}` : 'temp --'}
          </Badge>
          <Badge variant="outline" className="h-5 text-[10px] font-mono hidden lg:inline-flex">
            profile: {config.profile ?? '--'}
          </Badge>
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
