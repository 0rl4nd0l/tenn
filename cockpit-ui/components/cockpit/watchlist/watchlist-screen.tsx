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

interface WatchlistScreenProps {
  apiKey: string
}

export function WatchlistScreen({ apiKey }: WatchlistScreenProps) {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogError, setDialogError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const response = await fetch('/api/cockpit/watchlist', {
      headers: { 'X-API-Key': apiKey },
      cache: 'no-store',
    })
    if (response.ok) {
      const body = (await response.json()) as { items: WatchlistItem[] }
      setItems(body.items)
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
        {items.map((item) => (
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
