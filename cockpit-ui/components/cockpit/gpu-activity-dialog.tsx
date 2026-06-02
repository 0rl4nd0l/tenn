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

interface GpuActivityDialogProps {
  gpuHealth: ServiceHealth | null
  children: React.ReactNode
  summaryFooter?: React.ReactNode
}

export interface GpuRecord {
  name?: string
  temp_c?: number | null
  util_percent?: number | null
  mem_used_mib?: number | null
  mem_total_mib?: number | null
  power_draw_w?: number | null
  power_limit_w?: number | null
  fan_speed_pct?: number | null
  mem_util_percent?: number | null
  clock_gr_mhz?: number | null
  clock_mem_mhz?: number | null
  pstate?: string | null
  task_label?: string
  process_name?: string
  gpu_name?: string
  command?: string
  pid?: number
  used_gpu_memory_mib?: number | null
}

const POLL_MS = 2_000

function formatMem(value: unknown): string {
  return typeof value === 'number' ? `${Math.round(value)} MiB` : 'n/a'
}

function fmt(value: unknown, unit: string, decimals = 0): string {
  if (typeof value !== 'number') return 'n/a'
  return `${value.toFixed(decimals)}${unit}`
}

function readGpusFromHealth(health: ServiceHealth | null): GpuRecord[] {
  return Array.isArray(health?.details?.gpus)
    ? (health!.details!.gpus as GpuRecord[])
    : []
}

function readProcessesFromHealth(health: ServiceHealth | null): GpuRecord[] {
  return Array.isArray(health?.details?.processes)
    ? (health!.details!.processes as GpuRecord[])
    : []
}

export function readGpuSummary(health: ServiceHealth | null): string {
  const gpus = readGpusFromHealth(health)
  if (gpus.length === 0) return health?.error ?? 'unavailable'
  const g = gpus[0]
  const name = g.name ?? 'GPU'
  const temp = typeof g.temp_c === 'number' ? `${Math.round(g.temp_c)}°C` : null
  const util = typeof g.util_percent === 'number' ? `${Math.round(g.util_percent)}%` : 'n/a'
  const used = typeof g.mem_used_mib === 'number' ? Math.round(g.mem_used_mib) : null
  const total = typeof g.mem_total_mib === 'number' ? Math.round(g.mem_total_mib) : null
  const mem = used !== null && total !== null ? `${used}/${total} MiB` : 'n/a'
  return `${name}${temp ? ` ${temp}` : ''} ${util} ${mem}`
}

export function getGpuSummary(health: ServiceHealth | null): string {
  return readGpuSummary(health)
}

export function getGpuProcesses(health: ServiceHealth | null): GpuRecord[] {
  return readProcessesFromHealth(health)
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground/75 shrink-0">{label}</span>
      <span className="font-mono text-foreground/90 text-right">{value}</span>
    </div>
  )
}

function GpuMetricsPanel({ gpu }: { gpu: GpuRecord }) {
  const memUsed = typeof gpu.mem_used_mib === 'number' ? gpu.mem_used_mib : null
  const memTotal = typeof gpu.mem_total_mib === 'number' ? gpu.mem_total_mib : null
  const memPct = memUsed !== null && memTotal !== null && memTotal > 0
    ? Math.round((memUsed / memTotal) * 100)
    : null

  return (
    <div className="space-y-1.5 text-xs">
      <MetricRow label="Compute util" value={fmt(gpu.util_percent, '%')} />
      <MetricRow label="Memory util" value={fmt(gpu.mem_util_percent, '%')} />
      <MetricRow label="Temperature" value={fmt(gpu.temp_c, '°C')} />
      <MetricRow label="VRAM used" value={
        memUsed !== null && memTotal !== null
          ? `${formatMem(memUsed)} / ${formatMem(memTotal)}${memPct !== null ? ` (${memPct}%)` : ''}`
          : 'n/a'
      } />
      <MetricRow label="Power draw" value={fmt(gpu.power_draw_w, ' W', 1)} />
      <MetricRow label="Power limit" value={fmt(gpu.power_limit_w, ' W', 1)} />
      {gpu.fan_speed_pct !== null && gpu.fan_speed_pct !== undefined && (
        <MetricRow label="Fan speed" value={fmt(gpu.fan_speed_pct, '%')} />
      )}
      <MetricRow label="Graphics clock" value={fmt(gpu.clock_gr_mhz, ' MHz')} />
      <MetricRow label="Memory clock" value={fmt(gpu.clock_mem_mhz, ' MHz')} />
      {gpu.pstate && <MetricRow label="Perf state" value={gpu.pstate} />}
    </div>
  )
}

