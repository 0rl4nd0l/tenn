'use client'

import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { AttachedSourceKind } from '@/lib/hooks/use-attached-sources'

const RECENT_SOURCE_KIND_BY_TYPE: Record<string, AttachedSourceKind> = {
  market_commentary: 'concat',
  podcast_transcript: 'ephemeral',
  youtube_transcript: 'ephemeral',
}

interface RecentItem {
  source_id: string
  source_name: string
  source_type: string
  source_kind?: AttachedSourceKind | null
  approved_at: string
}

interface SourcesDrawerProps {
  open: boolean
  apiKey: string
  onClose: () => void
  onReattach: (input: {
    sourceId: string
    sourceKind: AttachedSourceKind
    title: string
  }) => void
}

export function SourcesDrawer({
  open,
  apiKey,
  onClose,
  onReattach,
}: SourcesDrawerProps) {
  const [items, setItems] = useState<RecentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    void fetch('/api/cockpit/commentary/recent?limit=20', {
      headers: { 'X-API-Key': apiKey },
      cache: 'no-store',
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`${response.status}`)
        }
        const body = (await response.json()) as { items: RecentItem[] }
        if (!cancelled) {
          setItems(body.items)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'failed')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [apiKey, open])

  return (
    <Sheet open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Recent sources</SheetTitle>
        </SheetHeader>
        {loading ? <div className="mt-4 text-sm text-muted-foreground">Loading...</div> : null}
        {error ? <div className="mt-4 text-sm text-destructive">Error: {error}</div> : null}
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <li
              key={item.source_id}
              className="flex items-center justify-between gap-2"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{item.source_name}</div>
                <div className="text-xs text-muted-foreground">
                  {item.source_type} • {new Date(item.approved_at).toLocaleDateString()}
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  onReattach({
                    sourceId: item.source_id,
                    sourceKind: sourceKindForRecentItem(item),
                    title: item.source_name,
                  })
                }
                aria-label={`re-attach ${item.source_name}`}
              >
                Attach
              </Button>
            </li>
          ))}
        </ul>
      </SheetContent>
    </Sheet>
  )
}

function sourceKindForRecentItem(item: RecentItem): AttachedSourceKind {
  if (
    item.source_kind === 'ephemeral' ||
    item.source_kind === 'concat' ||
    item.source_kind === 'primary'
  ) {
    return item.source_kind
  }
  return RECENT_SOURCE_KIND_BY_TYPE[item.source_type] ?? 'ephemeral'
}
