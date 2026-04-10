'use client'

import React from 'react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface DiagnosticMatrixProps {
  stage: string
  _scope: 'global' | 'company'
  company: string | null
}

const mockMetrics = [
  'REVENUE', 'EBITDA', 'NET_DEBT', 'EPS_GROWTH', 'MARGIN_PCT', 'OPERATING_CASH_FLOW', 'CAPEX', 'DIVIDEND_YIELD'
]

const mockCompanies = [
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK.B', 'V', 'JPM'
]

export function DiagnosticMatrix({ stage, _scope, company }: DiagnosticMatrixProps) {
  const displayCompanies = company ? [company.toUpperCase()] : mockCompanies

  return (
    <div className="terminal-panel rounded-lg border border-border overflow-hidden">
      <div className="bg-muted/30 border-b border-border p-3 flex justify-between items-center">
        <h3 className="text-xs font-mono font-bold tracking-widest text-muted-foreground uppercase">
          {stage.toUpperCase()}_DENSITY_MATRIX
        </h3>
        <div className="flex gap-4">
          <LegendItem color="bg-primary" label="POPULATED" />
          <LegendItem color="bg-[oklch(0.78_0.17_80)]" label="ABSTAINED" />
          <LegendItem color="bg-destructive" label="FAILED" />
          <LegendItem color="bg-muted" label="SPARSE" />
        </div>
      </div>

      <div className="overflow-x-auto p-4">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left text-[10px] font-mono text-muted-foreground border border-border/50 sticky left-0 bg-background z-10">ENTITY</th>
              {mockMetrics.map(metric => (
                <th key={metric} className="p-2 text-center text-[10px] font-mono text-muted-foreground border border-border/50 whitespace-nowrap">
                  {metric}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayCompanies.map(comp => (
              <tr key={comp} className="hover:bg-muted/10 transition-colors">
                <td className="p-2 text-[10px] font-mono font-bold text-primary border border-border/50 sticky left-0 bg-background z-10">
                  {comp}
                </td>
                {mockMetrics.map(metric => {
                  // Mock some states
                  const rand = Math.random()
                  let state: 'populated' | 'abstain' | 'failed' | 'sparse' = 'populated'
                  if (rand > 0.85) state = 'failed'
                  else if (rand > 0.7) state = 'abstain'
                  else if (rand > 0.6) state = 'sparse'

                  return (
                    <td key={metric} className="p-1 border border-border/50">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className={cn(
                              "h-6 w-full rounded-sm transition-all hover:scale-105 cursor-crosshair",
                              state === 'populated' && "bg-primary/40 border border-primary/60",
                              state === 'abstain' && "bg-[oklch(0.78_0.17_80/0.4)] border border-[oklch(0.78_0.17_80/0.6)]",
                              state === 'failed' && "bg-destructive/40 border border-destructive/60",
                              state === 'sparse' && "bg-muted/40 border border-border"
                            )} />
                          </TooltipTrigger>
                          <TooltipContent className="font-mono text-xs p-2 bg-background border-border">
                            <div className="text-primary font-bold mb-1">{comp}::{metric}</div>
                            <div className="flex flex-col gap-1 text-muted-foreground">
                              <span>STATUS: {state.toUpperCase()}</span>
                              <span>CONFIDENCE: {(Math.random() * 0.4 + 0.6).toFixed(2)}</span>
                              <span>SOURCE: 10-K_FY2025</span>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string, label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={cn("h-2 w-2 rounded-full", color)} />
      <span className="text-[9px] font-mono text-muted-foreground">{label}</span>
    </div>
  )
}
