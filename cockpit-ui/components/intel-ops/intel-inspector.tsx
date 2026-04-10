'use client'

import React from 'react'
import { Info, ExternalLink, Terminal, History, Database, Code } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

export function IntelInspector() {
  return (
    <div className="h-full border-l border-border bg-muted/10 flex flex-col">
      <div className="p-4 border-b border-border bg-background/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-primary" />
          <h2 className="text-xs font-mono font-bold tracking-widest uppercase">INSPECTOR_PANE</h2>
        </div>
        <div className="text-[10px] font-mono text-muted-foreground animate-pulse">
          READY...
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6">
          {/* Default Empty State / Guidance */}
          <div className="terminal-panel p-4 border border-primary/20 bg-primary/5 rounded-md">
            <div className="flex items-center gap-2 text-primary mb-2">
              <Info className="h-4 w-4" />
              <span className="text-xs font-mono font-bold tracking-tight">OPERATIONAL_GUIDE</span>
            </div>
            <p className="text-[11px] text-muted-foreground font-mono leading-relaxed">
              Select any node in the pipeline or cell in the diagnostic matrix to inspect raw metadata, provenance chains, and validation logs.
            </p>
          </div>

          <Separator className="bg-border" />

          {/* Sample Metadata Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Code className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase">RAW_METADATA_PREVIEW</span>
            </div>
            <div className="bg-black/40 p-3 rounded border border-border/50 font-mono text-[10px] text-primary/80 overflow-hidden">
              <pre className="whitespace-pre-wrap">
{`{
  "entity_id": "TSLA_2025_Q1",
  "field": "EBITDA",
  "raw_value": "4.3B",
  "processed_value": 4300000000,
  "confidence": 0.94,
  "source_doc": "TSLA-2025-Q1-10Q.pdf",
  "page_ref": 12,
  "extraction_engine": "fin-bert-v2.1",
  "timestamp": "2026-04-10T12:04:22Z"
}`}
              </pre>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Provenance Chain */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <History className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase">PROVENANCE_TRACE</span>
            </div>
            <div className="space-y-3">
              <TraceStep label="INGESTION" status="SUCCESS" time="12:01:05" color="text-primary" />
              <TraceStep label="SEGMENTATION" status="SUCCESS" time="12:01:45" color="text-primary" />
              <TraceStep label="EXTRACTION" status="PENDING" time="12:02:10" color="text-[oklch(0.78_0.17_80)]" />
              <TraceStep label="EVALUATION" status="QUEUED" time="--" color="text-muted-foreground" />
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Linked Data */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Database className="h-3 w-3" />
              <span className="text-[10px] font-mono uppercase">LINKED_ENTITIES</span>
            </div>
            <div className="grid grid-cols-1 gap-2">
              <button className="flex items-center justify-between p-2 rounded border border-border hover:border-primary/40 hover:bg-primary/5 transition-all group">
                <span className="text-[10px] font-mono text-muted-foreground">TSLA-2025-Q1-10Q.pdf</span>
                <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
              </button>
              <button className="flex items-center justify-between p-2 rounded border border-border hover:border-primary/40 hover:bg-primary/5 transition-all group">
                <span className="text-[10px] font-mono text-muted-foreground">SEC_EDGAR_ENTRY: 0001652044-25-000012</span>
                <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
              </button>
            </div>
          </div>
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border bg-background/50 font-mono text-[9px] text-muted-foreground">
        SYS_LOG: PULSE_READY_FOR_INPUT
      </div>
    </div>
  )
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
