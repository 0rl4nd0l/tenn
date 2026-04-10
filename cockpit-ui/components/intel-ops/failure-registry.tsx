'use client'

import React from 'react'
import { AlertTriangle, ChevronRight, FileX, ShieldX, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface FailureRegistryProps {
  compact?: boolean
}

const mockFailures = [
  { id: 'F-001', entity: 'TSLA', type: 'EXTRACTION_FAIL', message: 'Regex mismatch on EBITDA field', confidence: 0.12, timestamp: '12:04:22' },
  { id: 'F-002', entity: 'AAPL', type: 'EVALUATION_REJECT', message: 'Source document year mismatch', confidence: 0.45, timestamp: '11:58:10' },
  { id: 'F-003', entity: 'NVDA', type: 'QUARANTINE', message: 'Unusually high variance in REVENUE', confidence: 0.33, timestamp: '11:45:01' },
  { id: 'F-004', entity: 'GOOGL', type: 'EXTRACTION_FAIL', message: 'PDF page 14 unreadable', confidence: 0.05, timestamp: '11:30:45' },
  { id: 'F-005', entity: 'MSFT', type: 'EVALUATION_REJECT', message: 'Manual override: low trust source', confidence: 0.00, timestamp: '11:15:00' },
]

export function FailureRegistry({ compact }: FailureRegistryProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <h3 className="text-xs font-mono font-bold tracking-widest uppercase">FAILURE_REGISTRY</h3>
        </div>
        {!compact && (
          <Button variant="outline" size="sm" className="h-7 text-[10px] font-mono gap-1.5">
            <RefreshCw className="h-3 w-3" />
            RETRY_ALL_FAILED
          </Button>
        )}
      </div>

      <div className="terminal-panel rounded-lg border border-border divide-y divide-border">
        {mockFailures.map((failure) => (
          <div key={failure.id} className="flex items-center gap-4 p-3 hover:bg-destructive/5 group transition-colors cursor-pointer">
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
          </div>
        ))}
      </div>
    </div>
  )
}
