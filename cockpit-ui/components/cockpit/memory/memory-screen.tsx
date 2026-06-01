'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useCockpitStore } from '@/lib/cockpit-store'

type MemorySection = 'company' | 'sector' | 'macro' | 'strategy' | 'truth' | 'session' | 'operational'
type MemoryKind =
  | 'company_entry'
  | 'sector_entry'
  | 'macro_entry'
  | 'thesis_entry'
  | 'thesis_proposal'
  | 'truth_document'
  | 'truth_financial_period'
  | 'truth_announcement'
  | 'truth_risk_note'
  | 'truth_extraction_failure'
  | 'truth_low_confidence_financial'
  | 'session_chat'
  | 'operational_job'
  | 'operational_feedback'
  | 'operational_alert'
type StrategyProposalType = 'create_thesis' | 'add_evidence' | 'invalidate'
type EditableLevel = 'company' | 'sector' | 'macro' | 'strategy'
type MemoryWriteIntent =
  | 'company-memory-add'
  | 'company-memory-expire'
  | 'sector-memory-add'
  | 'sector-memory-expire'
  | 'macro-memory-add'
  | 'macro-memory-expire'
  | 'thesis-proposal-create'
  | 'thesis-proposal-confirm'
  | 'thesis-proposal-reject'
  | 'thesis-proposal-apply'

interface MemoryScreenProps {
  apiKey: string
}

interface MemoryPayload {
  ticker?: string | null
  summary?: Record<string, unknown>
  memory_levels?: Record<string, unknown>[]
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
  docs?: Record<string, unknown>[]
  financials?: Record<string, unknown>[]
  announcement_context?: Record<string, unknown>[]
  latest_financial_snapshot?: Record<string, unknown> | null
  risk_notes?: Record<string, unknown>[]
  extraction_failures?: Record<string, unknown>[]
  low_confidence_financials?: Record<string, unknown>[]
  errors?: unknown[]
}

interface WorkspaceMemoryPayload {
  chat_sessions?: Record<string, unknown>[]
  jobs?: Record<string, unknown>[]
  feedback_flags?: Record<string, unknown>[]
  marketplace_alerts?: Record<string, unknown>[]
  errors?: string[]
}

interface MemoryRow {
  key: string
  section: MemorySection
  kind: MemoryKind
  scope: string
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
  truth: 'Financial Truth (Docs + Financial Rows)',
  session: 'Session Memory',
  operational: 'Operational State',
}

const BROWSER_SECTIONS: MemorySection[] = [
  'company',
  'sector',
  'macro',
  'strategy',
  'truth',
  'session',
  'operational',
]

const MEMORY_WRITE_CONFIRMATION = 'reviewed-memory-write'
const MEMORY_WRITE_INTENT_HEADER = 'X-Cockpit-Memory-Write-Intent'

function addIntentForLevel(level: EditableLevel): MemoryWriteIntent {
  if (level === 'company') return 'company-memory-add'
  if (level === 'sector') return 'sector-memory-add'
  if (level === 'macro') return 'macro-memory-add'
  return 'thesis-proposal-create'
}

function expireIntentForKind(kind: MemoryKind): MemoryWriteIntent | null {
  if (kind === 'company_entry') return 'company-memory-expire'
  if (kind === 'sector_entry') return 'sector-memory-expire'
  if (kind === 'macro_entry') return 'macro-memory-expire'
  return null
}

function addIntentForKind(kind: MemoryKind): MemoryWriteIntent | null {
  if (kind === 'company_entry') return 'company-memory-add'
  if (kind === 'sector_entry') return 'sector-memory-add'
  if (kind === 'macro_entry') return 'macro-memory-add'
  return null
}

const PROPOSAL_ACTION_INTENTS: Record<'confirm' | 'reject' | 'apply', MemoryWriteIntent> = {
  confirm: 'thesis-proposal-confirm',
  reject: 'thesis-proposal-reject',
  apply: 'thesis-proposal-apply',
}

function parseMemorySection(raw: string | null): MemorySection {
  const normalized = (raw ?? '').trim().toLowerCase()
  if (normalized === 'thesis') return 'strategy'
  return BROWSER_SECTIONS.includes(normalized as MemorySection)
    ? (normalized as MemorySection)
    : 'company'
}

interface BrowserGroup {
  key: string
  label: string
  rows: MemoryRow[]
}

interface MemoryLevelSummary {
  level: string
  label: string
  status: string
  scope: string
  rowCount: number | null
  entityCount: number | null
  source: string
  section: MemorySection | null
}

const DEFAULT_MEMORY_LEVELS: Array<Omit<MemoryLevelSummary, 'rowCount' | 'entityCount'>> = [
  {
    level: 'financial_truth',
    label: 'Financial Truth',
    status: 'load_ticker',
    scope: 'ticker',
    source: 'postgres',
    section: 'truth',
  },
  {
    level: 'company',
    label: 'Company Memory',
    status: 'unknown',
    scope: 'all_tickers',
    source: 'company_memory.sqlite',
    section: 'company',
  },
  {
    level: 'sector',
    label: 'Sector Memory',
    status: 'unknown',
    scope: 'all_sectors',
    source: 'market_memory.sqlite',
    section: 'sector',
  },
  {
    level: 'macro',
    label: 'Macro Memory',
    status: 'unknown',
    scope: 'macro_topics',
    source: 'market_memory.sqlite',
    section: 'macro',
  },
  {
    level: 'strategy',
    label: 'Strategy / Thesis Memory',
    status: 'unknown',
    scope: 'all_tickers',
    source: 'user_thesis_memory.sqlite',
    section: 'strategy',
  },
  {
    level: 'session',
    label: 'Session Memory',
    status: 'outside_index',
    scope: 'conversation_sessions',
    source: 'openviking + cockpit recency',
    section: 'session',
  },
  {
    level: 'operational',
    label: 'Operational State',
    status: 'outside_reasoning_memory',
    scope: 'jobs_alerts_feedback_workspace',
    source: 'cockpit state + reports',
    section: 'operational',
  },
]

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

