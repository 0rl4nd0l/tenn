'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import type { ServiceHealth } from '@/lib/cockpit-types'

interface HostActivityDialogProps {
  hostHealth: ServiceHealth | null
  children: React.ReactNode
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

function readHostDetails(hostHealth: ServiceHealth | null): Record<string, unknown> {
  return hostHealth?.details && typeof hostHealth.details === 'object'
    ? hostHealth.details
    : {}
}

function formatProcessMetric(value: unknown, suffix: string): string {
  return typeof value === 'number' ? `${value}${suffix}` : 'n/a'
}

export function getHostSummary(hostHealth: ServiceHealth | null): string {
  const details = readHostDetails(hostHealth)
  const cpu = details.cpu as Record<string, unknown> | undefined
  const memory = details.memory as Record<string, unknown> | undefined

  if (!cpu && !memory) return hostHealth?.error ?? 'unavailable'

  const cores = typeof cpu?.core_count === 'number' ? `${cpu.core_count}c` : 'n/a'
  const load = typeof cpu?.normalized_load_percent === 'number' ? `${cpu.normalized_load_percent}% load` : 'n/a load'
  const ram = typeof memory?.used_gib === 'number' && typeof memory?.total_gib === 'number'
    ? `${memory.used_gib}/${memory.total_gib} GiB`
    : 'n/a RAM'

  return `CPU ${cores} ${load} | RAM ${ram}`
}

export function HostActivityDialog({ hostHealth, children }: HostActivityDialogProps) {
  const details = readHostDetails(hostHealth)
  const cpu = details.cpu as Record<string, unknown> | undefined
  const memory = details.memory as Record<string, unknown> | undefined
  const disks = Array.isArray(details.disks) ? (details.disks as Array<Record<string, unknown>>) : []
  const processes = Array.isArray(details.top_processes)
    ? (details.top_processes as Array<Record<string, unknown>>)
    : []

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-4xl font-mono">
        <DialogHeader>
          <DialogTitle>Host Activity</DialogTitle>
          <DialogDescription>
            Live CPU, RAM, disk, and top-process visibility from the Cockpit health probe.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-xs">
          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Summary</div>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              <div>
                <div className="text-muted-foreground/75">CPU</div>
                <div className="mt-1 text-muted-foreground/90">
                  {typeof cpu?.core_count === 'number' ? `${cpu.core_count} cores` : 'n/a'}
                  {typeof cpu?.normalized_load_percent === 'number' ? ` | ${cpu.normalized_load_percent}% normalized load` : ''}
                </div>
                <div className="mt-1 text-muted-foreground/75">
                  {typeof cpu?.load_1m === 'number' ? `1m ${cpu.load_1m}` : '1m n/a'}
                  {typeof cpu?.load_5m === 'number' ? ` | 5m ${cpu.load_5m}` : ''}
                  {typeof cpu?.load_15m === 'number' ? ` | 15m ${cpu.load_15m}` : ''}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground/75">Memory</div>
                <div className="mt-1 text-muted-foreground/90">
                  {typeof memory?.used_gib === 'number' && typeof memory?.total_gib === 'number'
                    ? `${memory.used_gib} / ${memory.total_gib} GiB`
                    : 'n/a'}
                </div>
                <div className="mt-1 text-muted-foreground/75">
                  {typeof memory?.used_percent === 'number' ? `${memory.used_percent}% used` : 'usage unavailable'}
                </div>
              </div>
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground/75">
              Last checked: {formatClock(hostHealth?.lastChecked)}
            </div>
          </div>

          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Disks</div>
            {disks.length === 0 ? (
              <div className="mt-2 text-muted-foreground/80">No disk data reported.</div>
            ) : (
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                {disks.map((disk, index) => (
                  <div key={`${String(disk.mount ?? 'disk')}-${index}`} className="rounded border border-border/70 bg-background/40 p-3">
                    <div className="text-foreground">{String(disk.mount ?? 'mount')}</div>
                    <div className="mt-1 text-muted-foreground/85">
                      {formatProcessMetric(disk.used_gib, ' GiB')} / {formatProcessMetric(disk.total_gib, ' GiB')}
                    </div>
                    <div className="mt-1 text-muted-foreground/75">
                      {formatProcessMetric(disk.used_percent, '%')} used
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Top Processes by Memory</div>
            {processes.length === 0 ? (
              <div className="mt-2 text-muted-foreground/80">No process data reported.</div>
            ) : (
              <div className="mt-2 max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                {processes.map((process, index) => (
                  <div key={`${String(process.pid ?? 'pid')}-${index}`} className="rounded border border-border/70 bg-background/40 p-3">
                    <div className="flex flex-wrap items-center gap-2 text-foreground">
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-primary">
                        {String(process.command_name ?? 'process')}
                      </span>
                      <span>PID {String(process.pid ?? 'n/a')}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground/85">
                      <span>CPU: {formatProcessMetric(process.cpu_percent, '%')}</span>
                      <span>MEM: {formatProcessMetric(process.mem_percent, '%')}</span>
                      <span>RSS: {formatProcessMetric(process.rss_mib, ' MiB')}</span>
                    </div>
                    <div className="mt-2 break-all text-[11px] text-muted-foreground/75">
                      {typeof process.command === 'string' ? process.command : 'Command unavailable'}
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
