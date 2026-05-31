'use client'

import { useCallback, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'

import { AddTickerDialog } from './add-ticker-dialog'

interface WatchlistItem {
  ticker: string
  added_at: string
  source_id: string | null
  note: string | null
  stance: string | null
}

interface HoldingItem {
  ticker: string
  account_label?: string | null
  status?: string | null
}

interface WatchlistCandidate {
  ticker: string
  reason: string
}

interface WatchlistScreenProps {
  apiKey: string
}

export function WatchlistScreen({ apiKey }: WatchlistScreenProps) {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [candidates, setCandidates] = useState<WatchlistCandidate[]>([])
  const [candidateState, setCandidateState] = useState<'idle' | 'loading' | 'ready' | 'data_missing'>('idle')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogError, setDialogError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setActionError(null)
    try {
      const response = await fetch('/api/cockpit/watchlist', {
        headers: { 'X-API-Key': apiKey },
        cache: 'no-store',
      })
      if (!response.ok) {
        setItems([])
        setCandidates([])
        setCandidateState('data_missing')
        return
      }

      const body = (await response.json()) as { items: WatchlistItem[] }
      setItems(body.items)
      if (body.items.length > 0) {
        setCandidates([])
        setCandidateState('idle')
        return
      }
      setCandidateState('loading')
      const holdingsResponse = await fetch('/api/cockpit/holdings', {
        headers: { 'X-API-Key': apiKey },
        cache: 'no-store',
      })
      if (!holdingsResponse.ok) {
        setCandidates([])
        setCandidateState('data_missing')
        return
      }
      const holdingsBody = (await holdingsResponse.json()) as { items?: HoldingItem[] }
      const seen = new Set<string>()
      const nextCandidates = (holdingsBody.items ?? [])
        .filter((holding) => holding.status !== 'archived')
        .map((holding) => {
          const ticker = holding.ticker.trim().toUpperCase()
          return {
            ticker,
            reason: holding.account_label
              ? `Current holding in ${holding.account_label}`
              : 'Current holding',
          }
        })
        .filter((candidate) => {
          if (!candidate.ticker || seen.has(candidate.ticker)) {
            return false
          }
          seen.add(candidate.ticker)
          return true
        })
        .slice(0, 3)

      setCandidates(nextCandidates)
      setCandidateState(nextCandidates.length > 0 ? 'ready' : 'data_missing')
    } catch {
      setItems([])
      setCandidates([])
      setCandidateState('data_missing')
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  async function handleSubmit(input: { ticker: string; note: string; stance: string }) {
    setDialogError(null)
    const response = await fetch('/api/cockpit/watchlist', {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    })
    if (response.status === 409) {
      setDialogError(`${input.ticker} is already in watchlist`)
      return
    }
    if (!response.ok) {
      setDialogError(`failed: ${response.status}`)
      return
    }
    setDialogOpen(false)
    await load()
  }

  async function handleAddSuggestion(candidate: WatchlistCandidate) {
    setDialogError(null)
    setActionError(null)
    const response = await fetch('/api/cockpit/watchlist', {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ticker: candidate.ticker,
        note: candidate.reason,
        stance: 'watch',
      }),
    })
    if (response.status === 409) {
      setActionError(`${candidate.ticker} is already in watchlist`)
      return
    }
    if (!response.ok) {
      setActionError(`failed to add ${candidate.ticker}: ${response.status}`)
      return
    }
    await load()
  }

  async function handleRemove(ticker: string) {
    await fetch(`/api/cockpit/watchlist/${encodeURIComponent(ticker)}`, {
      method: 'DELETE',
      headers: { 'X-API-Key': apiKey },
    })
    await load()
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Watchlist</h1>
        <Button onClick={() => setDialogOpen(true)}>Add ticker</Button>
      </div>
      <ul className="divide-y divide-border">
        {items.length === 0 ? (
          <li className="rounded-md border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
            <div className="space-y-4">
              <div>
                <p className="font-medium text-foreground">Track companies Tenn should monitor.</p>
                <p className="mt-1">
                  Add a ticker manually or start from a source-grounded portfolio holding.
                </p>
              </div>
              {candidateState === 'ready' ? (
                <div className="space-y-2" aria-label="Suggested watchlist tickers">
                  {candidates.map((candidate) => (
                    <div
                      key={candidate.ticker}
                      className="flex flex-col gap-2 rounded-md border border-border bg-background px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div>
                        <div className="font-medium text-foreground">{candidate.ticker}</div>
                        <div className="text-xs text-muted-foreground">
                          Source: {candidate.reason}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => void handleAddSuggestion(candidate)}
                      >
                        Add {candidate.ticker}
                      </Button>
                    </div>
                  ))}
                </div>
              ) : null}
              {candidateState === 'loading' ? (
                <p>Loading current holdings for watchlist suggestions...</p>
              ) : null}
              {candidateState === 'data_missing' ? (
                <p>
                  DATA_MISSING: no current holdings or watchlist suggestion source is available.
                </p>
              ) : null}
              {actionError ? (
                <p className="text-destructive">{actionError}</p>
              ) : null}
            </div>
          </li>
        ) : items.map((item) => (
          <li
            key={item.ticker}
            className="flex items-center justify-between gap-3 py-2"
          >
            <div className="min-w-0">
              <div className="font-medium">{item.ticker}</div>
              {item.note ? (
                <div className="text-xs text-muted-foreground">{item.note}</div>
              ) : null}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void handleRemove(item.ticker)}
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <AddTickerDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false)
          setDialogError(null)
        }}
        onSubmit={handleSubmit}
        error={dialogError}
      />
    </div>
  )
}
