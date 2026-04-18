'use client'

import { Activity, Clock, History } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { ExtractionReviewRunSummary } from '@/lib/cockpit-types'

type VerificationSidebarProps = {
  recentRuns: ExtractionReviewRunSummary[]
  loading: boolean
  onSelectTicker: (ticker: string) => void
  onSelectRun: (runId: string) => void
  activeTicker: string
}

export function VerificationSidebar({
  recentRuns,
  loading,
  onSelectTicker,
  onSelectRun,
  activeTicker,
}: VerificationSidebarProps) {
  // Group by ticker for discovery
  const tickerGroups = recentRuns.reduce((acc, run) => {
    const ticker = run.ticker || 'UNKNOWN'
    if (!acc[ticker]) acc[ticker] = []
    acc[ticker].push(run)
    return acc
  }, {} as Record<string, ExtractionReviewRunSummary[]>)

  const sortedTickers = Object.keys(tickerGroups).sort()

  return (
    <Card className="flex h-full flex-col border-border/40 bg-muted/10">
      <CardHeader className="p-4 pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-muted-foreground">
          <History className="h-4 w-4" />
          Discovery & History
        </CardTitle>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="flex flex-col gap-4 p-4">
            <section>
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground/80">
                <Clock className="h-3 w-3" />
                Recent Companies
              </h3>
              {loading && sortedTickers.length === 0 ? (
                <div className="flex animate-pulse flex-col gap-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-8 rounded bg-muted/40" />
                  ))}
                </div>
              ) : sortedTickers.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
                  No recent history found.
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {sortedTickers.map((ticker) => (
                    <Button
                      key={ticker}
                      variant={activeTicker === ticker ? 'default' : 'outline'}
                      size="sm"
                      className="h-7 px-2 text-xs font-mono"
                      onClick={() => onSelectTicker(ticker)}
                    >
                      {ticker}
                    </Button>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground/80">
                <Activity className="h-3 w-3" />
                Recent Runs
              </h3>
              <div className="flex flex-col gap-1">
                {recentRuns.slice(0, 10).map((run) => (
                  <button
                    key={run.run_id}
                    className={`flex flex-col rounded-md border p-2 text-left transition-colors hover:bg-muted/50 ${
                      activeTicker === run.ticker ? 'border-primary/30 bg-primary/5' : 'border-border/40'
                    }`}
                    onClick={() => {
                      if (run.ticker) onSelectTicker(run.ticker)
                      onSelectRun(run.run_id)
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold">{run.ticker}</span>
                      <Badge variant={run.status === 'succeeded' ? 'outline' : 'critical'} className="h-4 px-1 text-[9px]">
                        {run.status}
                      </Badge>
                    </div>
                    <span className="mt-1 truncate text-[10px] text-muted-foreground">
                      {run.run_id.slice(0, 12)}...
                    </span>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
