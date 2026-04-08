'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  AlertTriangle,
  Cpu,
  MessageSquare,
  Settings2,
  RefreshCw,
  CheckCircle2,
  History,
  Newspaper,
  Gauge,
  Activity,
  Zap,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { Badge } from '@/components/ui/badge'
import type { ServiceHealth } from '@/lib/cockpit-types'
import { useCockpitStore, AVAILABLE_CHAT_MODELS } from '@/lib/cockpit-store'

interface CockpitSidebarProps {
  backendHealthy: boolean
  backendLastHealthyAt: Date | null
  backendError: string | null
  gpuHealth: ServiceHealth | null
  sessionCost: number
}

interface ConfigSummary {
  model: string | null
  maxTokens: number | null
  temperature: number | null
  routingPolicy: string | null
  profile: string | null
}

interface ConfigNotice {
  level: 'warning' | 'error' | 'critical'
  message: string
}

const INITIAL_CONFIG_SUMMARY: ConfigSummary = {
  model: null,
  maxTokens: null,
  temperature: null,
  routingPolicy: null,
  profile: null,
}

const navItems = [
  { href: '/', icon: MessageSquare, label: 'Chat', shortcut: '1' },
  { href: '/operations', icon: Settings2, label: 'Operations', shortcut: '2' },
  { href: '/updater', icon: RefreshCw, label: 'Updater', shortcut: '3' },
  { href: '/verification', icon: CheckCircle2, label: 'Verification', shortcut: '4' },
  { href: '/history', icon: History, label: 'History', shortcut: '5' },
  { href: '/settings', icon: Gauge, label: 'Settings', shortcut: '6' },
  { href: '/news', icon: Newspaper, label: 'News', shortcut: '7' },
]

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