export function GpuActivityDialog({ gpuHealth, children, summaryFooter }: GpuActivityDialogProps) {
  const [open, setOpen] = useState(false)
  const [liveGpus, setLiveGpus] = useState<GpuRecord[]>(readGpusFromHealth(gpuHealth))
  const [liveProcesses, setLiveProcesses] = useState<GpuRecord[]>(readProcessesFromHealth(gpuHealth))
  const [lastChecked, setLastChecked] = useState<Date | null>(gpuHealth?.lastChecked ?? null)
  const [polling, setPolling] = useState(false)
  const [pollError, setPollError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Sync initial data from parent when not open
  useEffect(() => {
    if (!open) {
      setLiveGpus(readGpusFromHealth(gpuHealth))
      setLiveProcesses(readProcessesFromHealth(gpuHealth))
      setLastChecked(gpuHealth?.lastChecked ?? null)
    }
  }, [gpuHealth, open])

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
        const res = await fetch('/api/cockpit/metrics/gpu', {
          cache: 'no-store',
          headers: buildCockpitApiHeaders(),
        })
        if (!res.ok) throw new Error(`${res.status}`)
        const data = await res.json() as { details?: { gpus?: GpuRecord[]; processes?: GpuRecord[] }; error?: string }
        setLiveGpus(Array.isArray(data.details?.gpus) ? data.details!.gpus! : [])
        setLiveProcesses(Array.isArray(data.details?.processes) ? data.details!.processes! : [])
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

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-3xl font-mono max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            GPU Activity
            {polling && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
          </DialogTitle>
          <DialogDescription>
            Live GPU metrics — polling every {POLL_MS / 1000}s via nvidia-smi.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-xs">
          {pollError && (
            <div className="rounded border border-destructive/50 bg-destructive/10 px-3 py-2 text-destructive text-xs">
              Poll error: {pollError}
            </div>
          )}

          {liveGpus.length === 0 ? (
            <div className="rounded border border-border/80 bg-black/20 p-3 text-muted-foreground/80">
              No GPU data available.
            </div>
          ) : (
            liveGpus.map((gpu, i) => (
              <div key={i} className="rounded border border-border/80 bg-black/20 p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-[11px] font-semibold text-foreground">{gpu.name ?? 'GPU'}</div>
                  <div className="text-[10px] text-muted-foreground/70">
                    {formatClock(lastChecked)}
                  </div>
                </div>
                <GpuMetricsPanel gpu={gpu} />
                {summaryFooter && i === 0 && <div className="mt-2">{summaryFooter}</div>}
              </div>
            ))
          )}

          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2">
              Processes Using GPU
            </div>
            {liveProcesses.length === 0 ? (
              <div className="text-muted-foreground/80">No active GPU compute processes reported.</div>
            ) : (
              <div className="max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                {liveProcesses.map((proc, i) => (
                  <div key={`${proc.pid ?? 'p'}-${i}`} className="rounded border border-border/70 bg-background/40 p-3">
                    <div className="flex flex-wrap items-center gap-2 text-foreground">
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-primary">
                        {proc.task_label ?? 'GPU task'}
                      </span>
                      <span>{proc.process_name ?? 'process'}</span>
                      <span className="text-muted-foreground/70">on {proc.gpu_name ?? 'GPU'}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground/85">
                      <span>PID: {proc.pid ?? 'n/a'}</span>
                      <span>VRAM: {formatMem(proc.used_gpu_memory_mib)}</span>
                    </div>
                    <div className="mt-2 break-all text-[11px] text-muted-foreground/75">
                      {proc.command ?? 'Command unavailable'}
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
