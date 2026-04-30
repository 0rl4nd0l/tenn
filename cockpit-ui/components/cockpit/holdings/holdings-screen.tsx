'use client'

import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts'

interface HoldingItem {
  holding_id: string
  ticker: string
  account_label: string | null
  market_exchange: string | null
  thesis_bucket: string | null
  status: string | null
  quantity: number | null
  avg_cost: number | null
  cost_currency: string | null
  opened_at: string | null
  updated_at: string | null
  note: string | null
  current_price: number | null
  price_currency: string | null
  price_as_of: string | null
  market_value: number | null
  unrealized_pnl: number | null
  valuation_warning: string | null
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
  market_exchange: string
  thesis_bucket: string
  status: string
  cost_currency: string
  opened_at: string
  note: string
}

type StatusFilter = 'all' | 'active' | 'archived' | 'unset'
type SortKey = 'ticker-asc' | 'ticker-desc' | 'quantity-desc' | 'avg-cost-desc' | 'updated-desc'
type ValueMode = 'amount' | 'percent'
type ChartMode = 'line' | 'bar'
type ChartRange = 'd' | 'm' | 'y'
type ExposureBasis = 'live' | 'cost'

interface HoldingsChartPoint {
  label: string
  amount: number
  percent: number
}

const EMPTY_DRAFT: HoldingDraft = {
  ticker: '',
  quantity: '',
  avg_cost: '',
  account_label: '',
  market_exchange: '',
  thesis_bucket: '',
  status: '',
  cost_currency: '',
  opened_at: '',
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

function parseOptionalText(raw: string): string | null {
  const normalized = raw.trim()
  return normalized ? normalized : null
}

function toDraft(item: HoldingItem): HoldingDraft {
  return {
    ticker: item.ticker ?? '',
    quantity: item.quantity == null ? '' : String(item.quantity),
    avg_cost: item.avg_cost == null ? '' : String(item.avg_cost),
    account_label: item.account_label ?? '',
    market_exchange: item.market_exchange ?? '',
    thesis_bucket: item.thesis_bucket ?? '',
    status: item.status ?? '',
    cost_currency: item.cost_currency ?? '',
    opened_at: item.opened_at ?? '',
    note: item.note ?? '',
  }
}

function formatNumber(value: number | null): string {
  if (value == null) return '-'
  return new Intl.NumberFormat('en-AU', {
    maximumFractionDigits: 2,
  }).format(value)
}

function formatCurrencyAmount(value: number | null, currency?: string | null): string {
  if (value == null || !Number.isFinite(value)) return '-'
  const code = String(currency || 'AUD').trim().toUpperCase() || 'AUD'
  try {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: code,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${code} ${formatNumber(value)}`
  }
}

function formatTimestamp(value: string | null): string {
  if (!value) return '-'
  return value.slice(0, 19).replace('T', ' ')
}

function normalizeStatus(value: string | null): string {
  return String(value ?? '').trim().toLowerCase()
}

function formatChartNumber(value: number, valueMode: ValueMode): string {
  if (!Number.isFinite(value)) return '-'
  if (valueMode === 'percent') {
    return `${value.toFixed(2)}%`
  }
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0,
  }).format(value)
}

function parseHoldingDate(item: HoldingItem): Date | null {
  const raw = item.opened_at || item.updated_at
  if (!raw) return null
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed
}

function getInvestedAmount(item: HoldingItem): number {
  if (item.quantity == null || item.avg_cost == null) return 0
  return Math.max(0, item.quantity * item.avg_cost)
}

function getLiveMarketValue(item: HoldingItem): number {
  if (item.market_value != null && Number.isFinite(item.market_value)) {
    return Math.max(0, item.market_value)
  }
  return 0
}

function buildRangePoints(range: ChartRange): Date[] {
  const now = new Date()
  const points: Date[] = []
  if (range === 'd') {
    for (let offset = 9; offset >= 0; offset -= 1) {
      const date = new Date(now)
      date.setHours(0, 0, 0, 0)
      date.setDate(date.getDate() - offset)
      points.push(date)
    }
    return points
  }

  if (range === 'm') {
    for (let offset = 11; offset >= 0; offset -= 1) {
      const date = new Date(now.getFullYear(), now.getMonth() - offset, 1)
      points.push(date)
    }
    return points
  }

  for (let offset = 5; offset >= 0; offset -= 1) {
    const date = new Date(now.getFullYear() - offset, 0, 1)
    points.push(date)
  }
  return points
}

function rangePointLabel(date: Date, range: ChartRange): string {
  if (range === 'd') {
    return date.toLocaleDateString('en-AU', { month: 'short', day: 'numeric' })
  }
  if (range === 'm') {
    return date.toLocaleDateString('en-AU', { month: 'short', year: '2-digit' })
  }
  return date.toLocaleDateString('en-AU', { year: 'numeric' })
}

function rangePointCutoff(date: Date, range: ChartRange): Date {
  if (range === 'd') {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999)
  }
  if (range === 'm') {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59, 999)
  }
  return new Date(date.getFullYear(), 11, 31, 23, 59, 59, 999)
}

function buildHoldingsSeries(
  items: HoldingItem[],
  range: ChartRange,
  basis: ExposureBasis,
): HoldingsChartPoint[] {
  const points = buildRangePoints(range)
  const contributions = items
    .map((item) => ({
      date: parseHoldingDate(item) ?? new Date(),
      amount:
        basis === 'live'
          ? (getLiveMarketValue(item) || getInvestedAmount(item))
          : getInvestedAmount(item),
    }))
    .filter((entry) => entry.amount > 0)
    .sort((left, right) => left.date.getTime() - right.date.getTime())

  const series = points.map((point) => {
    const cutoff = rangePointCutoff(point, range).getTime()
    const amount = contributions.reduce((sum, entry) => {
      return entry.date.getTime() <= cutoff ? sum + entry.amount : sum
    }, 0)
    return {
      label: rangePointLabel(point, range),
      amount,
      percent: 0,
    }
  })

  const baseline = series.find((point) => point.amount > 0)?.amount ?? 0
  return series.map((point) => ({
    ...point,
    percent: baseline > 0 ? ((point.amount - baseline) / baseline) * 100 : 0,
  }))
}

export function HoldingsScreen({ apiKey }: HoldingsScreenProps) {
  const [items, setItems] = useState<HoldingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createDraft, setCreateDraft] = useState<HoldingDraft>(EMPTY_DRAFT)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<HoldingDraft>(EMPTY_DRAFT)
  const [saving, setSaving] = useState(false)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('ticker-asc')
  const [portfolioFilter, setPortfolioFilter] = useState<string>('all')
  const [valueMode, setValueMode] = useState<ValueMode>('amount')
  const [chartMode, setChartMode] = useState<ChartMode>('line')
  const [chartRange, setChartRange] = useState<ChartRange>('m')
  const [exposureBasis, setExposureBasis] = useState<ExposureBasis>('live')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

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
      setError(fetchError instanceof Error ? fetchError.message : 'Failed to load holdings')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  const canCreate = useMemo(() => createDraft.ticker.trim().length > 0, [createDraft.ticker])
  const portfolioOptions = useMemo(() => {
    return Array.from(
      new Set(
        items
          .map((item) => item.account_label?.trim())
          .filter((value): value is string => Boolean(value)),
      ),
    ).sort((left, right) => left.localeCompare(right))
  }, [items])

  useEffect(() => {
    if (portfolioFilter === 'all') return
    if (portfolioOptions.includes(portfolioFilter)) return
    setPortfolioFilter('all')
  }, [portfolioFilter, portfolioOptions])

  const scopedItems = useMemo(() => {
    if (portfolioFilter === 'all') return items
    return items.filter((item) => item.account_label?.trim() === portfolioFilter)
  }, [items, portfolioFilter])

  const holdingsSeries = useMemo(
    () => buildHoldingsSeries(scopedItems, chartRange, exposureBasis),
    [chartRange, exposureBasis, scopedItems],
  )

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
        account_label: parseOptionalText(createDraft.account_label),
        market_exchange: parseOptionalText(createDraft.market_exchange),
        thesis_bucket: parseOptionalText(createDraft.thesis_bucket),
        status: parseOptionalText(createDraft.status),
        cost_currency: parseOptionalText(createDraft.cost_currency),
        opened_at: parseOptionalText(createDraft.opened_at),
        note: parseOptionalText(createDraft.note),
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
      setError(createError instanceof Error ? createError.message : 'Failed to add holding')
    } finally {
      setSaving(false)
    }
  }

  function beginEdit(item: HoldingItem) {
    setEditingId(item.holding_id)
    setExpandedId(item.holding_id)
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
        account_label: parseOptionalText(editDraft.account_label),
        market_exchange: parseOptionalText(editDraft.market_exchange),
        thesis_bucket: parseOptionalText(editDraft.thesis_bucket),
        status: parseOptionalText(editDraft.status),
        cost_currency: parseOptionalText(editDraft.cost_currency),
        opened_at: parseOptionalText(editDraft.opened_at),
        note: parseOptionalText(editDraft.note),
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
      setError(editError instanceof Error ? editError.message : 'Failed to update holding')
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
      if (expandedId === holdingId) {
        setExpandedId(null)
      }
      await load()
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : 'Failed to remove holding')
    } finally {
      setSaving(false)
    }
  }

  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    const filtered = scopedItems.filter((item) => {
      const status = normalizeStatus(item.status)
      if (statusFilter === 'active' && status !== 'active') return false
      if (statusFilter === 'archived' && status !== 'archived') return false
      if (statusFilter === 'unset' && status.length > 0) return false

      if (!normalizedQuery) return true
      const haystack = [
        item.ticker,
        item.account_label,
        item.note,
        item.status,
        item.thesis_bucket,
        item.market_exchange,
        item.cost_currency,
      ]
        .map((value) => String(value ?? '').toLowerCase())
        .join(' ')
      return haystack.includes(normalizedQuery)
    })

    filtered.sort((left, right) => {
      switch (sortKey) {
        case 'ticker-desc':
          return right.ticker.localeCompare(left.ticker)
        case 'quantity-desc':
          return (right.quantity ?? Number.NEGATIVE_INFINITY) - (left.quantity ?? Number.NEGATIVE_INFINITY)
        case 'avg-cost-desc':
          return (right.avg_cost ?? Number.NEGATIVE_INFINITY) - (left.avg_cost ?? Number.NEGATIVE_INFINITY)
        case 'updated-desc':
          return new Date(right.updated_at ?? 0).getTime() - new Date(left.updated_at ?? 0).getTime()
        case 'ticker-asc':
        default:
          return left.ticker.localeCompare(right.ticker)
      }
    })

    return filtered
  }, [query, scopedItems, sortKey, statusFilter])

  const summary = useMemo(() => {
    const accounts = new Set(
      scopedItems
        .map((item) => item.account_label?.trim())
        .filter((label): label is string => Boolean(label)),
    )
    const costKnown = scopedItems.filter((item) => item.avg_cost != null && item.quantity != null).length
    const livePriced = scopedItems.filter((item) => item.current_price != null && item.quantity != null).length
    const activeCount = scopedItems.filter((item) => {
      const status = normalizeStatus(item.status)
      return status.length === 0 || status === 'active'
    }).length

    const investedByCurrency = new Map<string, number>()
    const marketValueByCurrency = new Map<string, number>()
    for (const item of scopedItems) {
      if (item.avg_cost == null || item.quantity == null) continue
      const currency = (item.cost_currency?.trim().toUpperCase() || 'UNK')
      investedByCurrency.set(currency, (investedByCurrency.get(currency) ?? 0) + item.avg_cost * item.quantity)
    }
    for (const item of scopedItems) {
      if (item.market_value == null) continue
      const currency = (item.price_currency?.trim().toUpperCase() || item.cost_currency?.trim().toUpperCase() || 'UNK')
      marketValueByCurrency.set(currency, (marketValueByCurrency.get(currency) ?? 0) + item.market_value)
    }

    return {
      positions: scopedItems.length,
      accounts: accounts.size,
      costKnown,
      livePriced,
      activeCount,
      investedByCurrency,
      marketValueByCurrency,
    }
  }, [scopedItems])

  const totalPages = Math.max(1, Math.ceil(visibleItems.length / pageSize))

  useEffect(() => {
    setPage((current) => Math.min(Math.max(current, 1), totalPages))
  }, [totalPages])

  useEffect(() => {
    setPage(1)
  }, [portfolioFilter, query, statusFilter, sortKey, pageSize])

  const pagedItems = useMemo(() => {
    const offset = (page - 1) * pageSize
    return visibleItems.slice(offset, offset + pageSize)
  }, [page, pageSize, visibleItems])

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Portfolio Holdings</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={portfolioFilter} onValueChange={setPortfolioFilter}>
            <SelectTrigger className="w-[210px]">
              <SelectValue placeholder="Portfolio scope" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All portfolios</SelectItem>
              {portfolioOptions.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {loading ? <Badge variant="outline">Loading</Badge> : null}
          <Button onClick={() => void load()} disabled={loading || saving}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-wide text-muted-foreground">Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{summary.positions}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-wide text-muted-foreground">Active</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{summary.activeCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-wide text-muted-foreground">Accounts</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{portfolioFilter === 'all' ? summary.accounts : 1}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-mono uppercase tracking-wide text-muted-foreground">Live Prices</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">
              {summary.livePriced}/{summary.positions}
            </p>
            <div className="mt-1 flex flex-wrap gap-1 text-xs text-muted-foreground">
              <span>Cost basis known: {summary.costKnown}</span>
              {summary.investedByCurrency.size === 0 ? (
                <span>Invested capital unavailable</span>
              ) : (
                Array.from(summary.investedByCurrency.entries())
                  .slice(0, 2)
                  .map(([currency, total]) => (
                    <Badge key={currency} variant="secondary" className="font-mono text-[10px]">
                      Cost {currency} {formatNumber(total)}
                    </Badge>
                  ))
              )}
              {summary.marketValueByCurrency.size > 0
                ? Array.from(summary.marketValueByCurrency.entries())
                  .slice(0, 2)
                  .map(([currency, total]) => (
                    <Badge key={`mv-${currency}`} variant="outline" className="font-mono text-[10px]">
                      Mkt {currency} {formatNumber(total)}
                    </Badge>
                  ))
                : null}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-mono uppercase tracking-wide">Holdings Exposure</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <ToggleGroup type="single" value={valueMode} onValueChange={(value) => value && setValueMode(value as ValueMode)} variant="outline" size="sm">
              <ToggleGroupItem id="amount" value="amount" aria-label="Amount mode">
                Amount
              </ToggleGroupItem>
              <ToggleGroupItem id="percent" value="percent" aria-label="Percent mode">
                Percent
              </ToggleGroupItem>
            </ToggleGroup>
            <ToggleGroup type="single" value={chartMode} onValueChange={(value) => value && setChartMode(value as ChartMode)} variant="outline" size="sm">
              <ToggleGroupItem id="line" value="line" aria-label="Line mode">
                Line
              </ToggleGroupItem>
              <ToggleGroupItem id="bar" value="bar" aria-label="Bar mode">
                Bar
              </ToggleGroupItem>
            </ToggleGroup>
            <ToggleGroup type="single" value={chartRange} onValueChange={(value) => value && setChartRange(value as ChartRange)} variant="outline" size="sm">
              <ToggleGroupItem id="d" value="d" aria-label="Daily range">
                D
              </ToggleGroupItem>
              <ToggleGroupItem id="m" value="m" aria-label="Monthly range">
                M
              </ToggleGroupItem>
              <ToggleGroupItem id="y" value="y" aria-label="Yearly range">
                Y
              </ToggleGroupItem>
            </ToggleGroup>
            <ToggleGroup
              type="single"
              value={exposureBasis}
              onValueChange={(value) => value && setExposureBasis(value as ExposureBasis)}
              variant="outline"
              size="sm"
            >
              <ToggleGroupItem id="live" value="live" aria-label="Live valuation basis">
                Live
              </ToggleGroupItem>
              <ToggleGroupItem id="cost" value="cost" aria-label="Cost basis exposure">
                Cost
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
          {holdingsSeries.every((point) => point.amount === 0) ? (
            <p className="rounded border border-dashed border-border/70 px-3 py-6 text-center text-sm text-muted-foreground">
              Add holdings with quantity and average cost to populate this chart.
            </p>
          ) : (
            <ChartContainer
              config={{
                value: {
                  label: valueMode === 'amount' ? 'Amount' : 'Percent',
                  color: 'oklch(0.62 0.16 165)',
                },
              }}
              className="h-[260px] w-full aspect-auto"
            >
              {chartMode === 'line' ? (
                <LineChart data={holdingsSeries} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={22} />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    width={82}
                    tickFormatter={(value) => formatChartNumber(Number(value), valueMode)}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => formatChartNumber(Number(value), valueMode)}
                      />
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey={valueMode}
                    stroke="var(--color-value)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              ) : (
                <BarChart data={holdingsSeries} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={22} />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    width={82}
                    tickFormatter={(value) => formatChartNumber(Number(value), valueMode)}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => formatChartNumber(Number(value), valueMode)}
                      />
                    }
                  />
                  <Bar dataKey={valueMode} fill="var(--color-value)" radius={[4, 4, 0, 0]} />
                </BarChart>
              )}
            </ChartContainer>
          )}
          <p className="text-xs text-muted-foreground">
            {exposureBasis === 'live'
              ? 'Live basis uses latest market value where available, otherwise falls back to quantity x average cost.'
              : 'Cost basis uses quantity x average cost, rolled up by opened date.'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-mono uppercase tracking-wide">Add Holding</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 md:grid-cols-4">
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
          </div>
          <div className="grid gap-2 md:grid-cols-5">
            <Input
              placeholder="Thesis bucket"
              value={createDraft.thesis_bucket}
              onChange={(event) =>
                setCreateDraft((current) => ({ ...current, thesis_bucket: event.target.value }))
              }
            />
            <Input
              placeholder="Exchange (ASX/NASDAQ)"
              value={createDraft.market_exchange}
              onChange={(event) =>
                setCreateDraft((current) => ({ ...current, market_exchange: event.target.value }))
              }
            />
            <Input
              placeholder="Status"
              value={createDraft.status}
              onChange={(event) =>
                setCreateDraft((current) => ({ ...current, status: event.target.value }))
              }
            />
            <Input
              placeholder="Currency (AUD)"
              value={createDraft.cost_currency}
              onChange={(event) =>
                setCreateDraft((current) => ({ ...current, cost_currency: event.target.value }))
              }
            />
            <Input
              placeholder="Opened at (YYYY-MM-DD)"
              value={createDraft.opened_at}
              onChange={(event) =>
                setCreateDraft((current) => ({ ...current, opened_at: event.target.value }))
              }
            />
          </div>
          <div className="flex flex-wrap gap-2">
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-mono uppercase tracking-wide">Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-[2fr_1fr_1fr_auto]">
          <Input
            placeholder="Search ticker, account, status, note"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as StatusFilter)}>
            <SelectTrigger>
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
              <SelectItem value="unset">Unset</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sortKey} onValueChange={(value) => setSortKey(value as SortKey)}>
            <SelectTrigger>
              <SelectValue placeholder="Sort" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ticker-asc">Ticker A-Z</SelectItem>
              <SelectItem value="ticker-desc">Ticker Z-A</SelectItem>
              <SelectItem value="quantity-desc">Quantity (desc)</SelectItem>
              <SelectItem value="avg-cost-desc">Avg cost (desc)</SelectItem>
              <SelectItem value="updated-desc">Recently updated</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center text-xs text-muted-foreground">
            {visibleItems.length} shown · page {page}/{totalPages}
          </div>
        </CardContent>
      </Card>

      {error ? (
        <p className="rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-mono uppercase tracking-wide">Holdings Ledger</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead className="font-mono">Quantity</TableHead>
                <TableHead className="font-mono">Avg Cost</TableHead>
                <TableHead className="font-mono">Current Px</TableHead>
                <TableHead className="font-mono">Total Value</TableHead>
                <TableHead className="font-mono">Unrealized P&L</TableHead>
                <TableHead>Account</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="py-8 text-center text-muted-foreground">
                    {loading ? 'Loading holdings...' : 'No holdings yet.'}
                  </TableCell>
                </TableRow>
              ) : (
                pagedItems.map((item) => {
                  const editing = editingId === item.holding_id
                  const expanded = expandedId === item.holding_id || editing

                  return (
                    <Fragment key={item.holding_id}>
                      <TableRow>
                        <TableCell className="align-top">
                          {editing ? (
                            <Input
                              value={editDraft.ticker}
                              onChange={(event) =>
                                setEditDraft((current) => ({ ...current, ticker: event.target.value }))
                              }
                            />
                          ) : (
                            <span className="font-medium">{item.ticker}</span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono align-top">
                          {editing ? (
                            <Input
                              value={editDraft.quantity}
                              onChange={(event) =>
                                setEditDraft((current) => ({ ...current, quantity: event.target.value }))
                              }
                            />
                          ) : (
                            formatNumber(item.quantity)
                          )}
                        </TableCell>
                        <TableCell className="font-mono align-top">
                          {editing ? (
                            <Input
                              value={editDraft.avg_cost}
                              onChange={(event) =>
                                setEditDraft((current) => ({ ...current, avg_cost: event.target.value }))
                              }
                            />
                          ) : (
                            formatNumber(item.avg_cost)
                          )}
                        </TableCell>
                        <TableCell className="font-mono align-top">
                          {formatCurrencyAmount(item.current_price, item.price_currency || item.cost_currency)}
                        </TableCell>
                        <TableCell className="font-mono align-top">
                          {formatCurrencyAmount(item.market_value, item.price_currency || item.cost_currency)}
                        </TableCell>
                        <TableCell className="font-mono align-top">
                          {formatCurrencyAmount(item.unrealized_pnl, item.price_currency || item.cost_currency)}
                        </TableCell>
                        <TableCell className="align-top">
                          {editing ? (
                            <Input
                              value={editDraft.account_label}
                              onChange={(event) =>
                                setEditDraft((current) => ({ ...current, account_label: event.target.value }))
                              }
                            />
                          ) : (
                            item.account_label || '-'
                          )}
                        </TableCell>
                        <TableCell className="align-top">
                          {editing ? (
                            <Input
                              value={editDraft.status}
                              onChange={(event) =>
                                setEditDraft((current) => ({ ...current, status: event.target.value }))
                              }
                            />
                          ) : item.status ? (
                            <Badge variant={normalizeStatus(item.status) === 'archived' ? 'secondary' : 'outline'}>
                              {item.status}
                            </Badge>
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground align-top">
                          {formatTimestamp(item.updated_at)}
                        </TableCell>
                        <TableCell className="align-top">
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
                              variant="ghost"
                              onClick={() =>
                                setExpandedId((current) =>
                                  current === item.holding_id ? null : item.holding_id,
                                )
                              }
                            >
                              {expanded ? 'Hide' : 'Details'}
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => void removeHolding(item.holding_id)}
                              disabled={saving}
                            >
                              Remove
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                      {expanded ? (
                        <TableRow>
                          <TableCell colSpan={10}>
                            <div className="grid gap-2 md:grid-cols-5">
                              <div>
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Thesis Bucket</p>
                                {editing ? (
                                  <Input
                                    value={editDraft.thesis_bucket}
                                    onChange={(event) =>
                                      setEditDraft((current) => ({ ...current, thesis_bucket: event.target.value }))
                                    }
                                  />
                                ) : (
                                  <p className="text-sm">{item.thesis_bucket || '-'}</p>
                                )}
                              </div>
                              <div>
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Exchange</p>
                                {editing ? (
                                  <Input
                                    value={editDraft.market_exchange}
                                    onChange={(event) =>
                                      setEditDraft((current) => ({ ...current, market_exchange: event.target.value }))
                                    }
                                  />
                                ) : (
                                  <p className="text-sm">{item.market_exchange || '-'}</p>
                                )}
                              </div>
                              <div>
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Cost Currency</p>
                                {editing ? (
                                  <Input
                                    value={editDraft.cost_currency}
                                    onChange={(event) =>
                                      setEditDraft((current) => ({ ...current, cost_currency: event.target.value }))
                                    }
                                  />
                                ) : (
                                  <p className="text-sm">{item.cost_currency || '-'}</p>
                                )}
                              </div>
                              <div>
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Opened At</p>
                                {editing ? (
                                  <Input
                                    value={editDraft.opened_at}
                                    onChange={(event) =>
                                      setEditDraft((current) => ({ ...current, opened_at: event.target.value }))
                                    }
                                  />
                                ) : (
                                  <p className="text-sm">{item.opened_at || '-'}</p>
                                )}
                              </div>
                              <div>
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Price As Of</p>
                                <p className="text-sm">{formatTimestamp(item.price_as_of)}</p>
                              </div>
                              <div className="md:col-span-5">
                                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Note</p>
                                {editing ? (
                                  <Input
                                    value={editDraft.note}
                                    onChange={(event) =>
                                      setEditDraft((current) => ({ ...current, note: event.target.value }))
                                    }
                                  />
                                ) : (
                                  <p className="text-sm">{item.note || '-'}</p>
                                )}
                              </div>
                              {item.valuation_warning ? (
                                <div className="md:col-span-5 rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-200">
                                  {item.valuation_warning}
                                </div>
                              ) : null}
                            </div>
                          </TableCell>
                        </TableRow>
                      ) : null}
                    </Fragment>
                  )
                })
              )}
            </TableBody>
          </Table>
          {visibleItems.length > 0 ? (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Rows</span>
                <Select
                  value={String(pageSize)}
                  onValueChange={(value) => setPageSize(Number(value))}
                >
                  <SelectTrigger className="h-8 w-[84px]">
                    <SelectValue placeholder="Rows" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="25">25</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1}
                >
                  Prev
                </Button>
                <span className="font-mono text-xs text-muted-foreground">
                  {page} / {totalPages}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
