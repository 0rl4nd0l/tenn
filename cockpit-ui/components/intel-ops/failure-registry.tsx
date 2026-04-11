'use client'

import React from 'react'
import { AlertTriangle, ChevronRight, FileX, ShieldX, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { IntelPulseFailure } from '@/lib/cockpit-types'

interface FailureRegistryProps {
  compact?: boolean
  failures?: IntelPulseFailure[]
  unavailableMessage?: string | null
  onFailureSelect?: (failure: IntelPulseFailure) => void
}

export function FailureRegistry({
  compact,
  failures = [],
  unavailableMessage,
  onFailureSelect,
}: FailureRegistryProps) {
  const displayFailures = failures.length > 0 ? failures : []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <h3 className="text-xs font-mono font-bold tracking-widest uppercase">FAILURE_REGISTRY</h3>
        </div>
        {!compact && (
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] font-mono gap-1.5"
            disabled
            title="Retry wiring is not implemented on this surface yet."
          >
            <RefreshCw className="h-3 w-3" />
            READ_ONLY
          </Button>
        )}
      </div>

      <div className="terminal-panel rounded-lg border border-border divide-y divide-border">
        {unavailableMessage ? (
          <div className="p-8 text-center text-[10px] font-mono text-destructive whitespace-pre-wrap break-words">
            [ FAILURE_FEED_UNAVAILABLE ]{'\n'}
            {unavailableMessage}
          </div>
        ) : displayFailures.length === 0 ? (
          <div className="p-8 text-center text-[10px] font-mono text-muted-foreground uppercase">
            [ NO_CRITICAL_FAILURES_DETECTED ]
          </div>
        ) : (
          displayFailures.map((failure) => (
            <button
              key={failure.id}
              type="button"
              onClick={() => onFailureSelect?.(failure)}
              className="flex w-full items-center gap-4 p-3 text-left hover:bg-destructive/5 group transition-colors cursor-pointer"
            >
              <div className={cn(
                "flex h-8 w-8 items-center justify-center rounded border",
                failure.type === 'EXTRACTION_FAIL' ? "border-destructive/50 bg-destructive/10 text-destructive" : 
                failure.type === 'EVALUATION_REJECT' ? "border-amber-500/50 bg-amber-500/10 text-amber-500" :
                "border-muted bg-muted/20 text-muted-foreground"
              )}>
                {failure.type === 'EXTRACTION_FAIL' ? <FileX className="h-4 w-4" /> : <ShieldX className="h-4 w-4" />}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-bold text-destructive">{failure.id}</span>
                  <span className="text-[10px] font-mono font-bold text-foreground">[{failure.entity}]</span>
                  <span className="text-[9px] font-mono text-muted-foreground uppercase">{failure.type}</span>
                </div>
                <p className="text-xs text-muted-foreground truncate font-mono mt-0.5">
                  {failure.message}
                </p>
              </div>

              <div className="text-right group-data-[collapsible=icon]:hidden">
                <div className="text-[10px] font-mono text-muted-foreground">{failure.timestamp}</div>
                <div className="text-[10px] font-mono text-destructive">CFD: {failure.confidence.toFixed(2)}</div>
              </div>

              <ChevronRight className="h-4 w-4 text-muted-foreground/30 group-hover:text-foreground transition-colors" />
            </button>
          ))
        )}
      </div>
    </div>
  )
}
