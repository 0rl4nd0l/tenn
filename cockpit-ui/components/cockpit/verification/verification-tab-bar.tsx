'use client'

import { BarChart3, CheckCircle2, ClipboardCheck, Play, Search } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { TabsList, TabsTrigger } from '@/components/ui/tabs'

type VerificationTabBarProps = {
  wrongQueueCount: number
  pendingCount: number
  failedChecksCount: number
}

export function VerificationTabBar({ wrongQueueCount, pendingCount, failedChecksCount }: VerificationTabBarProps) {
  return (
    <TabsList className="h-auto w-full justify-start gap-2 rounded-xl border border-border/60 bg-muted/30 p-2">
      <TabsTrigger value="review" className="justify-start gap-2 px-3 py-2">
        <Search className="h-4 w-4" />
        Review
        {pendingCount > 0 ? <Badge variant="outline">{pendingCount}</Badge> : null}
      </TabsTrigger>
      <TabsTrigger value="runs" className="justify-start gap-2 px-3 py-2">
        <BarChart3 className="h-4 w-4" />
        Runs
      </TabsTrigger>
      <TabsTrigger value="gold-eval" className="justify-start gap-2 px-3 py-2">
        <Play className="h-4 w-4" />
        Real-Gold
      </TabsTrigger>
      <TabsTrigger value="metric-coverage" className="justify-start gap-2 px-3 py-2">
        <ClipboardCheck className="h-4 w-4" />
        Metric Coverage
      </TabsTrigger>
      <TabsTrigger value="verify" className="justify-start gap-2 px-3 py-2">
        <CheckCircle2 className="h-4 w-4" />
        Verify
        {failedChecksCount > 0 ? (
          <Badge variant="critical" className="ml-auto">
            {failedChecksCount}
          </Badge>
        ) : wrongQueueCount > 0 ? (
          <Badge variant="outline">{wrongQueueCount}</Badge>
        ) : null}
      </TabsTrigger>
    </TabsList>
  )
}
