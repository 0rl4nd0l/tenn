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

interface GpuActivityDialogProps {
  gpuHealth: ServiceHealth | null
  children: React.ReactNode
  summaryFooter?: React.ReactNode
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

function formatGpuMemory(value: unknown): string {
  return typeof value === 'number' ? `${Math.round(value)} MiB` : 'n/a'
}

function readGpuSummary(gpuHealth: ServiceHealth | null): string {
  const gpus = Array.isArray(gpuHealth?.details?.gpus)
    ? (gpuHealth.details.gpus as Array<Record<string, unknown>>)
    : []
  if (gpus.length === 0) return gpuHealth?.error ?? 'unavailable'

  const first = gpus[0]
  const name = typeof first.name === 'string' ? first.name : 'GPU'
  const temp = typeof first.temp_c === 'number' ? `${Math.round(first.temp_c)}C` : null
  const util = typeof first.util_percent === 'number' ? `${Math.round(first.util_percent)}%` : 'n/a'
  const used = typeof first.mem_used_mib === 'number' ? Math.round(first.mem_used_mib) : null
  const total = typeof first.mem_total_mib === 'number' ? Math.round(first.mem_total_mib) : null
  const mem = used !== null && total !== null ? `${used}/${total} MiB` : 'n/a'
  return `${name}${temp ? ` ${temp}` : ''} ${util} ${mem}`
}

function readGpuProcesses(gpuHealth: ServiceHealth | null): Array<Record<string, unknown>> {
  return Array.isArray(gpuHealth?.details?.processes)
    ? (gpuHealth.details.processes as Array<Record<string, unknown>>)
    : []
}

export function GpuActivityDialog({ gpuHealth, children, summaryFooter }: GpuActivityDialogProps) {
  const gpuSummary = readGpuSummary(gpuHealth)
  const gpuProcesses = readGpuProcesses(gpuHealth)

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-3xl font-mono">
        <DialogHeader>
          <DialogTitle>GPU Activity</DialogTitle>
          <DialogDescription>
            Live host GPU visibility from the Cockpit health probe.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-xs">
          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Summary</div>
            <div className="mt-2 whitespace-pre-wrap break-words text-muted-foreground/90">
              {gpuSummary}
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground/75">
              Last checked: {formatClock(gpuHealth?.lastChecked)}
            </div>
            {summaryFooter ? <div className="mt-2">{summaryFooter}</div> : null}
          </div>

          <div className="rounded border border-border/80 bg-black/20 p-3">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Processes Using GPU</div>
            {gpuProcesses.length === 0 ? (
              <div className="mt-2 text-muted-foreground/80">No active GPU compute processes were reported.</div>
            ) : (
              <div className="mt-2 max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                {gpuProcesses.map((process, index) => {
                  const taskLabel = typeof process.task_label === 'string' ? process.task_label : 'GPU task'
                  const processName = typeof process.process_name === 'string' ? process.process_name : 'process'
                  const gpuName = typeof process.gpu_name === 'string' ? process.gpu_name : 'GPU'
                  const command = typeof process.command === 'string' ? process.command : null
                  const pid = typeof process.pid === 'number' ? process.pid : null

                  return (
                    <div key={`${pid ?? 'pid'}-${index}`} className="rounded border border-border/70 bg-background/40 p-3">
                      <div className="flex flex-wrap items-center gap-2 text-foreground">
                        <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-primary">
                          {taskLabel}
                        </span>
                        <span>{processName}</span>
                        <span className="text-muted-foreground/70">on {gpuName}</span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground/85">
                        <span>PID: {pid ?? 'n/a'}</span>
                        <span>VRAM: {formatGpuMemory(process.used_gpu_memory_mib)}</span>
                      </div>
                      <div className="mt-2 break-all text-[11px] text-muted-foreground/75">
                        {command ?? 'Command unavailable'}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function getGpuSummary(gpuHealth: ServiceHealth | null): string {
  return readGpuSummary(gpuHealth)
}

export function getGpuProcesses(gpuHealth: ServiceHealth | null): Array<Record<string, unknown>> {
  return readGpuProcesses(gpuHealth)
}
