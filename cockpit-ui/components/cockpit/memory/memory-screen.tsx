'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useCockpitStore } from '@/lib/cockpit-store'

type MemorySection = 'company' | 'sector' | 'macro' | 'strategy'
type MemoryKind = 'company_entry' | 'sector_entry' | 'macro_entry' | 'thesis_entry' | 'thesis_proposal'
type StrategyProposalType = 'create_thesis' | 'add_evidence' | 'invalidate'
type EditableLevel = 'company' | 'sector' | 'macro' | 'strategy'

interface MemoryScreenProps {
  apiKey: string
}

interface MemoryPayload {
  ticker: string
  summary?: Record<string, unknown>
  company_memory?: {
    entries?: Record<string, unknown>[]
    change_log?: Record<string, unknown>[]
  }
  market_memory?: {
    sector?: string | null
    sector_items?: Record<string, unknown>[]
    macro_items?: Record<string, unknown>[]
  }
  user_thesis_memory?: {
    entries?: Record<string, unknown>[]
    proposals?: Record<string, unknown>[]
  }
  errors?: unknown[]
}

interface CompanyDumpPayload {
  ticker: string
  summary?: Record<string, unknown>
  latest_financial_snapshot?: Record<string, unknown> | null
  risk_notes?: Record<string, unknown>[]
  errors?: unknown[]
}

interface MemoryRow {
  key: string
  section: MemorySection
  kind: MemoryKind
  entryId: number | null
  proposalId: string | null
  type: string
  statement: string
  status: string
  seenAt: string
  signal: string | null
  confidence: number | null
  editable: boolean
}

const SECTION_LABELS: Record<MemorySection, string> = {
  company: 'Company Memory',
  sector: 'Sector Memory',
  macro: 'Macro Memory',
  strategy: 'Strategy / Thesis Memory',
}

function asObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function asArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return []
  return value.filter(
    (item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item),
  )
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function asString(value: unknown, fallback: string = ''): string {
  if (typeof value === 'string') return value
  if (value == null) return fallback
  return String(value)
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function asInt(value: unknown): number | null {
  const parsed = asNumber(value)
  if (parsed == null) return null
  return Math.trunc(parsed)
}

function formatTimestamp(value: unknown): string {
  const text = asString(value).trim()
  if (!text) return '-'
  return text.slice(0, 19).replace('T', ' ')
}

function summarizeErrorPayload(raw: unknown): string {
  if (typeof raw === 'string') return raw
  const data = asObject(raw)
  const detail = asString(data.detail)
  if (detail) return detail
  const message = asString(data.message)
  if (message) return message
  return 'Request failed'
}

function buildRows(payload: MemoryPayload): MemoryRow[] {
  const rows: MemoryRow[] = []
  const companyMemory = asObject(payload.company_memory)
  const marketMemory = asObject(payload.market_memory)
  const thesisMemory = asObject(payload.user_thesis_memory)

  for (const item of asArray(companyMemory.entries)) {
    const entryId = asInt(item.entry_id)
    rows.push({
      key: `company:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'company',
      kind: 'company_entry',
      entryId,
      proposalId: null,
      type: asString(item.type, 'observed_fact'),
      statement: asString(item.statement, '-'),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.last_seen_at ?? item.updated_at ?? item.created_at),
      signal: null,
      confidence: asNumber(item.confidence),
      editable: asString(item.status, '').toLowerCase() === 'active' && entryId != null,
    })
  }

  for (const item of asArray(marketMemory.sector_items)) {
    const entryId = asInt(item.entry_id)
    rows.push({
      key: `sector:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'sector',
      kind: 'sector_entry',
      entryId,
      proposalId: null,
      type: asString(item.type, 'sector_trend'),
      statement: asString(item.statement, '-'),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.last_seen_at ?? item.updated_at ?? item.created_at),
      signal: null,
      confidence: asNumber(item.confidence),
      editable: asString(item.status, '').toLowerCase() === 'active' && entryId != null,
    })
  }

  for (const item of asArray(marketMemory.macro_items)) {
    const entryId = asInt(item.entry_id)
    rows.push({
      key: `macro:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'macro',
      kind: 'macro_entry',
      entryId,
      proposalId: null,
      type: asString(item.type, 'macro_theme'),
      statement: asString(item.statement, '-'),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.last_seen_at ?? item.updated_at ?? item.created_at),
      signal: null,
      confidence: asNumber(item.confidence),
      editable: asString(item.status, '').toLowerCase() === 'active' && entryId != null,
    })
  }

  for (const item of asArray(thesisMemory.entries)) {
    const entryId = asInt(item.entry_id)
    rows.push({
      key: `thesis-entry:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'strategy',
      kind: 'thesis_entry',
      entryId,
      proposalId: null,
      type: asString(item.entry_type, 'thesis'),
      statement: asString(item.statement, '-'),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.updated_at ?? item.created_at),
      signal: asString(item.signal) || null,
      confidence: asNumber(item.confidence),
      editable: false,
    })
  }

  for (const item of asArray(thesisMemory.proposals)) {
    const proposalId = asString(item.proposal_id)
    rows.push({
      key: `thesis-proposal:${proposalId || Math.random().toString(36).slice(2)}`,
      section: 'strategy',
      kind: 'thesis_proposal',
      entryId: null,
      proposalId: proposalId || null,
      type: asString(item.proposal_type, 'proposal'),
      statement: asString(item.statement, '-'),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.confirmed_at ?? item.applied_at ?? item.created_at),
      signal: asString(item.signal) || null,
      confidence: asNumber(item.confidence),
      editable: false,
    })
  }

  return rows
}

