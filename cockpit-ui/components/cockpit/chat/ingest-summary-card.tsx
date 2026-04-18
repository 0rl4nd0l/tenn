'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { AttachedSourceKind } from '@/lib/hooks/use-attached-sources'

export interface IngestSummary {
  sourceId: string
  title: string
  chunkCount: number
  detectedTickers: string[]
  status: 'pending' | 'approved'
  sourceKind: AttachedSourceKind
}

interface IngestSummaryCardProps {
  summary: IngestSummary
  isAttached: boolean
  onAttach: (sourceId: string) => void
  onDetach: (sourceId: string) => void
  onAddTicker: (ticker: string) => void
}

export function IngestSummaryCard({
  summary,
  isAttached,
  onAttach,
  onDetach,
  onAddTicker,
}: IngestSummaryCardProps) {
  return (
    <div className="space-y-3 rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="truncate font-medium">{summary.title}</div>
          <div className="text-xs text-muted-foreground">
            {summary.chunkCount} chunks • status: {summary.status}
          </div>
        </div>
        {isAttached ? (
          <Button size="sm" variant="outline" onClick={() => onDetach(summary.sourceId)}>
            Detach
          </Button>
        ) : (
          <Button size="sm" onClick={() => onAttach(summary.sourceId)}>
            Attach
          </Button>
        )}
      </div>

      {summary.detectedTickers.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Detected tickers:</span>
          {summary.detectedTickers.map((ticker) => (
            <span key={ticker} className="flex items-center gap-1">
              <Badge variant="secondary">{ticker}</Badge>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onAddTicker(ticker)}
                aria-label={`Add to watchlist ${ticker}`}
              >
                + add to watchlist
              </Button>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}