function formatClock(time: Date | null): string {
  if (!time) return 'unknown'
  return time.toLocaleTimeString('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export function CockpitSidebar({
  backendHealthy,
  backendLastHealthyAt,
  backendError,
  gpuHealth,
  sessionCost,
}: CockpitSidebarProps) {
  const pathname = usePathname()
  const { chatModel } = useCockpitStore()
  const [configSummary, setConfigSummary] = useState<ConfigSummary>(INITIAL_CONFIG_SUMMARY)
  const [configNotice, setConfigNotice] = useState<ConfigNotice | null>(null)
  const [lastConfigSyncAt, setLastConfigSyncAt] = useState<Date | null>(null)

  useEffect(() => {
    let cancelled = false

    async function pollConfig() {
      try {
        const response = await fetch('/api/cockpit/config', { cache: 'no-store' })
        if (!response.ok) {
          if (!cancelled) {
            const isAuthFailure = response.status === 401 || response.status === 403
            setConfigNotice({
              level: isAuthFailure ? 'critical' : backendHealthy ? 'warning' : 'error',
              message: isAuthFailure
                ? `Config auth failure (${response.status})`
                : `Config endpoint unavailable (${response.status})`,
            })
          }
          return
        }

        const payload = (await response.json()) as Record<string, unknown>

        if (cancelled) return

        setConfigSummary((prev) => ({
          model: readString(payload.llm_model) ?? readString(payload.model) ?? prev.model,
          maxTokens: readNumber(payload.max_tokens) ?? prev.maxTokens,
          temperature: readNumber(payload.temperature) ?? prev.temperature,
          routingPolicy: readString(payload.routing_policy) ?? prev.routingPolicy,
          profile: readString(payload.profile) ?? prev.profile,
        }))
        setLastConfigSyncAt(new Date())
        setConfigNotice(null)
      } catch (error) {
        if (cancelled) return
        setConfigNotice({
          level: backendHealthy ? 'warning' : 'critical',
          message:
            error instanceof Error
              ? `Config refresh failed: ${error.message}`
              : 'Config refresh failed',
        })
      }
    }

    pollConfig()
    const interval = setInterval(pollConfig, 30_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [backendHealthy])

  useEffect(() => {
    if (configNotice?.level !== 'warning') return
    const timeout = setTimeout(() => {
      setConfigNotice((current) => (current?.level === 'warning' ? null : current))
    }, 8_000)
    return () => clearTimeout(timeout)
  }, [configNotice])

  const modelLabel = useMemo(() => {
    const configuredModel = configSummary.model ?? chatModel
    return AVAILABLE_CHAT_MODELS.find((model) => model.id === configuredModel)?.label ?? configuredModel
  }, [chatModel, configSummary.model])

  const displayNotice = backendHealthy
    ? configNotice
    : {
        level: 'critical' as const,
        message: backendError ?? configNotice?.message ?? 'Backend is unavailable',
      }

  const gpuSummary = useMemo(() => {
    const gpus = Array.isArray(gpuHealth?.details?.gpus)
      ? (gpuHealth?.details?.gpus as Array<Record<string, unknown>>)
      : []
    if (gpus.length === 0) return gpuHealth?.error ?? 'unavailable'
    const first = gpus[0]
    const name = typeof first.name === 'string' ? first.name : 'GPU'
    const util =
      typeof first.util_percent === 'number'
        ? `${Math.round(first.util_percent)}%`
        : 'n/a'
    const used = typeof first.mem_used_mib === 'number' ? Math.round(first.mem_used_mib) : null
    const total = typeof first.mem_total_mib === 'number' ? Math.round(first.mem_total_mib) : null
    const mem = used !== null && total !== null ? `${used}/${total} MiB` : 'n/a'
    return `${name} ${util} ${mem}`
  }, [gpuHealth])

  const gpuHealthy = gpuHealth?.status === 'healthy'

  return (
    <Sidebar
      collapsible="icon"
      className="terminal-panel supports-[backdrop-filter:blur(0)]:backdrop-blur-sm"
    >
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">Financial Cockpit</span>
            <span className="text-xs text-muted-foreground">Analysis Workstation</span>
          </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton 
                    asChild 
                    isActive={pathname === item.href}
                    tooltip={item.label}
                    className="transition-colors duration-150"
                  >
                    <Link href={item.href}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.label}</span>
                      <kbd className="ml-auto text-[10px] text-muted-foreground opacity-60 group-data-[collapsible=icon]:hidden">
                        {item.shortcut}
                      </kbd>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>System Status</SidebarGroupLabel>
          <SidebarGroupContent>
            <div className="space-y-1 px-2 group-data-[collapsible=icon]:hidden">
              <div className="flex items-center justify-between text-xs py-1 font-mono">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${
                    backendHealthy
                      ? 'bg-[oklch(0.69_0.22_145)] status-dot-running'
                      : 'bg-[oklch(0.58_0.22_25)]'
                  }`} />
                  <span className="text-muted-foreground">
                    Backend: {backendHealthy ? 'RUNNING' : 'DOWN'}
                  </span>
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground/90 pl-4 font-mono">
                last healthy: {formatClock(backendLastHealthyAt)}
              </div>
              <div className="flex items-center justify-between text-xs py-1 font-mono">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${
                    gpuHealthy
                      ? 'bg-[oklch(0.7_0.18_205)] status-dot-running'
                      : 'bg-[oklch(0.7_0.05_250)]'
                  }`} />
                  <span className="text-muted-foreground">
                    GPU: {gpuHealthy ? 'VISIBLE' : (gpuHealth?.status ?? 'UNKNOWN').toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground/90 pl-4 font-mono break-words">
                {gpuSummary}
              </div>
              <div className="text-[11px] text-muted-foreground/90 pl-4 font-mono">
                config sync: {formatClock(lastConfigSyncAt)}
              </div>

              <div className="mt-2 space-y-1 rounded border border-sidebar-border/80 bg-black/20 px-2 py-1.5">
                <div className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <Cpu className="h-3 w-3" />
                  Cockpit Config
                </div>
                <div className="text-[11px] text-foreground font-mono">model: {modelLabel}</div>
                <div className="text-[11px] text-muted-foreground font-mono">
                  max_tokens: {configSummary.maxTokens ?? '--'} | temp:{' '}
                  {configSummary.temperature?.toFixed(2) ?? '--'}
                </div>
                <div className="text-[11px] text-muted-foreground font-mono">
                  route: {configSummary.routingPolicy ?? '--'} | profile: {configSummary.profile ?? '--'}
                </div>
              </div>

              {displayNotice?.message && (
                <div
                  className={`mt-2 flex items-start gap-1 rounded border px-2 py-1.5 text-[11px] font-mono ${
                    displayNotice.level === 'critical'
                      ? 'border-destructive/70 bg-destructive/15 text-destructive'
                      : displayNotice.level === 'error'
                      ? 'border-destructive/40 bg-destructive/10 text-destructive'
                      : 'border-[oklch(0.78_0.17_80/0.4)] bg-[oklch(0.78_0.17_80/0.08)] text-[oklch(0.78_0.17_80)]'
                  }`}
                  role="status"
                >
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                  <span>{displayNotice.level === 'critical' ? `[CRITICAL] ${displayNotice.message}` : displayNotice.message}</span>
                </div>
              )}
            </div>
            <div className="px-2 group-data-[collapsible=icon]:block hidden">
              <div className="flex items-center justify-center gap-1">
                <Activity
                  className={`h-4 w-4 ${backendHealthy ? 'text-[oklch(0.69_0.22_145)]' : 'text-destructive'}`}
                />
                <Cpu
                  className={`h-4 w-4 ${gpuHealthy ? 'text-[oklch(0.7_0.18_205)]' : 'text-muted-foreground/60'}`}
                />
              </div>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        <div className="flex items-center justify-between px-2 py-2 group-data-[collapsible=icon]:hidden">
          {backendHealthy ? (
            <Badge variant="outline" className="text-xs font-mono">
              1/1 Services
            </Badge>
          ) : (
            <Badge variant="critical" className="text-xs font-mono">
              CRITICAL: BACKEND DOWN
            </Badge>
          )}
          <div className="text-xs text-muted-foreground font-mono">
            ${sessionCost.toFixed(4)}
          </div>
        </div>
        <div className="px-2 py-2 group-data-[collapsible=icon]:block hidden">
          <Badge variant="outline" className="text-[10px] font-mono w-full justify-center">
            {backendHealthy ? '1/1' : '0/1'}
          </Badge>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