function previewStatement(text: string): string {
  const normalized = text.replace(/\s+/g, ' ').trim()
  if (normalized.length <= 120) return normalized
  return `${normalized.slice(0, 117)}...`
}

function displayMoney(value: unknown): string | null {
  const parsed = asNumber(value)
  if (parsed == null) return null
  if (Math.abs(parsed) >= 1_000_000_000) return `${(parsed / 1_000_000_000).toFixed(2)}b`
  if (Math.abs(parsed) >= 1_000_000) return `${(parsed / 1_000_000).toFixed(2)}m`
  if (Math.abs(parsed) >= 1_000) return `${(parsed / 1_000).toFixed(2)}k`
  return parsed.toFixed(2)
}

function displayCount(value: number | null): string {
  if (value == null) return '-'
  return String(value)
}

function displayLevelStatus(value: string): string {
  const normalized = value.trim().toLowerCase()
  if (normalized === 'outside_reasoning_memory') return 'ops'
  if (normalized === 'outside_index') return 'external'
  if (normalized === 'load_ticker') return 'ticker'
  if (normalized === 'ticker_scoped') return 'ticker'
  return value || 'unknown'
}

function sumCompanyDumpRows(companyDump: CompanyDumpPayload | null): number | null {
  if (!companyDump) return null
  const summary = asObject(companyDump.summary)
  const keys = [
    'doc_count',
    'financial_period_count',
    'announcement_context_count',
    'risk_note_count',
    'extraction_failure_count',
    'low_confidence_financial_count',
  ]
  return keys.reduce((total, key) => total + Math.trunc(asNumber(summary[key]) ?? 0), 0)
}

function buildMemoryLevelSummaries(
  payload: MemoryPayload | null,
  companyDump: CompanyDumpPayload | null,
  visibleCounts: Partial<Record<MemorySection, number>> = {},
): MemoryLevelSummary[] {
  const backendLevels = new Map<string, Record<string, unknown>>()
  for (const level of asArray(payload?.memory_levels)) {
    const key = asString(level.level).trim()
    if (key) {
      backendLevels.set(key, level)
    }
  }

  const summary = asObject(payload?.summary)
  const companyMemory = asObject(payload?.company_memory)
  const marketMemory = asObject(payload?.market_memory)
  const thesisMemory = asObject(payload?.user_thesis_memory)
  const truthRows = sumCompanyDumpRows(companyDump)
  const sectorRows =
    asNumber(marketMemory.sector_items_total) ?? asArray(marketMemory.sector_items).length
  const macroRows =
    asNumber(marketMemory.macro_items_total) ?? asArray(marketMemory.macro_items).length
  const strategyRows =
    (asNumber(thesisMemory.entries_total) ??
      Math.trunc(asNumber(summary.user_thesis_entry_count) ?? 0)) +
    (asNumber(thesisMemory.proposals_total) ??
      Math.trunc(asNumber(summary.user_thesis_proposal_count) ?? 0))

  const fallbackCounts: Record<string, { rowCount: number | null; entityCount: number | null }> = {
    financial_truth: {
      rowCount: truthRows,
      entityCount: companyDump ? 1 : null,
    },
    company: {
      rowCount:
        asNumber(companyMemory.entries_total) ??
        Math.trunc(asNumber(summary.company_memory_entry_count) ?? 0),
      entityCount: asNumber(summary.company_memory_ticker_count),
    },
    sector: {
      rowCount: Math.trunc(sectorRows),
      entityCount: asNumber(summary.market_memory_sector_count),
    },
    macro: {
      rowCount: Math.trunc(macroRows),
      entityCount: asNumber(summary.market_memory_macro_topic_count),
    },
    strategy: {
      rowCount: strategyRows,
      entityCount: asNumber(summary.user_thesis_ticker_count),
    },
    session: {
      rowCount: visibleCounts.session ?? null,
      entityCount: visibleCounts.session ?? null,
    },
    operational: {
      rowCount: visibleCounts.operational ?? null,
      entityCount: visibleCounts.operational ?? null,
    },
  }

  return DEFAULT_MEMORY_LEVELS.map((base) => {
    const backend = backendLevels.get(base.level) ?? {}
    const fallback = fallbackCounts[base.level] ?? { rowCount: null, entityCount: null }
    const rowCount = asNumber(backend.row_count) ?? fallback.rowCount
    const entityCount = asNumber(backend.entity_count) ?? fallback.entityCount
    return {
      ...base,
      label: asString(backend.label, base.label),
      status:
        base.level === 'financial_truth' && companyDump
          ? 'loaded'
          : asString(backend.status, base.status),
      scope:
        base.level === 'financial_truth' && companyDump
          ? asString(companyDump.ticker, base.scope)
          : asString(backend.scope, base.scope),
      rowCount,
      entityCount,
      source: asString(backend.source, base.source),
    }
  })
}

function buildFinancialPeriodStatement(item: Record<string, unknown>): string {
  const periodType = asString(item.period_type, 'period').toUpperCase()
  const periodEnd = asString(item.period_end, '-')
  const parts: string[] = [`${periodType} ${periodEnd}`]
  const revenue = displayMoney(item.revenue)
  const ebit = displayMoney(item.ebit)
  const np = displayMoney(item.np_attributable)
  const operatingCf = displayMoney(item.operating_cf)
  const netDebt = displayMoney(item.net_debt)
  if (revenue != null) parts.push(`Revenue ${revenue}`)
  if (ebit != null) parts.push(`EBIT ${ebit}`)
  if (np != null) parts.push(`NPAT ${np}`)
  if (operatingCf != null) parts.push(`OpCF ${operatingCf}`)
  if (netDebt != null) parts.push(`Net debt ${netDebt}`)
  return parts.join(' | ')
}

function compactParts(parts: Array<string | null | undefined>): string {
  return parts
    .map((part) => (part ?? '').trim())
    .filter(Boolean)
    .join(' | ')
}

