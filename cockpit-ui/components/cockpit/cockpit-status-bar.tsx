'use client'

import { Badge } from '@/components/ui/badge'
import { useCockpitStore, AVAILABLE_CHAT_MODELS } from '@/lib/cockpit-store'
import { useQuery } from '@tanstack/react-query'
import { checkHealth } from '@/lib/api-client'

export function CockpitStatusBar() {
  const { sessionStats, chatModel } = useCockpitStore()
  const modelLabel = AVAILABLE_CHAT_MODELS.find((m) => m.id === chatModel)?.label ?? chatModel
  
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 30000,
  })

  const backendHealthy = health?.status === 'ok'

  return (
    <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-card px-4 text-xs">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Model:</span>
          <span className="font-mono text-foreground">{modelLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Latency:</span>
          <span className="font-mono text-foreground">{sessionStats.lastLatencyMs}ms</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${
            backendHealthy
              ? 'bg-[oklch(0.65_0.2_145)]'
              : 'bg-[oklch(0.55_0.2_25)]'
          }`} />
          <span className="text-muted-foreground">
            {backendHealthy ? 'Backend healthy' : 'Backend down'}
          </span>
        </div>
        <Badge variant="outline" className="h-5 text-[10px] font-mono">
          Session: ${sessionStats.totalCostUsd.toFixed(4)}
        </Badge>
      </div>
    </footer>
  )
}