export function MemoryScreen({ apiKey }: MemoryScreenProps) {
  const { activeTicker, setActiveTicker } = useCockpitStore()
  const [tickerInput, setTickerInput] = useState(activeTicker)
  const [activeSection, setActiveSection] = useState<MemorySection>('company')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Load a ticker to browse Tenn memory levels.')
  const [memoryPayload, setMemoryPayload] = useState<MemoryPayload | null>(null)
  const [companyDump, setCompanyDump] = useState<CompanyDumpPayload | null>(null)
  const [rows, setRows] = useState<MemoryRow[]>([])
  const [level, setLevel] = useState<EditableLevel>('company')
  const [entryType, setEntryType] = useState('')
  const [statement, setStatement] = useState('')
  const [strategySignal, setStrategySignal] = useState('')
  const [strategyProposalType, setStrategyProposalType] = useState<StrategyProposalType>('create_thesis')
  const [editTarget, setEditTarget] = useState<MemoryRow | null>(null)

  useEffect(() => {
    if (!tickerInput && activeTicker) {
      setTickerInput(activeTicker)
    }
  }, [activeTicker, tickerInput])

  const query = search.trim().toLowerCase()

  const rowsBySection = useMemo(() => {
    const grouped: Record<MemorySection, MemoryRow[]> = {
      company: [],
      sector: [],
      macro: [],
      strategy: [],
    }
    for (const row of rows) {
      grouped[row.section].push(row)
    }
    return grouped
  }, [rows])

  const filteredRows = useMemo(() => {
    const source = rowsBySection[activeSection]
    if (!query) return source
    return source.filter((row) => {
      const haystack = [
        row.type,
        row.statement,
        row.status,
        row.signal ?? '',
        row.entryId != null ? String(row.entryId) : '',
        row.proposalId ?? '',
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    })
  }, [activeSection, query, rowsBySection])

  const summary = asObject(memoryPayload?.summary)
  const companyDumpSummary = asObject(companyDump?.summary)
  const latestSnapshot = asObject(companyDump?.latest_financial_snapshot)

  const headers = useMemo(() => {
    const nextHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (apiKey) {
      nextHeaders['X-API-Key'] = apiKey
    }
    return nextHeaders
  }, [apiKey])

  const loadMemory = useCallback(async () => {
    const ticker = tickerInput.trim().toUpperCase()
    if (!ticker) {
      setStatus('Ticker is required.')
      return
    }

    setLoading(true)
    setStatus(`Loading memory for ${ticker}...`)
    setActiveTicker(ticker)

    try {
      const [memoryResponse, dumpResponse] = await Promise.all([
        fetch(
          `/api/cockpit/memory?ticker=${encodeURIComponent(ticker)}&company_memory_entries_limit=500&company_memory_change_limit=300&market_memory_limit=300&user_thesis_entries_limit=250&user_thesis_proposals_limit=250`,
          {
            cache: 'no-store',
            headers,
          },
        ),
        fetch(
          `/api/cockpit/memory/company-dump?ticker=${encodeURIComponent(ticker)}&docs_limit=40&financials_limit=24&announcements_limit=40&risk_notes_limit=20`,
          {
            cache: 'no-store',
            headers,
          },
        ),
      ])

      if (!memoryResponse.ok) {
        const raw = await memoryResponse.json().catch(() => null)
        throw new Error(summarizeErrorPayload(raw) || `Memory load failed (${memoryResponse.status})`)
      }

      const memoryData = (await memoryResponse.json()) as MemoryPayload
      setMemoryPayload(memoryData)
      setRows(buildRows(memoryData))

      if (dumpResponse.ok) {
        const dumpData = (await dumpResponse.json()) as CompanyDumpPayload
        setCompanyDump(dumpData)
      } else {
        setCompanyDump(null)
      }

      const loadErrors = asList(memoryData.errors)
      if (loadErrors.length > 0) {
        setStatus(`Loaded with warnings for ${ticker}.`)
      } else {
        setStatus(`Loaded memory for ${ticker}.`)
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Failed to load memory.')
      setMemoryPayload(null)
      setCompanyDump(null)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [headers, setActiveTicker, tickerInput])

  const submitMutation = useCallback(
    async (path: string, body: Record<string, unknown> | null) => {
      const response = await fetch(path, {
        method: 'POST',
        headers,
        body: body ? JSON.stringify(body) : undefined,
      })
      if (!response.ok) {
        const raw = await response.json().catch(() => null)
        throw new Error(summarizeErrorPayload(raw) || `Mutation failed (${response.status})`)
      }
      return response.json().catch(() => ({}))
    },
    [headers],
  )

  const resetEditor = useCallback(() => {
    setEditTarget(null)
    setStatement('')
    setEntryType('')
    setLevel('company')
    setStrategySignal('')
    setStrategyProposalType('create_thesis')
  }, [])

  const applyAdd = useCallback(async () => {
    const ticker = tickerInput.trim().toUpperCase()
    const nextStatement = statement.trim()
    if (!ticker) {
      setStatus('Ticker is required.')
      return
    }
    if (!nextStatement) {
      setStatus('Statement is required.')
      return
    }

    setBusy(true)
    try {
      if (level === 'company') {
        await submitMutation('/api/cockpit/memory/company/add', {
          ticker,
          type: entryType.trim() || 'observed_fact',
          statement: nextStatement,
          note: 'web-memory-tab',
        })
      } else if (level === 'sector') {
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'sector',
          ticker,
          type: entryType.trim() || 'sector_trend',
          statement: nextStatement,
          note: 'web-memory-tab',
        })
      } else if (level === 'macro') {
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'macro',
          ticker,
          macro_topic: 'macro',
          type: entryType.trim() || 'macro_theme',
          statement: nextStatement,
          note: 'web-memory-tab',
        })
      } else {
        await submitMutation('/api/cockpit/memory/thesis/proposals', {
          ticker,
          proposal_type: strategyProposalType,
          statement: nextStatement,
          signal: strategySignal.trim() || null,
          is_supporting: true,
          note: 'web-memory-tab',
        })
      }

      setStatus(`Added ${SECTION_LABELS[level === 'strategy' ? 'strategy' : level]} item for ${ticker}.`)
      setStatement('')
      setEntryType('')
      setStrategySignal('')
      await loadMemory()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Add failed.')
    } finally {
      setBusy(false)
    }
  }, [entryType, level, loadMemory, statement, strategyProposalType, strategySignal, submitMutation, tickerInput])

  const startEdit = useCallback((row: MemoryRow) => {
    if (!row.editable) return
    setEditTarget(row)
    setStatement(row.statement)
    setEntryType(row.type)
    setStrategySignal(row.signal ?? '')
    if (row.kind === 'company_entry') setLevel('company')
    if (row.kind === 'sector_entry') setLevel('sector')
    if (row.kind === 'macro_entry') setLevel('macro')
  }, [])

  const applyEdit = useCallback(async () => {
    if (!editTarget) {
      setStatus('Select an editable row first.')
      return
    }
    const ticker = tickerInput.trim().toUpperCase()
    const nextStatement = statement.trim()
    if (!ticker || !nextStatement) {
      setStatus('Ticker and statement are required.')
      return
    }
    if (!editTarget.entryId) {
      setStatus('Selected row has no entry id.')
      return
    }

    setBusy(true)
    try {
      if (editTarget.kind === 'company_entry') {
        await submitMutation('/api/cockpit/memory/company/expire', {
          ticker,
          entry_id: editTarget.entryId,
          note: 'superseded-via-web-memory-tab',
        })
        await submitMutation('/api/cockpit/memory/company/add', {
          ticker,
          type: entryType.trim() || editTarget.type || 'observed_fact',
          statement: nextStatement,
          note: 'edited-via-web-memory-tab',
        })
      } else if (editTarget.kind === 'sector_entry') {
        await submitMutation('/api/cockpit/memory/market/expire', {
          scope: 'sector',
          entry_id: editTarget.entryId,
          note: 'superseded-via-web-memory-tab',
        })
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'sector',
          ticker,
          type: entryType.trim() || editTarget.type || 'sector_trend',
          statement: nextStatement,
          note: 'edited-via-web-memory-tab',
        })
      } else if (editTarget.kind === 'macro_entry') {
        await submitMutation('/api/cockpit/memory/market/expire', {
          scope: 'macro',
          entry_id: editTarget.entryId,
          note: 'superseded-via-web-memory-tab',
        })
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'macro',
          ticker,
          macro_topic: 'macro',
          type: entryType.trim() || editTarget.type || 'macro_theme',
          statement: nextStatement,
          note: 'edited-via-web-memory-tab',
        })
      } else {
        setStatus('Only company/sector/macro rows are directly editable.')
        return
      }

      setStatus(`Updated row ${editTarget.entryId} by expiring + replacing it.`)
      resetEditor()
      await loadMemory()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Edit failed.')
    } finally {
      setBusy(false)
    }
  }, [editTarget, entryType, loadMemory, resetEditor, statement, submitMutation, tickerInput])

  const expireRow = useCallback(
    async (row: MemoryRow) => {
      const ticker = tickerInput.trim().toUpperCase()
      if (!row.entryId) {
        setStatus('Row has no entry id.')
        return
      }
      setBusy(true)
      try {
        if (row.kind === 'company_entry') {
          await submitMutation('/api/cockpit/memory/company/expire', {
            ticker,
            entry_id: row.entryId,
            note: 'expired-via-web-memory-tab',
          })
        } else if (row.kind === 'sector_entry') {
          await submitMutation('/api/cockpit/memory/market/expire', {
            scope: 'sector',
            entry_id: row.entryId,
            note: 'expired-via-web-memory-tab',
          })
        } else if (row.kind === 'macro_entry') {
          await submitMutation('/api/cockpit/memory/market/expire', {
            scope: 'macro',
            entry_id: row.entryId,
            note: 'expired-via-web-memory-tab',
          })
        } else {
          return
        }
        setStatus(`Expired row ${row.entryId}.`)
        await loadMemory()
      } catch (error) {
        setStatus(error instanceof Error ? error.message : 'Expire failed.')
      } finally {
        setBusy(false)
      }
    },
    [loadMemory, submitMutation, tickerInput],
  )

  const runProposalAction = useCallback(
    async (row: MemoryRow, action: 'confirm' | 'reject' | 'apply') => {
      if (!row.proposalId) {
        setStatus('Proposal id missing.')
        return
      }
      setBusy(true)
      try {
        if (action === 'confirm') {
          await submitMutation(`/api/cockpit/memory/thesis/proposals/${encodeURIComponent(row.proposalId)}/confirm`, {
            note: 'confirmed-via-web-memory-tab',
          })
        } else if (action === 'reject') {
          await submitMutation(`/api/cockpit/memory/thesis/proposals/${encodeURIComponent(row.proposalId)}/reject`, {
            note: 'rejected-via-web-memory-tab',
          })
        } else {
          await submitMutation(`/api/cockpit/memory/thesis/proposals/${encodeURIComponent(row.proposalId)}/apply`, null)
        }
        setStatus(`Proposal ${row.proposalId} ${action}ed.`)
        await loadMemory()
      } catch (error) {
        setStatus(error instanceof Error ? error.message : 'Proposal action failed.')
      } finally {
        setBusy(false)
      }
    },
    [loadMemory, submitMutation],
  )

  const frameworkNotes = [
    'Canonical financial truth remains backend-authoritative.',
    'Company memory captures ticker-scoped qualitative signals.',
    'Market memory captures sector + macro qualitative signals.',
    'Strategy memory is user-thesis (proposal -> confirm -> apply).',
  ]

  const strategyEntries = rowsBySection.strategy.filter((row) => row.kind === 'thesis_entry').length
  const strategyProposals = rowsBySection.strategy.filter((row) => row.kind === 'thesis_proposal').length

  const memoryErrors = asList(memoryPayload?.errors)
  const dumpErrors = asList(companyDump?.errors)

  return (
    <div className="grid h-full min-h-0 gap-4 p-4 lg:grid-cols-[2.1fr_1fr]">
      <div className="flex min-h-0 flex-col gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Memory Workbench</CardTitle>
            <CardDescription>
              Browse, search, edit, and add memory across company, sector, macro, and strategy levels.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <Input
                value={tickerInput}
                placeholder="Ticker (e.g. BHP)"
                onChange={(event) => setTickerInput(event.target.value.toUpperCase())}
              />
              <Button onClick={() => void loadMemory()} disabled={loading || busy}>
                {loading ? 'Loading…' : 'Load'}
              </Button>
              <Button variant="outline" onClick={() => void loadMemory()} disabled={loading || busy}>
                Refresh
              </Button>
            </div>

            <div className="grid gap-2 md:grid-cols-[1fr_auto]">
              <Input
                value={search}
                placeholder="Search statements, type, status, id"
                onChange={(event) => setSearch(event.target.value)}
              />
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline">company {rowsBySection.company.length}</Badge>
                <Badge variant="outline">sector {rowsBySection.sector.length}</Badge>
                <Badge variant="outline">macro {rowsBySection.macro.length}</Badge>
                <Badge variant="outline">strategy {rowsBySection.strategy.length}</Badge>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">{status}</p>
            {memoryErrors.length > 0 ? (
              <p className="text-xs text-destructive">Memory warnings: {memoryErrors.map((item) => asString(item)).join(' | ')}</p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>{editTarget ? 'Edit Memory Entry' : 'Add Memory Entry'}</CardTitle>
            <CardDescription>
              {editTarget
                ? `Editing ${editTarget.kind} #${editTarget.entryId ?? '-'} using safe replace (expire + add).`
                : 'Add a qualitative note or thesis proposal to Tenn memory.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 md:grid-cols-3">
              <label className="space-y-1 text-xs text-muted-foreground">
                <span>Level</span>
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                  value={level}
                  onChange={(event) => setLevel(event.target.value as EditableLevel)}
                  disabled={Boolean(editTarget)}
                >
                  <option value="company">Company</option>
                  <option value="sector">Sector</option>
                  <option value="macro">Macro</option>
                  <option value="strategy">Strategy</option>
                </select>
              </label>

              <label className="space-y-1 text-xs text-muted-foreground">
                <span>{level === 'strategy' ? 'Proposal Type' : 'Type'}</span>
                {level === 'strategy' ? (
                  <select
                    className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                    value={strategyProposalType}
                    onChange={(event) => setStrategyProposalType(event.target.value as StrategyProposalType)}
                    disabled={busy}
                  >
                    <option value="create_thesis">create_thesis</option>
                    <option value="add_evidence">add_evidence</option>
                    <option value="invalidate">invalidate</option>
                  </select>
                ) : (
                  <Input
                    value={entryType}
                    placeholder={
                      level === 'company'
                        ? 'observed_fact / risk / guidance_shift'
                        : level === 'sector'
                        ? 'sector_trend / sector_risk'
                        : 'macro_theme / macro_risk'
                    }
                    onChange={(event) => setEntryType(event.target.value)}
                    disabled={busy}
                  />
                )}
              </label>

              <label className="space-y-1 text-xs text-muted-foreground">
                <span>Signal (strategy only)</span>
                <Input
                  value={strategySignal}
                  placeholder="BUY / HOLD / SELL"
                  onChange={(event) => setStrategySignal(event.target.value.toUpperCase())}
                  disabled={busy || level !== 'strategy'}
                />
              </label>
            </div>

            <Textarea
              value={statement}
              placeholder="Enter memory statement..."
              onChange={(event) => setStatement(event.target.value)}
              rows={3}
              disabled={busy}
            />

            <div className="flex flex-wrap items-center gap-2">
              {editTarget ? (
                <>
                  <Button onClick={() => void applyEdit()} disabled={busy || loading}>
                    Save Edit
                  </Button>
                  <Button variant="outline" onClick={resetEditor} disabled={busy || loading}>
                    Cancel Edit
                  </Button>
                </>
              ) : (
                <Button onClick={() => void applyAdd()} disabled={busy || loading}>
                  Add Entry
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="flex min-h-0 flex-1 flex-col">
          <CardHeader className="pb-3">
            <CardTitle>Memory Levels</CardTitle>
            <CardDescription>Each level is isolated so you can manage context Tenn can use during reasoning.</CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            <Tabs value={activeSection} onValueChange={(value) => setActiveSection(value as MemorySection)} className="flex min-h-0 flex-1 flex-col gap-3">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="company">Company</TabsTrigger>
                <TabsTrigger value="sector">Sector</TabsTrigger>
                <TabsTrigger value="macro">Macro</TabsTrigger>
                <TabsTrigger value="strategy">Strategy</TabsTrigger>
              </TabsList>

              {(['company', 'sector', 'macro', 'strategy'] as MemorySection[]).map((section) => (
                <TabsContent key={section} value={section} className="m-0 flex min-h-0 flex-1 flex-col">
                  <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                    <span>{SECTION_LABELS[section]}</span>
                    <span>{section === activeSection ? `${filteredRows.length} visible` : `${rowsBySection[section].length} total`}</span>
                  </div>
                  <div className="min-h-0 flex-1 overflow-auto rounded-md border border-border/70">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead className="w-[48%]">Statement</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Seen</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(section === activeSection ? filteredRows : rowsBySection[section]).map((row) => {
                          const statusLower = row.status.toLowerCase()
                          return (
                            <TableRow key={row.key}>
                              <TableCell className="font-mono text-xs">
                                {row.entryId != null ? row.entryId : row.proposalId ?? '-'}
                              </TableCell>
                              <TableCell className="text-xs">{row.type || '-'}</TableCell>
                              <TableCell className="max-w-0 whitespace-normal text-sm">{row.statement}</TableCell>
                              <TableCell>
                                <Badge variant={statusLower === 'active' || statusLower === 'applied' ? 'secondary' : 'outline'}>
                                  {row.status}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-xs text-muted-foreground">{row.seenAt}</TableCell>
                              <TableCell>
                                <div className="flex flex-wrap gap-1">
                                  {row.editable ? (
                                    <Button size="sm" variant="outline" onClick={() => startEdit(row)} disabled={busy || loading}>
                                      Edit
                                    </Button>
                                  ) : null}
                                  {row.editable ? (
                                    <Button
                                      size="sm"
                                      variant="destructive"
                                      onClick={() => void expireRow(row)}
                                      disabled={busy || loading}
                                    >
                                      Expire
                                    </Button>
                                  ) : null}
                                  {row.kind === 'thesis_proposal' && row.status === 'pending' && row.proposalId ? (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => void runProposalAction(row, 'confirm')}
                                      disabled={busy || loading}
                                    >
                                      Confirm
                                    </Button>
                                  ) : null}
                                  {row.kind === 'thesis_proposal' && (row.status === 'pending' || row.status === 'confirmed') && row.proposalId ? (
                                    <Button
                                      size="sm"
                                      variant="destructive"
                                      onClick={() => void runProposalAction(row, 'reject')}
                                      disabled={busy || loading}
                                    >
                                      Reject
                                    </Button>
                                  ) : null}
                                  {row.kind === 'thesis_proposal' && row.status === 'confirmed' && row.proposalId ? (
                                    <Button
                                      size="sm"
                                      variant="default"
                                      onClick={() => void runProposalAction(row, 'apply')}
                                      disabled={busy || loading}
                                    >
                                      Apply
                                    </Button>
                                  ) : null}
                                </div>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                        {(section === activeSection ? filteredRows : rowsBySection[section]).length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={6} className="py-6 text-center text-sm text-muted-foreground">
                              No rows found for this subsection.
                            </TableCell>
                          </TableRow>
                        ) : null}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div className="flex min-h-0 flex-col gap-4 overflow-auto">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Framework Context</CardTitle>
            <CardDescription>What Tenn can use from memory surfaces.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {frameworkNotes.map((note) => (
              <p key={note} className="text-muted-foreground">
                {note}
              </p>
            ))}
            <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
              <Badge variant="outline">company: {asString(summary.company_memory_entry_count, '0')}</Badge>
              <Badge variant="outline">changes: {asString(summary.company_memory_change_count, '0')}</Badge>
              <Badge variant="outline">market: {asString(summary.market_memory_item_count, '0')}</Badge>
              <Badge variant="outline">thesis: {asString(summary.user_thesis_entry_count, '0')}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Strategy Context</CardTitle>
            <CardDescription>User thesis memory driving strategy reasoning.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">Confirmed thesis entries: {strategyEntries}</p>
            <p className="text-muted-foreground">Open/archived proposals: {strategyProposals}</p>
            <p className="text-muted-foreground">
              Proposal queue: {asString(summary.user_thesis_proposal_count, '0')} total | entries: {asString(summary.user_thesis_entry_count, '0')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Company Context</CardTitle>
            <CardDescription>Operational context Tenn can reference for this ticker.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">Docs: {asString(companyDumpSummary.doc_count, '0')}</p>
            <p className="text-muted-foreground">Financial periods: {asString(companyDumpSummary.financial_period_count, '0')}</p>
            <p className="text-muted-foreground">Risk notes: {asString(companyDumpSummary.risk_note_count, '0')}</p>
            <p className="text-muted-foreground">1Y return: {asString(companyDumpSummary.one_year_return_pct, '-')}</p>
            <p className="text-muted-foreground">Latest period: {asString(latestSnapshot.period_end, '-')}</p>
            {dumpErrors.length > 0 ? (
              <p className="text-xs text-destructive">Context warnings: {dumpErrors.map((item) => asString(item)).join(' | ')}</p>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