function buildWorkspaceRows(payload: WorkspaceMemoryPayload | null): MemoryRow[] {
  const rows: MemoryRow[] = []

  for (const item of asArray(payload?.chat_sessions)) {
    const sessionId = asString(item.session_id)
    const title = asString(item.title, sessionId || 'Untitled chat')
    const lastMessage = asString(item.last_message)
    const messageCount = Math.trunc(asNumber(item.message_count) ?? 0)
    rows.push({
      key: `session-chat:${sessionId || Math.random().toString(36).slice(2)}`,
      section: 'session',
      kind: 'session_chat',
      scope: 'chat_sessions',
      entryId: null,
      proposalId: sessionId || null,
      type: 'chat_session',
      statement: compactParts([title, lastMessage]),
      status: `${messageCount} messages`,
      seenAt: formatTimestamp(item.updated_at),
      signal: null,
      confidence: null,
      editable: false,
    })
  }

  for (const item of asArray(payload?.jobs)) {
    const jobId = asString(item.job_id)
    const title = asString(item.title, asString(item.job_type, 'job'))
    rows.push({
      key: `operational-job:${jobId || Math.random().toString(36).slice(2)}`,
      section: 'operational',
      kind: 'operational_job',
      scope: 'jobs',
      entryId: null,
      proposalId: jobId || null,
      type: compactParts([asString(item.job_family), asString(item.job_type)]) || 'job',
      statement: compactParts([
        title,
        asString(item.phase),
        asString(item.summary),
        asString(item.current_item_label),
      ]),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.updated_at ?? item.completed_at ?? item.started_at ?? item.queued_at),
      signal: asString(item.ticker) || null,
      confidence: null,
      editable: false,
    })
  }

  for (const item of asArray(payload?.feedback_flags)) {
    const reportId = asString(item.report_id)
    rows.push({
      key: `operational-feedback:${reportId || Math.random().toString(36).slice(2)}`,
      section: 'operational',
      kind: 'operational_feedback',
      scope: 'feedback_flags',
      entryId: null,
      proposalId: reportId || null,
      type: compactParts([asString(item.capture_kind), asString(item.feedback_type)]) || 'feedback',
      statement: compactParts([asString(item.note), asString(item.flagged_response_excerpt)]),
      status: asString(item.resolution_status, '-'),
      seenAt: formatTimestamp(item.saved_at),
      signal: asString(item.ticker) || null,
      confidence: null,
      editable: false,
    })
  }

  for (const item of asArray(payload?.marketplace_alerts)) {
    const alertId = asString(item.alert_id)
    rows.push({
      key: `operational-alert:${alertId || Math.random().toString(36).slice(2)}`,
      section: 'operational',
      kind: 'operational_alert',
      scope: 'marketplace_alerts',
      entryId: null,
      proposalId: alertId || null,
      type: compactParts([asString(item.decision_band), 'marketplace_alert']) || 'marketplace_alert',
      statement: compactParts([
        asString(item.match_title),
        asString(item.trigger_reason),
        asString(item.price),
        asString(item.location),
      ]),
      status: asString(item.status, '-'),
      seenAt: formatTimestamp(item.updated_at ?? item.created_at),
      signal: asString(item.mission_name) || null,
      confidence: null,
      editable: false,
    })
  }

  return rows
}

function groupRowsForBrowser(rows: MemoryRow[]): BrowserGroup[] {
  const grouped = new Map<string, MemoryRow[]>()
  for (const row of rows) {
    const key = row.scope.trim() || 'global'
    const bucket = grouped.get(key)
    if (bucket) {
      bucket.push(row)
    } else {
      grouped.set(key, [row])
    }
  }

  return Array.from(grouped.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, groupRows]) => ({
      key,
      label: key,
      rows: groupRows.sort((a, b) => {
        const typeDiff = a.type.localeCompare(b.type)
        if (typeDiff !== 0) return typeDiff
        const leftId = a.entryId != null ? a.entryId : Number.MAX_SAFE_INTEGER
        const rightId = b.entryId != null ? b.entryId : Number.MAX_SAFE_INTEGER
        if (leftId !== rightId) return leftId - rightId
        return (a.proposalId ?? '').localeCompare(b.proposalId ?? '')
      }),
    }))
}

