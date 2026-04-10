'use client'

import React from 'react'
import { Database, ShieldCheck, Zap, Brain, LayoutPanelLeft, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PipelineRibbonProps {
  activeStage: string
  onStageSelect: (stage: string) => void
}

const stages = [
  { id: 'overview', label: 'PULSE_HOME', icon: LayoutPanelLeft, health: 98, color: 'text-primary' },
  { id: 'extraction', label: 'EXTRACTION', icon: Database, health: 94, color: 'text-[oklch(0.69_0.22_145)]' },
  { id: 'evaluation', label: 'EVALUATION', icon: ShieldCheck, health: 88, color: 'text-[oklch(0.7_0.15_195)]' },
  { id: 'signals', label: 'SIGNALS', icon: Zap, health: 76, color: 'text-[oklch(0.78_0.17_80)]' },
  { id: 'memory', label: 'MEMORY', icon: Brain, health: 92, color: 'text-[oklch(0.65_0.15_240)]' },
  { id: 'failures', label: 'FAILURES', icon: AlertCircle, health: 3.4, color: 'text-destructive', isFailure: true },
]

export function PipelineRibbon({ activeStage, onStageSelect }: PipelineRibbonProps) {
  return (
    <div className="flex items-stretch gap-1 overflow-x-auto no-scrollbar py-1">
      {stages.map((stage, idx) => {
        const isActive = activeStage === stage.id
        const Icon = stage.icon
        
        return (
          <React.Fragment key={stage.id}>
            <button
              onClick={() => onStageSelect(stage.id)}
              className={cn(
                "flex-1 min-w-[120px] flex flex-col gap-1 p-2 rounded-md border transition-all duration-200 group relative overflow-hidden",
                isActive 
                  ? "bg-muted/40 border-primary/50 shadow-[0_0_15px_rgba(var(--primary),0.1)]" 
                  : "bg-muted/10 border-border hover:bg-muted/20 hover:border-border/80"
              )}
            >
              <div className="flex items-center justify-between">
                <Icon className={cn("h-3 w-3", isActive ? stage.color : "text-muted-foreground")} />
                <span className={cn(
                  "font-mono text-[9px] px-1 rounded",
                  stage.isFailure 
                    ? "bg-destructive/20 text-destructive" 
                    : "bg-primary/10 text-primary"
                )}>
                  {stage.health}%
                </span>
              </div>
              
              <span className={cn(
                "font-mono text-[10px] font-bold tracking-tighter truncate",
                isActive ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
              )}>
                {stage.label}
              </span>

              {isActive && (
                <div className="absolute bottom-0 left-0 h-[2px] w-full bg-primary" />
              )}
            </button>
            
            {idx < stages.length - 1 && (
              <div className="flex items-center text-muted-foreground/30 px-0.5">
                <div className="h-px w-3 bg-current" />
              </div>
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}
