'use client'

import React from 'react'
import { Info, ExternalLink, Terminal, History, Database, Code, TriangleAlert } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

export interface IntelInspectorSelection {
  kind: 'stage' | 'failure' | 'matrix-cell'
  title: string
  subtitle: string
  status: string
  rawMetadata: Record<string, unknown>
  trace: Array<{
    label: string
    status: string
    time?: string | null
  }>
  linkedEntities: string[]
  notes?: string[]
}

interface IntelInspectorProps {
  selection: IntelInspectorSelection | null
  dataError?: string | null
}

export function IntelInspector({ selection, dataError }: IntelInspectorProps) {
  return (
    <div className="h-full border-l border-border bg-muted/10 flex flex-col">
      <div className="p-4 border-b border-border bg-background/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-primary" />
          <h2 className="text-xs font-mono font-bold tracking-widest uppercase">INSPECTOR_PANE</h2>
        </div>
        <div className="text-[10px] font-mono text-muted-foreground animate-pulse">
          {selection ? 'LIVE' : 'READY...'}
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6">
          {dataError ? (
            <div className="terminal-panel p-4 border border-destructive/40 bg-destructive/10 rounded-md">
              <div className="flex items-center gap-2 text-destructive mb-2">
                <TriangleAlert className="h-4 w-4" />
                <span className="text-xs font-mono font-bold tracking-tight">DATA_STREAM_ERROR</span>
              </div>
              <p className="text-[11px] text-muted-foreground font-mono leading-relaxed break-words">
                {dataError}
              </p>
            </div>
          ) : (
            <div className="terminal-panel p-4 border border-primary/20 bg-primary/5 rounded-md">
              <div className="flex items-center gap-2 text-primary mb-2">
                <Info className="h-4 w-4" />
                <span className="text-xs font-mono font-bold tracking-tight">OPERATIONAL_GUIDE</span>
              </div>
              <p className="text-[11px] text-muted-foreground font-mono leading-relaxed">
                {selection
                  ? 'Inspector payload reflects the live item you selected. Missing provenance details are shown explicitly instead of synthetic placeholders.'
                  : 'Select any pipeline node, diagnostic cell, or failure row to inspect live metadata. This surface no longer renders sample data when nothing is selected.'}
              </p>
            </div>
          )}

          <Separator className="bg-border" />

          <div className="space-y-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Code className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase">RAW_METADATA_PREVIEW</span>
            </div>
            <div className="bg-black/40 p-3 rounded border border-border/50 font-mono text-[10px] text-primary/80 overflow-hidden">
              <pre className="whitespace-pre-wrap">
                {selection
                  ? JSON.stringify(selection.rawMetadata, null, 2)
                  : '{\n  "state": "idle",\n  "message": "No Intel Pulse node selected."\n}'}
              </pre>
            </div>
          </div>

          <Separator className="bg-border" />

          <div className="space-y-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <History className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase">PROVENANCE_TRACE</span>
            </div>
            <div className="space-y-3">
              {selection ? (
                selection.trace.map((step) => (
                  <TraceStep
                    key={`${selection.kind}-${step.label}`}
                    label={step.label}
                    status={step.status}
                    time={step.time ?? '--'}
                    color={traceColor(step.status)}
                  />
                ))
              ) : (
                <TraceStep
                  label="SELECTION"
                  status="PENDING"
                  time="--"
                  color="text-muted-foreground"
                />
              )}
            </div>
          </div>

          <Separator className="bg-border" />

          <div className="space-y-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Database className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase">LINKED_ENTITIES</span>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {(selection?.linkedEntities.length ? selection.linkedEntities : ['NO_LINKED_ENTITIES']).map((entity) => (
                <div
                  key={entity}
                  className="flex items-center justify-between p-2 rounded border border-border hover:border-primary/40 hover:bg-primary/5 transition-all group"
                >
                  <span className="text-[10px] font-mono text-muted-foreground break-all">{entity}</span>
                  <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
                </div>
              ))}
            </div>
          </div>

          {selection?.notes?.length ? (
            <>
              <Separator className="bg-border" />
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Info className="h-3 w-3" />
                  <span className="text-[10px] font-mono uppercase">INSPECTOR_NOTES</span>
                </div>
                <div className="space-y-2">
                  {selection.notes.map((note) => (
                    <div
                      key={note}
                      className="rounded border border-border/60 bg-black/20 px-3 py-2 text-[10px] font-mono text-muted-foreground"
                    >
                      {note}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : null}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border bg-background/50 font-mono text-[9px] text-muted-foreground">
        SYS_LOG: {selection ? `${selection.kind.toUpperCase()}_${selection.status}` : 'PULSE_READY_FOR_INPUT'}
      </div>
    </div>
  )
}

function traceColor(status: string): string {
  if (status === 'SUCCESS' || status === 'POPULATED' || status === 'NOMINAL') return 'text-primary'
  if (status === 'FAILED' || status === 'CRITICAL') return 'text-destructive'
  if (status === 'SPARSE' || status === 'PENDING' || status === 'DEGRADED') return 'text-[oklch(0.78_0.17_80)]'
  return 'text-muted-foreground'
}

function TraceStep({ label, status, time, color }: { label: string, status: string, time: string, color: string }) {
  return (
    <div className="flex items-center justify-between text-[10px] font-mono">
      <div className="flex items-center gap-2">
        <div className={cn("h-1.5 w-1.5 rounded-full", status === 'SUCCESS' ? "bg-primary" : status === 'PENDING' ? "bg-[oklch(0.78_0.17_80)] animate-pulse" : "bg-muted")} />
        <span className="text-muted-foreground">{label}</span>
      </div>
      <div className="flex gap-3">
        <span className={cn("font-bold", color)}>{status}</span>
        <span className="text-muted-foreground opacity-50">{time}</span>
      </div>
    </div>
  )
}
