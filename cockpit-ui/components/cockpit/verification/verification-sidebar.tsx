'use client'

import { Activity, Clock, History, ChevronDown, ChevronRight, LayoutGrid } from 'lucide-react'
import { useState, useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { ExtractionReviewRunSummary, ExtractionReviewSessionSummary } from '@/lib/cockpit-types'

type VerificationSidebarProps = {
  recentRuns: ExtractionReviewRunSummary[]
  recentReviewSessions: ExtractionReviewSessionSummary[]
  loading: boolean
  onSelectTicker: (ticker: string) => void
  onSelectRun: (runId: string) => void
  onSelectSession: (sessionId: string) => void
  onSelectRunGroup?: (runIds: string[]) => void
  activeTicker: string
}

type RunGroup = {
  id: string
  label: string
  timestamp: Date
  runs: ExtractionReviewRunSummary[]
}

export function VerificationSidebar({
  recentRuns,
  recentReviewSessions,
  loading,
  onSelectTicker,
  onSelectRun,
  onSelectSession,
  onSelectRunGroup,
  activeTicker,
}: VerificationSidebarProps) {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({})

  // Group by ticker for discovery
  const tickerGroups = recentRuns.reduce((acc, run) => {
    const ticker = run.ticker || 'UNKNOWN'
    if (!acc[ticker]) acc[ticker] = []
    acc[ticker].push(run)
    return acc
  }, {} as Record<string, ExtractionReviewRunSummary[]>)

  const sortedTickers = Object.keys(tickerGroups).sort()

  // Group by operation (heuristic: same model/version and within 60 seconds)
  const operationGroups = useMemo(() => {
    const groups: RunGroup[] = []
    const sortedRuns = [...recentRuns].sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )

    for (const run of sortedRuns) {
      const runTime = new Date(run.created_at)
      const matchedGroup = groups.find(g => {
        const timeDiff = Math.abs(g.timestamp.getTime() - runTime.getTime())
        // Heuristic: runs within 60s of each other
        return timeDiff < 60000 
      })

      if (matchedGroup) {
        matchedGroup.runs.push(run)
      } else {
        const isGoldEval = run.title?.toLowerCase().includes('gold') || false
        groups.push({
          id: `group-${run.run_id}`,
          label: isGoldEval ? 'Gold Evaluation' : run.ticker || 'System Run',
          timestamp: runTime,
          runs: [run]
        })
      }
    }
    return groups
  }, [recentRuns])

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => ({ ...prev, [groupId]: !prev[groupId] }))
  }

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
                <History className="h-3 w-3" />
                Saved Reviews
              </h3>
              {recentReviewSessions.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/60 p-3 text-center text-xs text-muted-foreground">
                  No saved reviews yet.
                </div>
              ) : (
                <div className="flex flex-col gap-1">
                  {recentReviewSessions.slice(0, 8).map((session) => (
                    <button
                      key={session.session_id}
                      className="flex flex-col rounded-md border border-border/40 p-2 text-left transition-colors hover:bg-muted/30"
                      onClick={() => onSelectSession(session.session_id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-mono text-[10px] font-bold">
                          {session.tickers.join(', ') || 'BROAD'}
                        </span>
                        <Badge variant="outline" className="h-4 px-1 text-[8px]">
                          {session.item_count ?? session.summary?.total ?? 0} items
                        </Badge>
                      </div>
                      <span className="mt-1 truncate text-[10px] text-muted-foreground">
                        {session.titles[0] || session.session_id}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground/80">
                <Activity className="h-3 w-3" />
                Recent Operations
              </h3>
              <div className="flex flex-col gap-2">
                {operationGroups.slice(0, 15).map((group) => (
                  <div key={group.id} className="flex flex-col gap-1">
                    <div
                      className={`flex w-full flex-col rounded-md border p-1 transition-colors hover:bg-muted/50 ${
                        group.runs.some(r => r.ticker === activeTicker) 
                          ? 'border-primary/30 bg-primary/5' 
                          : 'border-border/40'
                      }`}
                    >
                      <div className="flex items-center justify-between p-1">
                        <button 
                          className="flex flex-1 items-center gap-2 text-left"
                          onClick={() => toggleGroup(group.id)}
                        >
                          {expandedGroups[group.id] ? (
                            <ChevronDown className="h-3 w-3 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="font-mono text-xs font-bold truncate max-w-[100px]">
                            {group.label}
                          </span>
                          {group.runs.length > 1 && (
                            <Badge variant="secondary" className="h-4 px-1 text-[9px]">
                              {group.runs.length}
                            </Badge>
                          )}
                        </button>
                        <div className="flex items-center gap-1">
                          {group.runs.length > 1 && onSelectRunGroup && (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-5 w-5" 
                              title="Review all in group"
                              onClick={(e) => {
                                e.stopPropagation()
                                onSelectRunGroup(group.runs.map(r => r.run_id))
                              }}
                            >
                              <LayoutGrid className="h-3 w-3" />
                            </Button>
                          )}
                          <span className="text-[8px] text-muted-foreground whitespace-nowrap">
                            {group.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>

                    {expandedGroups[group.id] && (
                      <div className="ml-4 flex flex-col gap-1 border-l border-border/60 pl-2">
                        {group.runs.map((run) => (
                          <button
                            key={run.run_id}
                            className={`flex flex-col rounded-md p-1.5 text-left transition-colors hover:bg-muted/30 ${
                              activeTicker === run.ticker ? 'bg-primary/5' : ''
                            }`}
                            onClick={() => {
                              if (run.ticker) onSelectTicker(run.ticker)
                              onSelectRun(run.run_id)
                            }}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="truncate text-[10px] font-medium">
                                {run.title || run.run_id.slice(0, 8)}
                              </span>
                              <Badge 
                                variant={run.review_ready ? 'outline' : 'secondary'}
                                className="h-3 px-1 text-[8px]"
                              >
                                {run.review_ready ? 'review' : run.status}
                              </Badge>
                            </div>
                            <div className="mt-1 flex gap-1 text-[9px] text-muted-foreground">
                              <span>{run.metrics_count ?? 0} metrics</span>
                              <span>{run.has_timeline ? 'timeline' : 'no timeline'}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
