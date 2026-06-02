'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { buildCockpitApiHeaders } from '@/lib/cockpit-api-headers'
import type { ServiceHealth } from '@/lib/cockpit-types'

interface HostActivityDialogProps {
  hostHealth: ServiceHealth | null
  children: React.ReactNode
}

interface HostDetails {
  cpu?: {
    core_count?: number
    logical_count?: number
    load_1m?: number
    load_5m?: number
    load_15m?: number
    normalized_load_percent?: number
  }
  memory?: {
    total_gib?: number
    used_gib?: number
    available_gib?: number
    used_percent?: number
    swap_total_gib?: number
    swap_used_gib?: number
    swap_used_percent?: number
  }
  disks?: Array<{
    mount?: string
    total_gib?: number
    used_gib?: number
    used_percent?: number
  }>
  top_processes?: Array<{
    pid?: number
    command_name?: string
    command?: string
    cpu_percent?: number
    mem_percent?: number
    rss_mib?: number | null
  }>
}

const POLL_MS = 2_000

function readDetails(health: ServiceHealth | null): HostDetails {
  return health?.details && typeof health.details === 'object'
    ? (health.details as HostDetails)
    : {}
}

export function getHostSummary(health: ServiceHealth | null): string {
  const d = readDetails(health)
  if (!d.cpu && !d.memory) return health?.error ?? 'unavailable'
  const cores = typeof d.cpu?.core_count === 'number' ? `${d.cpu.core_count}c` : 'n/a'
  const load = typeof d.cpu?.normalized_load_percent === 'number'
    ? `${d.cpu.normalized_load_percent}% load`
    : 'n/a load'
  const ram =
    typeof d.memory?.used_gib === 'number' && typeof d.memory?.total_gib === 'number'
      ? `${d.memory.used_gib}/${d.memory.total_gib} GiB`
      : 'n/a RAM'
  return `CPU ${cores} ${load} | RAM ${ram}`
}

function fmt(v: unknown, unit: string, decimals = 0): string {
  if (typeof v !== 'number') return 'n/a'
  return `${v.toFixed(decimals)}${unit}`
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground/75 shrink-0">{label}</span>
      <span className="font-mono text-foreground/90 text-right">{value}</span>
    </div>
  )
}

function LoadBar({ pct }: { pct: number }) {
  const clamped = Math.min(100, Math.max(0, pct))
  const color = clamped > 85 ? 'bg-destructive' : clamped > 60 ? 'bg-yellow-500' : 'bg-primary'
  return (
    <div className="mt-1 h-1.5 w-full rounded-full bg-muted/40 overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${clamped}%` }} />
    </div>
  )
}