function buildRows(
  payload: MemoryPayload,
  companyDump: CompanyDumpPayload | null,
  workspacePayload: WorkspaceMemoryPayload | null,
): MemoryRow[] {
  const rows: MemoryRow[] = []
  const companyMemory = asObject(payload.company_memory)
  const marketMemory = asObject(payload.market_memory)
  const thesisMemory = asObject(payload.user_thesis_memory)
  const fallbackTicker = asString(payload.ticker, 'GLOBAL')

  for (const item of asArray(companyMemory.entries)) {
    const entryId = asInt(item.entry_id)
    const ticker = asString(item.company_id, fallbackTicker)
    rows.push({
      key: `company:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'company',
      kind: 'company_entry',
      scope: ticker || 'GLOBAL',
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
    const sector = asString(item.sector, asString(marketMemory.sector, 'sector'))
    rows.push({
      key: `sector:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'sector',
      kind: 'sector_entry',
      scope: sector || 'sector',
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
    const macroTopic = asString(item.macro_topic, 'macro')
    rows.push({
      key: `macro:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'macro',
      kind: 'macro_entry',
      scope: macroTopic || 'macro',
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
    const ticker = asString(item.ticker, fallbackTicker)
    rows.push({
      key: `thesis-entry:${entryId ?? Math.random().toString(36).slice(2)}`,
      section: 'strategy',
      kind: 'thesis_entry',
      scope: ticker || 'GLOBAL',
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
    const ticker = asString(item.ticker, fallbackTicker)
    rows.push({
      key: `thesis-proposal:${proposalId || Math.random().toString(36).slice(2)}`,
      section: 'strategy',
      kind: 'thesis_proposal',
      scope: ticker || 'GLOBAL',
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

  if (companyDump) {
    const ticker = asString(companyDump.ticker, fallbackTicker || 'GLOBAL')

    for (const item of asArray(companyDump.docs)) {
      const documentId = asString(item.document_id)
      const docClass = asString(item.doc_class, 'document')
      const docSubtype = asString(item.doc_subtype)
      const label = docSubtype ? `${docClass}/${docSubtype}` : docClass
      rows.push({
        key: `truth-document:${documentId || Math.random().toString(36).slice(2)}`,
        section: 'truth',
        kind: 'truth_document',
        scope: 'documents',
        entryId: null,
        proposalId: documentId || null,
        type: label,
        statement: asString(item.title, '(untitled document)'),
        status: 'available',
        seenAt: formatTimestamp(item.published_at),
        signal: ticker || null,
        confidence: null,
        editable: false,
      })
    }

    for (const item of asArray(companyDump.financials)) {
      const periodEnd = asString(item.period_end)
      const periodType = asString(item.period_type)
      rows.push({
        key: `truth-financial:${periodType}:${periodEnd || Math.random().toString(36).slice(2)}`,
        section: 'truth',
        kind: 'truth_financial_period',
        scope: 'financial_periods',
        entryId: null,
        proposalId: [periodType, periodEnd].filter(Boolean).join(':') || null,
        type: 'financial_period',
        statement: buildFinancialPeriodStatement(item),
        status: 'available',
        seenAt: formatTimestamp(item.period_end),
        signal: ticker || null,
        confidence: null,
        editable: false,
      })
    }

    for (const item of asArray(companyDump.announcement_context)) {
      const documentId = asString(item.document_id)
      const excerpt = asString(item.excerpt)
      const title = asString(item.title, '(untitled announcement)')
      rows.push({
        key: `truth-announcement:${documentId || Math.random().toString(36).slice(2)}`,
        section: 'truth',
        kind: 'truth_announcement',
        scope: 'announcement_context',
        entryId: null,
        proposalId: documentId || null,
        type: 'announcement_context',
        statement: excerpt || title,
        status: 'available',
        seenAt: formatTimestamp(item.published_at ?? item.updated_at),
        signal: ticker || null,
        confidence: null,
        editable: false,
      })
    }

    for (const item of asArray(companyDump.risk_notes)) {
      const documentId = asString(item.document_id)
      const summary = asString(item.risk_summary)
      const guidance = asString(item.guidance_summary)
      const bullets = asList(item.risk_bullets)
        .map((value) => asString(value).trim())
        .filter(Boolean)
        .slice(0, 2)
      rows.push({
        key: `truth-risk:${documentId || Math.random().toString(36).slice(2)}`,
        section: 'truth',
        kind: 'truth_risk_note',
        scope: 'risk_notes',
        entryId: null,
        proposalId: documentId || null,
        type: 'risk_note',
        statement: [summary, guidance, ...bullets].filter(Boolean).join(' | ') || '(no risk summary)',
        status: 'available',
        seenAt: formatTimestamp(item.published_at ?? item.updated_at),
        signal: ticker || null,
        confidence: null,
        editable: false,
      })
    }

    for (const item of asArray(companyDump.extraction_failures)) {
      const runId = asString(item.run_id)
      const title = asString(item.title)
      const error = asString(item.error, '(unknown extraction error)')
      rows.push({
        key: `truth-extraction-failure:${runId || Math.random().toString(36).slice(2)}`,
        section: 'truth',
        kind: 'truth_extraction_failure',
        scope: 'extraction_failures',
        entryId: null,
        proposalId: runId || null,
        type: 'extraction_failure',
        statement: title ? `${title}: ${error}` : error,
        status: asString(item.status, 'failed'),
        seenAt: formatTimestamp(item.created_at),
        signal: ticker || null,
        confidence: null,
        editable: false,
      })
    }

    for (const item of asArray(companyDump.low_confidence_financials)) {
      const periodEnd = asString(item.period_end)
      const periodType = asString(item.period_type)
      rows.push({
        key: `truth-low-confidence:${periodType}:${periodEnd || Math.random().toString(36).slice(2)}`,
        section: 'truth',
        kind: 'truth_low_confidence_financial',
        scope: 'low_confidence_financials',
        entryId: null,
        proposalId: [periodType, periodEnd].filter(Boolean).join(':') || null,
        type: 'low_confidence_financial',
        statement: buildFinancialPeriodStatement(item),
        status: 'low_confidence',
        seenAt: formatTimestamp(item.period_end),
        signal: ticker || null,
        confidence: asNumber(item.confidence),
        editable: false,
      })
    }
  }

  return [...rows, ...buildWorkspaceRows(workspacePayload)]
}

export function MemoryScreen({ apiKey }: MemoryScreenProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { activeTicker, setActiveTicker } = useCockpitStore()
  const [tickerInput, setTickerInput] = useState(activeTicker)
  const [activeSection, setActiveSection] = useState<MemorySection>(() => parseMemorySection(searchParams.get('tab')))
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Loading persistent memory index...')
  const [memoryPayload, setMemoryPayload] = useState<MemoryPayload | null>(null)
  const [companyDump, setCompanyDump] = useState<CompanyDumpPayload | null>(null)
  const [workspacePayload, setWorkspacePayload] = useState<WorkspaceMemoryPayload | null>(null)
  const [rows, setRows] = useState<MemoryRow[]>([])
  const [level, setLevel] = useState<EditableLevel>('company')
  const [entryType, setEntryType] = useState('')
  const [statement, setStatement] = useState('')
  const [strategySignal, setStrategySignal] = useState('')
  const [strategyProposalType, setStrategyProposalType] = useState<StrategyProposalType>('create_thesis')
  const [editTarget, setEditTarget] = useState<MemoryRow | null>(null)
  const [selectedRowKey, setSelectedRowKey] = useState<string | null>(null)
  const initialLoadDoneRef = useRef(false)

  useEffect(() => {
    if (!tickerInput && activeTicker) {
      setTickerInput(activeTicker)
    }
  }, [activeTicker, tickerInput])

  const query = search.trim().toLowerCase()

  const updateActiveSection = useCallback((value: string) => {
    const nextSection = parseMemorySection(value)
    setActiveSection(nextSection)

    const params = new URLSearchParams(searchParams.toString())
    if (nextSection === 'company') {
      params.delete('tab')
    } else {
      params.set('tab', nextSection)
    }
    const queryString = params.toString()
    window.history.replaceState(null, '', queryString ? `${pathname}?${queryString}` : pathname)
  }, [pathname, searchParams])

  useEffect(() => {
    const nextSection = parseMemorySection(searchParams.get('tab'))
    setActiveSection((current) => (current === nextSection ? current : nextSection))
  }, [searchParams])

  const rowsBySection = useMemo(() => {
    const grouped: Record<MemorySection, MemoryRow[]> = {
      company: [],
      sector: [],
      macro: [],
      strategy: [],
      truth: [],
      session: [],
      operational: [],
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
        row.scope,
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

  useEffect(() => {
    if (filteredRows.length === 0) {
      if (selectedRowKey !== null) {
        setSelectedRowKey(null)
      }
      return
    }
    if (selectedRowKey && filteredRows.some((row) => row.key === selectedRowKey)) {
      return
    }
    setSelectedRowKey(filteredRows[0]?.key ?? null)
  }, [filteredRows, selectedRowKey])

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

  const loadWorkspaceContext = useCallback(async (): Promise<WorkspaceMemoryPayload> => {
    const fetchItems = async (path: string): Promise<Record<string, unknown>[]> => {
      const response = await fetch(path, {
        cache: 'no-store',
        headers,
      })
      if (!response.ok) {
        const raw = await response.json().catch(() => null)
        throw new Error(summarizeErrorPayload(raw) || `${path} failed (${response.status})`)
      }
      const payload = asObject(await response.json())
      return asArray(payload.items)
    }

    const requests = await Promise.allSettled([
      fetchItems('/api/cockpit/chat/sessions?limit=50'),
      fetchItems('/api/ops/jobs?limit=50'),
      fetchItems('/api/cockpit/feedback/flags?limit=25&status=open'),
      fetchItems('/api/cockpit/marketplace/alerts?limit=50'),
    ])
    const errors: string[] = []
    const valueAt = (index: number): Record<string, unknown>[] => {
      const result = requests[index]
      if (!result) return []
      if (result.status === 'fulfilled') return result.value
      errors.push(result.reason instanceof Error ? result.reason.message : 'Workspace context request failed.')
      return []
    }

    return {
      chat_sessions: valueAt(0),
      jobs: valueAt(1),
      feedback_flags: valueAt(2),
      marketplace_alerts: valueAt(3),
      errors,
    }
  }, [headers])

  const loadMemory = useCallback(async (explicitTicker?: string) => {
    const ticker = (explicitTicker ?? tickerInput).trim().toUpperCase()
    const scopedLoad = Boolean(ticker)
    setLoading(true)
    setStatus(scopedLoad ? `Loading memory for ${ticker}...` : 'Loading full persistent memory index...')
    if (scopedLoad) {
      setActiveTicker(ticker)
    }

    try {
      const memoryPath = scopedLoad
        ? `/api/cockpit/memory?ticker=${encodeURIComponent(ticker)}&company_memory_entries_limit=500&company_memory_change_limit=300&market_memory_limit=300&user_thesis_entries_limit=250&user_thesis_proposals_limit=250`
        : '/api/cockpit/memory/index?company_memory_entries_limit=5000&company_memory_change_limit=2000&market_sector_limit=5000&market_macro_limit=5000&user_thesis_entries_limit=5000&user_thesis_proposals_limit=5000'
      const memoryResponse = await fetch(memoryPath, {
        cache: 'no-store',
        headers,
      })

      if (!memoryResponse.ok) {
        const raw = await memoryResponse.json().catch(() => null)
        throw new Error(summarizeErrorPayload(raw) || `Memory load failed (${memoryResponse.status})`)
      }

      const memoryData = (await memoryResponse.json()) as MemoryPayload
      setMemoryPayload(memoryData)
      let dumpData: CompanyDumpPayload | null = null
      const workspaceData = await loadWorkspaceContext()
      setWorkspacePayload(workspaceData)

      if (scopedLoad) {
        const dumpResponse = await fetch(
          `/api/cockpit/memory/company-dump?ticker=${encodeURIComponent(ticker)}&docs_limit=40&financials_limit=24&announcements_limit=40&risk_notes_limit=20`,
          {
            cache: 'no-store',
            headers,
          },
        )

        if (dumpResponse.ok) {
          dumpData = (await dumpResponse.json()) as CompanyDumpPayload
          setCompanyDump(dumpData)
        } else {
          setCompanyDump(null)
        }
      } else {
        setCompanyDump(null)
      }
      setRows(buildRows(memoryData, dumpData, workspaceData))

      const loadErrors = asList(memoryData.errors)
      const workspaceErrors = workspaceData.errors ?? []
      if (loadErrors.length > 0 || workspaceErrors.length > 0) {
        setStatus(scopedLoad ? `Loaded with warnings for ${ticker}.` : 'Loaded full persistent memory index with warnings.')
      } else {
        setStatus(scopedLoad ? `Loaded memory for ${ticker}.` : 'Loaded full persistent memory index.')
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Failed to load memory.')
      setMemoryPayload(null)
      setCompanyDump(null)
      setWorkspacePayload(null)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [headers, loadWorkspaceContext, setActiveTicker, tickerInput])

  useEffect(() => {
    if (initialLoadDoneRef.current) return
    initialLoadDoneRef.current = true
    void loadMemory('')
  }, [loadMemory])

  const submitMutation = useCallback(
    async (path: string, body: Record<string, unknown>, intent: MemoryWriteIntent) => {
      const response = await fetch(path, {
        method: 'POST',
        headers: {
          ...headers,
          [MEMORY_WRITE_INTENT_HEADER]: intent,
        },
        body: JSON.stringify({
          ...body,
          intent,
          confirmation: MEMORY_WRITE_CONFIRMATION,
        }),
      })
      if (!response.ok) {
        const raw = await response.json().catch(() => null)
        throw new Error(summarizeErrorPayload(raw) || `Mutation failed (${response.status})`)
      }
      return response.json().catch(() => ({}))
    },
    [headers],
  )

  const confirmMemoryWrite = useCallback((action: string, detail: string) => {
    const confirmed = window.confirm(
      `Confirm ${action}\n\n${detail}\n\nThis writes durable memory through the backend-owned Memory Workbench path.`,
    )
    if (!confirmed) {
      setStatus('Memory write cancelled.')
    }
    return confirmed
  }, [])

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

    const intent = addIntentForLevel(level)
    if (!confirmMemoryWrite('add memory entry', `${SECTION_LABELS[level === 'strategy' ? 'strategy' : level]} item for ${ticker}.`)) {
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
        }, intent)
      } else if (level === 'sector') {
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'sector',
          ticker,
          type: entryType.trim() || 'sector_trend',
          statement: nextStatement,
          note: 'web-memory-tab',
        }, intent)
      } else if (level === 'macro') {
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'macro',
          ticker,
          macro_topic: 'macro',
          type: entryType.trim() || 'macro_theme',
          statement: nextStatement,
          note: 'web-memory-tab',
        }, intent)
      } else {
        await submitMutation('/api/cockpit/memory/thesis/proposals', {
          ticker,
          proposal_type: strategyProposalType,
          statement: nextStatement,
          signal: strategySignal.trim() || null,
          is_supporting: true,
          note: 'web-memory-tab',
        }, intent)
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
  }, [confirmMemoryWrite, entryType, level, loadMemory, statement, strategyProposalType, strategySignal, submitMutation, tickerInput])

  const startEdit = useCallback((row: MemoryRow) => {
    if (!row.editable) return
    setEditTarget(row)
    if (row.section === 'company' && row.scope) {
      setTickerInput(row.scope.toUpperCase())
    }
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
    const ticker = (tickerInput.trim() || editTarget.scope || '').toUpperCase()
    const nextStatement = statement.trim()
    if (!ticker || !nextStatement) {
      setStatus('Ticker and statement are required.')
      return
    }
    if (!editTarget.entryId) {
      setStatus('Selected row has no entry id.')
      return
    }
    const expireIntent = expireIntentForKind(editTarget.kind)
    const addIntent = addIntentForKind(editTarget.kind)
    if (!expireIntent || !addIntent) {
      setStatus('Only company/sector/macro rows are directly editable.')
      return
    }
    if (!confirmMemoryWrite('save memory edit', `Expire row ${editTarget.entryId} and add its replacement for ${ticker}.`)) {
      return
    }

    setBusy(true)
    try {
      if (editTarget.kind === 'company_entry') {
        await submitMutation('/api/cockpit/memory/company/expire', {
          ticker,
          entry_id: editTarget.entryId,
          note: 'superseded-via-web-memory-tab',
        }, expireIntent)
        await submitMutation('/api/cockpit/memory/company/add', {
          ticker,
          type: entryType.trim() || editTarget.type || 'observed_fact',
          statement: nextStatement,
          note: 'edited-via-web-memory-tab',
        }, addIntent)
      } else if (editTarget.kind === 'sector_entry') {
        await submitMutation('/api/cockpit/memory/market/expire', {
          scope: 'sector',
          entry_id: editTarget.entryId,
          note: 'superseded-via-web-memory-tab',
        }, expireIntent)
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'sector',
          ticker,
          type: entryType.trim() || editTarget.type || 'sector_trend',
          statement: nextStatement,
          note: 'edited-via-web-memory-tab',
        }, addIntent)
      } else if (editTarget.kind === 'macro_entry') {
        await submitMutation('/api/cockpit/memory/market/expire', {
          scope: 'macro',
          entry_id: editTarget.entryId,
          note: 'superseded-via-web-memory-tab',
        }, expireIntent)
        await submitMutation('/api/cockpit/memory/market/add', {
          scope: 'macro',
          ticker,
          macro_topic: 'macro',
          type: entryType.trim() || editTarget.type || 'macro_theme',
          statement: nextStatement,
          note: 'edited-via-web-memory-tab',
        }, addIntent)
      }

      setStatus(`Updated row ${editTarget.entryId} by expiring + replacing it.`)
      resetEditor()
      await loadMemory()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Edit failed.')
    } finally {
      setBusy(false)
    }
  }, [confirmMemoryWrite, editTarget, entryType, loadMemory, resetEditor, statement, submitMutation, tickerInput])

  const expireRow = useCallback(
    async (row: MemoryRow) => {
      const ticker = (tickerInput.trim() || row.scope || '').toUpperCase()
      if (!row.entryId) {
        setStatus('Row has no entry id.')
        return
      }
      const intent = expireIntentForKind(row.kind)
      if (!intent) return
      if (!confirmMemoryWrite('expire memory row', `Expire row ${row.entryId} from ${row.scope || 'memory'}.`)) {
        return
      }

      setBusy(true)
      try {
        if (row.kind === 'company_entry') {
          await submitMutation('/api/cockpit/memory/company/expire', {
            ticker,
            entry_id: row.entryId,
            note: 'expired-via-web-memory-tab',
          }, intent)
        } else if (row.kind === 'sector_entry') {
          await submitMutation('/api/cockpit/memory/market/expire', {
            scope: 'sector',
            entry_id: row.entryId,
            note: 'expired-via-web-memory-tab',
          }, intent)
        } else if (row.kind === 'macro_entry') {
          await submitMutation('/api/cockpit/memory/market/expire', {
            scope: 'macro',
            entry_id: row.entryId,
            note: 'expired-via-web-memory-tab',
          }, intent)
        }
        setStatus(`Expired row ${row.entryId}.`)
        await loadMemory()
      } catch (error) {
        setStatus(error instanceof Error ? error.message : 'Expire failed.')
      } finally {
        setBusy(false)
      }
    },
    [confirmMemoryWrite, loadMemory, submitMutation, tickerInput],
  )

  const runProposalAction = useCallback(
    async (row: MemoryRow, action: 'confirm' | 'reject' | 'apply') => {
      if (!row.proposalId) {
        setStatus('Proposal id missing.')
        return
      }
      const intent = PROPOSAL_ACTION_INTENTS[action]
      if (!confirmMemoryWrite(`${action} thesis proposal`, `Proposal ${row.proposalId}.`)) {
        return
      }

      setBusy(true)
      try {
        if (action === 'confirm') {
          await submitMutation(`/api/cockpit/memory/thesis/proposals/${encodeURIComponent(row.proposalId)}/confirm`, {
            note: 'confirmed-via-web-memory-tab',
          }, intent)
        } else if (action === 'reject') {
          await submitMutation(`/api/cockpit/memory/thesis/proposals/${encodeURIComponent(row.proposalId)}/reject`, {
            note: 'rejected-via-web-memory-tab',
          }, intent)
        } else {
          await submitMutation(`/api/cockpit/memory/thesis/proposals/${encodeURIComponent(row.proposalId)}/apply`, {
            note: 'applied-via-web-memory-tab',
          }, intent)
        }
        setStatus(`Proposal ${row.proposalId} ${action}ed.`)
        await loadMemory()
      } catch (error) {
        setStatus(error instanceof Error ? error.message : 'Proposal action failed.')
      } finally {
        setBusy(false)
      }
    },
    [confirmMemoryWrite, loadMemory, submitMutation],
  )

  const frameworkNotes = [
    'Canonical financial truth remains backend-authoritative.',
    'Financial Truth tab is read-only and ticker-scoped (documents + structured rows).',
    'Company memory captures ticker-scoped qualitative signals.',
    'Market memory captures sector + macro qualitative signals.',
    'Strategy memory is user-thesis (proposal -> confirm -> apply).',
    'Session memory shows recent chat-session continuity.',
    'Operational state shows jobs, alerts, and feedback records.',
  ]

  const strategyEntries = rowsBySection.strategy.filter((row) => row.kind === 'thesis_entry').length
  const strategyProposals = rowsBySection.strategy.filter((row) => row.kind === 'thesis_proposal').length

  const memoryErrors = asList(memoryPayload?.errors)
  const workspaceErrors = workspacePayload?.errors ?? []
  const dumpErrors = asList(companyDump?.errors)
  const memoryLevels = useMemo(
    () =>
      buildMemoryLevelSummaries(memoryPayload, companyDump, {
        session: rowsBySection.session.length,
        operational: rowsBySection.operational.length,
      }),
    [companyDump, memoryPayload, rowsBySection.operational.length, rowsBySection.session.length],
  )

  return (
    <div className="grid h-full min-h-0 gap-4 p-4 lg:grid-cols-[2.1fr_1fr]">
      <div className="flex min-h-0 flex-col gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Memory Workbench</CardTitle>
            <CardDescription>
              Browse, search, edit, and add memory across persistent, financial-truth, session, and operational levels.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <Input
                value={tickerInput}
                placeholder="Ticker filter (optional, e.g. BHP)"
                onChange={(event) => setTickerInput(event.target.value.toUpperCase())}
              />
              <Button onClick={() => void loadMemory()} disabled={loading || busy}>
                {loading ? 'Loading…' : tickerInput.trim() ? 'Load Ticker' : 'Load All'}
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
                <Badge variant="outline">truth {rowsBySection.truth.length}</Badge>
                <Badge variant="outline">session {rowsBySection.session.length}</Badge>
                <Badge variant="outline">ops {rowsBySection.operational.length}</Badge>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">{status}</p>
            <p className="text-xs text-muted-foreground/80">
              Financial Truth context is ticker-scoped. Load a ticker to browse docs/financial rows beside persistent memory.
            </p>
            {memoryErrors.length > 0 ? (
              <p className="text-xs text-destructive">Memory warnings: {memoryErrors.map((item) => asString(item)).join(' | ')}</p>
            ) : null}
            {workspaceErrors.length > 0 ? (
              <p className="text-xs text-destructive">Workspace warnings: {workspaceErrors.join(' | ')}</p>
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
            <CardDescription>File-browser style memory navigation by level, then type, then entry.</CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            <Tabs value={activeSection} onValueChange={updateActiveSection} className="flex min-h-0 flex-1 flex-col gap-3">
              <TabsList className="grid h-auto w-full grid-cols-2 md:grid-cols-4 xl:grid-cols-7">
                <TabsTrigger value="company">Company</TabsTrigger>
                <TabsTrigger value="sector">Sector</TabsTrigger>
                <TabsTrigger value="macro">Macro</TabsTrigger>
                <TabsTrigger value="strategy">Strategy</TabsTrigger>
                <TabsTrigger value="truth">Financial Truth</TabsTrigger>
                <TabsTrigger value="session">Session</TabsTrigger>
                <TabsTrigger value="operational">Operational</TabsTrigger>
              </TabsList>

              {BROWSER_SECTIONS.map((section) => (
                <TabsContent key={section} value={section} className="m-0 flex min-h-0 flex-1 flex-col">
                  {(() => {
                    const sectionRows = section === activeSection ? filteredRows : rowsBySection[section]
                    const groupedRows = groupRowsForBrowser(sectionRows)
                    const selectedRow = sectionRows.find((row) => row.key === selectedRowKey) ?? sectionRows[0] ?? null
                    const selectedRowId =
                      selectedRow?.entryId != null ? String(selectedRow.entryId) : selectedRow?.proposalId ?? '-'
                    const selectedStatus = selectedRow?.status?.toLowerCase() ?? ''

                    return (
                      <>
                        <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                          <span>{SECTION_LABELS[section]}</span>
                          <span>{section === activeSection ? `${sectionRows.length} visible` : `${rowsBySection[section].length} total`}</span>
                        </div>
                        <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[1.35fr_1fr]">
                          <div className="min-h-0 overflow-auto rounded-md border border-border/70 p-2">
                            {groupedRows.length > 0 ? (
                              groupedRows.map((group) => (
                                <details key={group.key} open className="mb-2 rounded-md border border-border/70 bg-background/50 last:mb-0">
                                  <summary className="flex cursor-pointer items-center justify-between gap-2 px-2 py-1.5 text-xs text-muted-foreground">
                                    <span className="font-mono">/{group.label}</span>
                                    <Badge variant="outline">{group.rows.length}</Badge>
                                  </summary>
                                  <div className="space-y-1 px-2 pb-2 pt-1">
                                    {group.rows.map((row) => {
                                      const rowId = row.entryId != null ? String(row.entryId) : row.proposalId ?? '-'
                                      const rowStatus = row.status.toLowerCase()
                                      const isSelected = selectedRow?.key === row.key
                                      return (
                                        <button
                                          key={row.key}
                                          type="button"
                                          onClick={() => {
                                            updateActiveSection(section)
                                            setSelectedRowKey(row.key)
                                          }}
                                          className={`w-full rounded-md border p-2 text-left transition-colors ${
                                            isSelected
                                              ? 'border-primary/60 bg-primary/10'
                                              : 'border-border/70 bg-background/70 hover:border-border hover:bg-muted/40'
                                          }`}
                                        >
                                          <div className="flex items-center justify-between gap-2">
                                            <span className="font-mono text-[11px] text-foreground/90">{rowId}</span>
                                            <Badge variant={rowStatus === 'active' || rowStatus === 'applied' ? 'secondary' : 'outline'}>
                                              {row.status}
                                            </Badge>
                                          </div>
                                          <p className="mt-1 text-[10px] text-muted-foreground/70">{row.type}</p>
                                          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{previewStatement(row.statement)}</p>
                                          <p className="mt-1 text-[10px] text-muted-foreground/70">{row.seenAt}</p>
                                        </button>
                                      )
                                    })}
                                  </div>
                                </details>
                              ))
                            ) : (
                              <div className="py-6 text-center text-sm text-muted-foreground">
                                {section === 'truth'
                                  ? 'No Financial Truth rows loaded. Set a ticker and click Load Ticker to browse docs + structured context.'
                                  : section === 'session'
                                  ? 'No session memory rows found.'
                                  : section === 'operational'
                                  ? 'No operational state rows found.'
                                  : 'No persistent memory rows found for this subsection.'}
                              </div>
                            )}
                          </div>

                          <div className="min-h-0 overflow-auto rounded-md border border-border/70 bg-background/40 p-3">
                            {selectedRow ? (
                              <div className="flex h-full min-h-[18rem] flex-col gap-3">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-mono text-xs text-muted-foreground">{selectedRowId}</span>
                                  <Badge variant={selectedStatus === 'active' || selectedStatus === 'applied' ? 'secondary' : 'outline'}>
                                    {selectedRow.status}
                                  </Badge>
                                </div>
                                <div className="space-y-1 text-xs text-muted-foreground">
                                  <p>Scope: {selectedRow.scope || '-'}</p>
                                  <p>Type: {selectedRow.type || '-'}</p>
                                  <p>Seen: {selectedRow.seenAt}</p>
                                  <p>Signal: {selectedRow.signal ?? '-'}</p>
                                  <p>Confidence: {selectedRow.confidence != null ? selectedRow.confidence : '-'}</p>
                                </div>
                                <div className="rounded-md border border-border/70 bg-background/60 p-2 text-sm whitespace-pre-wrap">
                                  {selectedRow.statement}
                                </div>
                                <div className="mt-auto flex flex-wrap gap-1">
                                  {selectedRow.editable ? (
                                    <Button size="sm" variant="outline" onClick={() => startEdit(selectedRow)} disabled={busy || loading}>
                                      Edit
                                    </Button>
                                  ) : null}
                                  {selectedRow.editable ? (
                                    <Button
                                      size="sm"
                                      variant="destructive"
                                      onClick={() => void expireRow(selectedRow)}
                                      disabled={busy || loading}
                                    >
                                      Expire
                                    </Button>
                                  ) : null}
                                  {selectedRow.kind === 'thesis_proposal' && selectedRow.status === 'pending' && selectedRow.proposalId ? (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => void runProposalAction(selectedRow, 'confirm')}
                                      disabled={busy || loading}
                                    >
                                      Confirm
                                    </Button>
                                  ) : null}
                                  {selectedRow.kind === 'thesis_proposal' &&
                                  (selectedRow.status === 'pending' || selectedRow.status === 'confirmed') &&
                                  selectedRow.proposalId ? (
                                    <Button
                                      size="sm"
                                      variant="destructive"
                                      onClick={() => void runProposalAction(selectedRow, 'reject')}
                                      disabled={busy || loading}
                                    >
                                      Reject
                                    </Button>
                                  ) : null}
                                  {selectedRow.kind === 'thesis_proposal' && selectedRow.status === 'confirmed' && selectedRow.proposalId ? (
                                    <Button
                                      size="sm"
                                      variant="default"
                                      onClick={() => void runProposalAction(selectedRow, 'apply')}
                                      disabled={busy || loading}
                                    >
                                      Apply
                                    </Button>
                                  ) : null}
                                </div>
                              </div>
                            ) : (
                              <div className="py-6 text-center text-sm text-muted-foreground">Select an entry to inspect or edit it.</div>
                            )}
                          </div>
                        </div>
                      </>
                    )
                  })()}
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </div>

      <div className="flex min-h-0 flex-col gap-4 overflow-auto">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Memory Level Directory</CardTitle>
            <CardDescription>Backend-owned memory surfaces.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {memoryLevels.map((level) => (
              <button
                key={level.level}
                type="button"
                onClick={() => {
                  if (level.section) {
                    updateActiveSection(level.section)
                  }
                }}
                disabled={!level.section}
                className={`w-full rounded-md border border-border/70 bg-background/50 p-2 text-left ${
                  level.section ? 'hover:border-border hover:bg-muted/40' : 'cursor-default opacity-85'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{level.label}</p>
                    <p className="truncate font-mono text-[10px] text-muted-foreground">{level.scope}</p>
                  </div>
                  <Badge
                    title={level.status}
                    variant={level.status === 'ok' || level.status === 'loaded' ? 'secondary' : 'outline'}
                  >
                    {displayLevelStatus(level.status)}
                  </Badge>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
                  <span>Rows {displayCount(level.rowCount)}</span>
                  <span>Entities {displayCount(level.entityCount)}</span>
                  <span className="truncate">{level.source}</span>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

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
              <Badge variant="outline">company tickers: {asString(summary.company_memory_ticker_count, '0')}</Badge>
              <Badge variant="outline">thesis tickers: {asString(summary.user_thesis_ticker_count, '0')}</Badge>
              <Badge variant="outline">sessions: {rowsBySection.session.length}</Badge>
              <Badge variant="outline">ops rows: {rowsBySection.operational.length}</Badge>
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
