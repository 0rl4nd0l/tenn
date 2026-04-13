'use client'

import { BarChart3, CheckCircle2, Play, Search } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { TabsList, TabsTrigger } from '@/components/ui/tabs'

import type { VerificationTab } from './types'

type VerificationTabBarProps = {
  wrongQueueCount: number
  pendingCount: number
  activeTab: VerificationTab
}

export function VerificationTabBar({ wrongQueueCount, pendingCount }: VerificationTabBarProps) {
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
      <TabsTrigger value="verify" className="justify-start gap-2 px-3 py-2">
        <CheckCircle2 className="h-4 w-4" />
        Verify
        {wrongQueueCount > 0 ? <Badge variant="outline">{wrongQueueCount}</Badge> : null}
      </TabsTrigger>
    </TabsList>
  )
}