export function HostActivityDialog({ hostHealth, children }: HostActivityDialogProps) {
  const [open, setOpen] = useState(false)
  const [details, setDetails] = useState<HostDetails>(readDetails(hostHealth))
  const [lastChecked, setLastChecked] = useState<Date | null>(hostHealth?.lastChecked ?? null)
  const [polling, setPolling] = useState(false)
  const [pollError, setPollError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!open) {
      setDetails(readDetails(hostHealth))
      setLastChecked(hostHealth?.lastChecked ?? null)
    }
  }, [hostHealth, open])

  useEffect(() => {
    if (!open) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    async function poll() {
      setPolling(true)
      try {
        const res = await fetch('/api/cockpit/metrics/host', {
          cache: 'no-store',
          headers: buildCockpitApiHeaders(),
        })
        if (!res.ok) throw new Error(`${res.status}`)
        const data = await res.json() as { details?: HostDetails; error?: string }
        setDetails(data.details ?? {})
        setLastChecked(new Date())
        setPollError(null)
      } catch (err) {
        setPollError(err instanceof Error ? err.message : 'Poll failed')
      } finally {
        setPolling(false)
      }
    }

    void poll()
    intervalRef.current = setInterval(() => void poll(), POLL_MS)
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [open])

  const formatClock = (d: Date | null) =>
    d
      ? d.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
      : '--:--:--'

  const cpu = details.cpu
  const memory = details.memory
  const disks = details.disks ?? []
  const procs = details.top_processes ?? []

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-4xl font-mono max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Host Activity
            {polling && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
          </DialogTitle>
          <DialogDescription>
            Live CPU, RAM, disk, and top-process metrics — polling every {POLL_MS / 1000}s.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-xs">
          {pollError && (
            <div className="rounded border border-destructive/50 bg-destructive/10 px-3 py-2 text-destructive">
              Poll error: {pollError}
            </div>
          )}

          {/* CPU + Memory */}
          <div className="rounded border border-border/80 bg-black/20 p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">CPU &amp; Memory</div>
              <div className="text-[10px] text-muted-foreground/70">{formatClock(lastChecked)}</div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground/60 mb-1">CPU</div>
                <MetricRow
                  label="Cores"
                  value={
                    cpu?.core_count != null
                      ? `${cpu.core_count} physical / ${cpu.logical_count ?? '?'} logical`
                      : 'n/a'
                  }
                />
                <MetricRow label="Normalized load" value={fmt(cpu?.normalized_load_percent, '%', 1)} />
                {typeof cpu?.normalized_load_percent === 'number' && (
                  <LoadBar pct={cpu.normalized_load_percent} />
                )}
                <MetricRow label="Load avg 1m" value={fmt(cpu?.load_1m, '', 2)} />
                <MetricRow label="Load avg 5m" value={fmt(cpu?.load_5m, '', 2)} />
                <MetricRow label="Load avg 15m" value={fmt(cpu?.load_15m, '', 2)} />
              </div>

              <div className="space-y-1.5">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground/60 mb-1">Memory</div>
                <MetricRow
                  label="RAM used"
                  value={
                    memory?.used_gib != null && memory?.total_gib != null
                      ? `${memory.used_gib} / ${memory.total_gib} GiB`
                      : 'n/a'
                  }
                />
                {typeof memory?.used_percent === 'number' && (
                  <>
                    <MetricRow label="RAM %" value={fmt(memory.used_percent, '%', 1)} />
                    <LoadBar pct={memory.used_percent} />
                  </>
                )}
                <MetricRow label="Available" value={fmt(memory?.available_gib, ' GiB', 2)} />
                {(memory?.swap_total_gib ?? 0) > 0 && (
                  <>
                    <MetricRow
                      label="Swap used"
                      value={
                        memory?.swap_used_gib != null && memory?.swap_total_gib != null
                          ? `${memory.swap_used_gib.toFixed(2)} / ${memory.swap_total_gib.toFixed(2)} GiB`
                          : 'n/a'
                      }
                    />
                    {typeof memory?.swap_used_percent === 'number' && (
                      <LoadBar pct={memory.swap_used_percent} />
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Disks */}
          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2">Disks</div>
            {disks.length === 0 ? (
              <div className="text-muted-foreground/80">No disk data reported.</div>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                {disks.map((disk, i) => (
                  <div key={`${disk.mount ?? 'disk'}-${i}`} className="rounded border border-border/70 bg-background/40 p-3 space-y-1">
                    <div className="text-foreground font-semibold">{disk.mount ?? 'mount'}</div>
                    <MetricRow
                      label="Used"
                      value={
                        disk.used_gib != null && disk.total_gib != null
                          ? `${disk.used_gib.toFixed(2)} / ${disk.total_gib.toFixed(2)} GiB`
                          : 'n/a'
                      }
                    />
                    {typeof disk.used_percent === 'number' && (
                      <LoadBar pct={disk.used_percent} />
                    )}
                    <div className="text-[10px] text-muted-foreground/70 text-right">
                      {fmt(disk.used_percent, '%', 1)} used
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top Processes */}
          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2">Top Processes by CPU</div>
            {procs.length === 0 ? (
              <div className="text-muted-foreground/80">No process data reported.</div>
            ) : (
              <div className="max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                {procs.map((proc, i) => (
                  <div key={`${proc.pid ?? 'p'}-${i}`} className="rounded border border-border/70 bg-background/40 p-3">
                    <div className="flex flex-wrap items-center gap-2 text-foreground">
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-primary">
                        {proc.command_name ?? 'process'}
                      </span>
                      <span>PID {proc.pid ?? 'n/a'}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground/85">
                      <span>CPU: {fmt(proc.cpu_percent, '%', 1)}</span>
                      <span>MEM: {fmt(proc.mem_percent, '%', 2)}</span>
                      {proc.rss_mib != null && <span>RSS: {fmt(proc.rss_mib, ' MiB', 1)}</span>}
                    </div>
                    <div className="mt-2 break-all text-[11px] text-muted-foreground/75">
                      {proc.command || proc.command_name || 'Command unavailable'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
