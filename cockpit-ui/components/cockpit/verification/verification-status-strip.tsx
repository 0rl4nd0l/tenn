import { Activity } from 'lucide-react'

import { Badge } from '@/components/ui/badge'

type VerificationStatusStripProps = {
  wrongQueueCount: number
  pendingCount: number
  activeRunId: string
  attachActiveRuns: boolean
}

export function VerificationStatusStrip({
  wrongQueueCount,
  pendingCount,
  activeRunId,
  attachActiveRuns,
}: VerificationStatusStripProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
      <Badge variant="outline">wrong queue {wrongQueueCount}</Badge>
      <Badge variant="outline">pending review {pendingCount}</Badge>
      {activeRunId ? <Badge variant="outline">active run {activeRunId.slice(0, 12)}</Badge> : null}
      {attachActiveRuns ? (
        <span className="flex items-center gap-2">
          <Activity className="h-3.5 w-3.5 text-primary" />
          attached to backend active-run monitor
        </span>
      ) : null}
    </div>
  )
}
