'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface HoldingItem {
  holding_id: string
  ticker: string
  account_label: string | null
  thesis_bucket: string | null
  status: string | null
  quantity: number | null
  avg_cost: number | null
  cost_currency: string | null
  opened_at: string | null
  updated_at: string | null
  note: string | null
}

interface HoldingsResponse {
  items: HoldingItem[]
}

interface HoldingsScreenProps {
  apiKey: string
}

interface HoldingDraft {
  ticker: string
  quantity: string
  avg_cost: string
  account_label: string
  note: string
}

const EMPTY_DRAFT: HoldingDraft = {
  ticker: '',
  quantity: '',
  avg_cost: '',
  account_label: '',
  note: '',
}

function parseOptionalNumber(raw: string, fieldName: string): number | null {
  const normalized = raw.trim()
  if (!normalized) return null
  const parsed = Number(normalized)
  if (!Number.isFinite(parsed)) {
    throw new Error(`${fieldName} must be numeric`)
  }
  return parsed
}

function toDraft(item: HoldingItem): HoldingDraft {
  return {
    ticker: item.ticker ?? '',
    quantity: item.quantity == null ? '' : String(item.quantity),
    avg_cost: item.avg_cost == null ? '' : String(item.avg_cost),
    account_label: item.account_label ?? '',
    note: item.note ?? '',
  }
}

