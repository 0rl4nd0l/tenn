'use client'

import React from 'react'
import { Search, X, Monitor, Building2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ScopeTerminalProps {
  scope: 'global' | 'company'
  selectedCompany: string | null
  onCompanySelect: (company: string | null) => void
  streamStatus?: 'live' | 'loading' | 'error'
}

export function ScopeTerminal({
  scope,
  selectedCompany,
  onCompanySelect,
  streamStatus = 'live',
}: ScopeTerminalProps) {
  const modeLabel = scope === 'company' ? 'COMPANY_SCOPE' : 'GLOBAL_SYSTEM'
  const streamLabel =
    streamStatus === 'error'
      ? 'SYSTEM_PULSE: DEGRADED'
      : streamStatus === 'loading'
        ? 'SYSTEM_PULSE: SYNCING'
        : 'SYSTEM_PULSE: LIVE'
  const streamDotClass =
    streamStatus === 'error'
      ? 'bg-destructive'
      : streamStatus === 'loading'
        ? 'bg-[oklch(0.78_0.17_80)]'
        : 'bg-[oklch(0.69_0.22_145)]'

  return (
    <div className="flex items-center gap-4">
      <div className={cn(
        "flex flex-1 items-center gap-3 px-3 py-2 border rounded-md transition-all duration-300",
        scope === 'global' ? "border-primary/50 bg-primary/5" : "border-border bg-muted/20"
      )}>
        <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider">
          <Monitor className={cn("h-4 w-4", scope === 'global' ? "text-primary" : "text-muted-foreground")} />
          <span className={scope === 'global' ? "text-primary" : "text-muted-foreground"}>MODE:</span>
          <span className={cn(
            "px-1.5 py-0.5 rounded",
            scope === 'global' ? "bg-primary text-primary-foreground font-bold" : "bg-[oklch(0.7_0.15_195)] text-background font-bold"
          )}>{modeLabel}</span>
        </div>
        
        <div className="h-4 w-px bg-border mx-2" />
        
        <div className="flex-1 flex items-center gap-2 group">
          <Search className="h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
          <Input 
            placeholder="SEARCH_COMPANY_ENTITY..." 
            aria-label="Search company entity scope"
            className="h-8 border-none bg-transparent font-mono text-sm focus-visible:ring-0 p-0 placeholder:text-muted-foreground/50"
            value={selectedCompany || ''}
            onChange={(e) => onCompanySelect(e.target.value)}
            autoCapitalize="characters"
            spellCheck={false}
          />
          {selectedCompany && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-6 w-6 hover:bg-destructive/10 hover:text-destructive"
              onClick={() => onCompanySelect(null)}
              aria-label="Clear company entity scope"
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        {scope === 'company' && (
          <>
            <div className="h-4 w-px bg-border mx-2" />
            <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider animate-in fade-in slide-in-from-left-2">
              <Building2 className="h-4 w-4 text-[oklch(0.7_0.15_195)]" />
              <span className="text-muted-foreground">TARGET:</span>
              <span className="bg-[oklch(0.7_0.15_195)] text-background px-1.5 py-0.5 rounded font-bold">
                {selectedCompany?.toUpperCase()}
              </span>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground bg-black/20 px-3 py-2 rounded-md border border-border/50 group-data-[collapsible=icon]:hidden">
        <span className={cn("h-2 w-2 rounded-full", streamDotClass, streamStatus === 'live' && "status-dot-running")} />
        {streamLabel}
      </div>
    </div>
  )
}
