'use client'

import { Button } from '@/components/ui/button'

export interface TakeawayCitation {
  chunkId: string
  segmentStartSeconds: number
}

export interface Takeaway {
  text: string
  citations: TakeawayCitation[]
}

export interface WatchlistSuggestion {
  ticker: string
  commentary: string
  citations: TakeawayCitation[]
}

export interface TakeawaysPayload {
  sourceId: string
  videoId: string
  takeaways: Takeaway[]
  watchlistSuggestions: WatchlistSuggestion[]
  model: string
  promptVersion: string
}

interface TakeawaysPanelProps {
  payload: TakeawaysPayload
  onAddTicker: (input: { ticker: string; commentary: string; sourceId: string }) => void
  onJumpToCitation: (citation: TakeawayCitation) => void
}

function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(total / 60)
  const remainder = total % 60
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

export function TakeawaysPanel({
  payload,
  onAddTicker,
  onJumpToCitation,
}: TakeawaysPanelProps) {
  return (
    <div className="space-y-4 rounded-lg border border-border bg-card p-4">
      <section>
        <h3 className="mb-2 text-sm font-medium">Takeaways</h3>
        <ul className="space-y-2">
          {payload.takeaways.map((takeaway, index) => (
            <li key={`${takeaway.text}-${index}`} className="text-sm">
              <span>{takeaway.text}</span>
              {takeaway.citations.map((citation) => (
                <Button
                  key={`${citation.chunkId}-${citation.segmentStartSeconds}`}
                  size="sm"
                  variant="ghost"
                  className="ml-1 h-6 px-2 text-xs"
                  onClick={() => onJumpToCitation(citation)}
                  aria-label={formatTimestamp(citation.segmentStartSeconds)}
                >
                  ▶ {formatTimestamp(citation.segmentStartSeconds)}
                </Button>
              ))}
            </li>
          ))}
        </ul>
      </section>

      {payload.watchlistSuggestions.length > 0 ? (
        <section>
          <h3 className="mb-2 text-sm font-medium">Watchlist suggestions</h3>
          <ul className="space-y-2">
            {payload.watchlistSuggestions.map((suggestion) => (
              <li
                key={suggestion.ticker}
                className="flex items-start justify-between gap-3 text-sm"
              >
                <div className="min-w-0">
                  <div className="font-medium">{suggestion.ticker}</div>
                  <div className="text-muted-foreground">{suggestion.commentary}</div>
                </div>
                <Button
                  size="sm"
                  aria-label={`add ${suggestion.ticker} to watchlist`}
                  onClick={() =>
                    onAddTicker({
                      ticker: suggestion.ticker,
                      commentary: suggestion.commentary,
                      sourceId: payload.sourceId,
                    })
                  }
                >
                  Add
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="text-[11px] text-muted-foreground">
        model: {payload.model} • prompt: {payload.promptVersion}
      </div>
    </div>
  )
}