export function HoldingsScreen({ apiKey }: HoldingsScreenProps) {
  const [items, setItems] = useState<HoldingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createDraft, setCreateDraft] = useState<HoldingDraft>(EMPTY_DRAFT)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<HoldingDraft>(EMPTY_DRAFT)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/cockpit/holdings', {
        headers: { 'X-API-Key': apiKey },
        cache: 'no-store',
      })
      if (!response.ok) {
        setError(`Failed to load holdings (${response.status})`)
        return
      }
      const body = (await response.json()) as HoldingsResponse
      setItems(Array.isArray(body.items) ? body.items : [])
      setError(null)
    } catch (fetchError) {
      setError(
        fetchError instanceof Error ? fetchError.message : 'Failed to load holdings',
      )
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  const canCreate = useMemo(() => createDraft.ticker.trim().length > 0, [createDraft.ticker])

  async function handleCreate() {
    if (!canCreate) {
      setError('Ticker is required')
      return
    }
    try {
      setSaving(true)
      setError(null)
      const payload = {
        ticker: createDraft.ticker.trim().toUpperCase(),
        quantity: parseOptionalNumber(createDraft.quantity, 'Quantity'),
        avg_cost: parseOptionalNumber(createDraft.avg_cost, 'Avg cost'),
        account_label: createDraft.account_label.trim() || null,
        note: createDraft.note.trim() || null,
      }
      const response = await fetch('/api/cockpit/holdings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        setError(`Failed to add holding (${response.status})`)
        return
      }
      setCreateDraft(EMPTY_DRAFT)
      await load()
    } catch (createError) {
      setError(
        createError instanceof Error ? createError.message : 'Failed to add holding',
      )
    } finally {
      setSaving(false)
    }
  }

  function beginEdit(item: HoldingItem) {
    setEditingId(item.holding_id)
    setEditDraft(toDraft(item))
    setError(null)
  }

  async function saveEdit() {
    if (!editingId) return
    const ticker = editDraft.ticker.trim().toUpperCase()
    if (!ticker) {
      setError('Ticker is required')
      return
    }
    try {
      setSaving(true)
      setError(null)
      const payload = {
        ticker,
        quantity: parseOptionalNumber(editDraft.quantity, 'Quantity'),
        avg_cost: parseOptionalNumber(editDraft.avg_cost, 'Avg cost'),
        account_label: editDraft.account_label.trim() || null,
        note: editDraft.note.trim() || null,
      }
      const response = await fetch(`/api/cockpit/holdings/${encodeURIComponent(editingId)}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        setError(`Failed to update holding (${response.status})`)
        return
      }
      setEditingId(null)
      setEditDraft(EMPTY_DRAFT)
      await load()
    } catch (editError) {
      setError(
        editError instanceof Error ? editError.message : 'Failed to update holding',
      )
    } finally {
      setSaving(false)
    }
  }

  async function removeHolding(holdingId: string) {
    try {
      setSaving(true)
      setError(null)
      const response = await fetch(`/api/cockpit/holdings/${encodeURIComponent(holdingId)}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': apiKey },
      })
      if (!response.ok) {
        setError(`Failed to remove holding (${response.status})`)
        return
      }
      if (editingId === holdingId) {
        setEditingId(null)
        setEditDraft(EMPTY_DRAFT)
      }
      await load()
    } catch (removeError) {
      setError(
        removeError instanceof Error ? removeError.message : 'Failed to remove holding',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Portfolio Holdings</h1>
        <Button onClick={() => void load()} disabled={loading || saving}>
          Refresh
        </Button>
      </div>

      <div className="grid gap-2 rounded-lg border border-border/70 bg-card/40 p-3 md:grid-cols-5">
        <Input
          placeholder="Ticker (e.g. BHP)"
          value={createDraft.ticker}
          onChange={(event) =>
            setCreateDraft((current) => ({ ...current, ticker: event.target.value }))
          }
        />
        <Input
          placeholder="Quantity"
          value={createDraft.quantity}
          onChange={(event) =>
            setCreateDraft((current) => ({ ...current, quantity: event.target.value }))
          }
        />
        <Input
          placeholder="Avg cost"
          value={createDraft.avg_cost}
          onChange={(event) =>
            setCreateDraft((current) => ({ ...current, avg_cost: event.target.value }))
          }
        />
        <Input
          placeholder="Account"
          value={createDraft.account_label}
          onChange={(event) =>
            setCreateDraft((current) => ({ ...current, account_label: event.target.value }))
          }
        />
        <div className="flex gap-2">
          <Input
            placeholder="Note"
            value={createDraft.note}
            onChange={(event) =>
              setCreateDraft((current) => ({ ...current, note: event.target.value }))
            }
          />
          <Button onClick={() => void handleCreate()} disabled={!canCreate || saving}>
            Add
          </Button>
        </div>
      </div>

      {error ? (
        <p className="rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <div className="overflow-x-auto rounded-lg border border-border/70">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">Ticker</th>
              <th className="px-3 py-2">Quantity</th>
              <th className="px-3 py-2">Avg Cost</th>
              <th className="px-3 py-2">Account</th>
              <th className="px-3 py-2">Note</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                  {loading ? 'Loading holdings...' : 'No holdings yet.'}
                </td>
              </tr>
            ) : (
              items.map((item) => {
                const editing = editingId === item.holding_id
                return (
                  <tr key={item.holding_id} className="border-t border-border/60">
                    <td className="px-3 py-2 align-top">
                      {editing ? (
                        <Input
                          value={editDraft.ticker}
                          onChange={(event) =>
                            setEditDraft((current) => ({ ...current, ticker: event.target.value }))
                          }
                        />
                      ) : (
                        item.ticker
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      {editing ? (
                        <Input
                          value={editDraft.quantity}
                          onChange={(event) =>
                            setEditDraft((current) => ({ ...current, quantity: event.target.value }))
                          }
                        />
                      ) : (
                        item.quantity ?? '-'
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      {editing ? (
                        <Input
                          value={editDraft.avg_cost}
                          onChange={(event) =>
                            setEditDraft((current) => ({ ...current, avg_cost: event.target.value }))
                          }
                        />
                      ) : (
                        item.avg_cost ?? '-'
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      {editing ? (
                        <Input
                          value={editDraft.account_label}
                          onChange={(event) =>
                            setEditDraft((current) => ({ ...current, account_label: event.target.value }))
                          }
                        />
                      ) : (
                        item.account_label ?? '-'
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      {editing ? (
                        <Input
                          value={editDraft.note}
                          onChange={(event) =>
                            setEditDraft((current) => ({ ...current, note: event.target.value }))
                          }
                        />
                      ) : (
                        item.note ?? '-'
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <div className="flex flex-wrap gap-2">
                        {editing ? (
                          <>
                            <Button size="sm" onClick={() => void saveEdit()} disabled={saving}>
                              Save
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setEditingId(null)
                                setEditDraft(EMPTY_DRAFT)
                              }}
                              disabled={saving}
                            >
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => beginEdit(item)} disabled={saving}>
                            Edit
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => void removeHolding(item.holding_id)}
                          disabled={saving}
                        >
                          Remove
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

