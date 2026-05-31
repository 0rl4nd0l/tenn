import { describe, expect, it } from 'vitest'

import { deriveChatEvidenceActionability } from './cockpit-chat-actionability'
import type { ChatEvidenceStateCode } from './cockpit-chat-actionability'
import { buildHomeChatDraftHref, getHomeSourceActionability } from './cockpit-home-actionability'
import type { ChatMessage, Source } from './cockpit-types'
import type { CockpitHomeBackendSourceLabel, NewsItem, TrustLevel } from '@/types/cockpit-home'

type ChatMatrixRow = {
  name: string
  content: string
  evidenceLabels: string[]
  sources: Source[]
  expectedStates: ChatEvidenceStateCode[]
  absentStates: ChatEvidenceStateCode[]
  claimVerifiedSourceCount?: number
  sourceCoverageStatus?: string
  actionPreview?: ChatMessage['actionPreview']
}

const chatRows: ChatMatrixRow[] = [
  {
    name: 'direct claim-verified evidence',
    content: 'Revenue is source-backed in the FY25 filing.',
    evidenceLabels: ['claim_verified', 'financial_truth'],
    claimVerifiedSourceCount: 1,
    sourceCoverageStatus: 'claim_verified',
    sources: [
      source({
        title: 'CSL FY25 annual report',
        kind: 'document',
        docType: 'annual_report',
        evidenceLabel: 'claim_verified',
        evidenceLabels: ['claim_verified', 'financial_truth'],
        claimVerified: true,
      }),
    ],
    expectedStates: ['claim_verified'],
    absentStates: ['context_only', 'unsupported_or_not_verified'],
  },
  {
    name: 'live price source',
    content: 'CSL price trend is weakening based on visible price data.',
    evidenceLabels: ['operational_trace'],
    sources: [
      source({
        title: 'CSL live price data',
        kind: 'context',
        sourceId: 'price:CSL:current:1d',
        evidenceLabel: 'operational_trace',
        evidenceLabels: ['operational_trace'],
      }),
    ],
    expectedStates: [],
    absentStates: ['claim_verified', 'market_data_missing', 'unsupported_or_not_verified'],
  },
  {
    name: 'historical source context',
    content: 'CSL annual report filing context is available.',
    evidenceLabels: ['context_only'],
    sources: [
      source({
        title: 'CSL historical annual report',
        kind: 'document',
        docType: 'annual_report',
        evidenceLabel: 'context_only',
        evidenceLabels: ['context_only'],
      }),
    ],
    expectedStates: ['context_only'],
    absentStates: ['claim_verified', 'unsupported_or_not_verified'],
  },
  {
    name: 'weak local-news context',
    content: 'Draft answer from local news context.',
    evidenceLabels: ['context_only', 'local_news_context', 'unsupported_or_not_verified'],
    sources: [
      source({
        title: 'CSL scan-list mention',
        kind: 'news',
        docType: 'news',
        sourceId: 'news:scan-list:1',
        evidenceLabel: 'context_only',
        evidenceLabels: ['context_only', 'local_news_context'],
      }),
    ],
    expectedStates: ['context_only', 'unsupported_or_not_verified'],
    absentStates: ['claim_verified'],
  },
  {
    name: 'DATA_MISSING',
    content: 'DATA_MISSING: deterministic evidence is absent.',
    evidenceLabels: ['missing_required_evidence'],
    sourceCoverageStatus: 'missing_required_evidence',
    sources: [],
    expectedStates: ['unresolved_source', 'unsupported_or_not_verified'],
    absentStates: ['claim_verified'],
  },
  {
    name: 'no-hit',
    content: 'CSL looks bearish on the current price trend.',
    evidenceLabels: ['no_hit'],
    sources: [
      source({
        title: 'TradingView screener no rows',
        kind: 'context',
        docType: 'operational_no_hit',
        sourceId: 'tv_screener:ASX',
        evidenceLabel: 'no_hit',
        evidenceLabels: ['no_hit', 'operational_trace'],
      }),
    ],
    expectedStates: ['market_data_missing', 'unsupported_or_not_verified', 'no_hit'],
    absentStates: ['claim_verified'],
  },
  {
    name: 'degraded runtime',
    content: 'Runtime provider degraded before evidence could be collected.',
    evidenceLabels: ['degraded_runtime'],
    sourceCoverageStatus: 'degraded_runtime',
    sources: [
      source({
        title: 'Provider timeout',
        kind: 'context',
        docType: 'runtime_failure',
        sourceId: 'runtime_failure:price-provider',
        evidenceLabel: 'degraded_runtime',
        evidenceLabels: ['degraded_runtime'],
      }),
    ],
    expectedStates: ['degraded_runtime', 'context_only'],
    absentStates: ['claim_verified'],
  },
  {
    name: 'memory context',
    content: 'Draft answer from memory context.',
    evidenceLabels: ['memory_context'],
    sources: [
      source({
        title: 'Company memory note',
        kind: 'context',
        sourceId: 'memory:company:CSL',
        evidenceLabel: 'memory_context',
        evidenceLabels: ['memory_context'],
      }),
    ],
    expectedStates: ['memory_context', 'context_only'],
    absentStates: ['claim_verified', 'unsupported_or_not_verified'],
  },
  {
    name: 'external web context',
    content: 'Draft answer from external web context.',
    evidenceLabels: ['external_web_context'],
    sources: [
      source({
        title: 'External web snippet',
        kind: 'web',
        sourceId: 'web:snippet:1',
        evidenceLabel: 'external_web_context',
        evidenceLabels: ['external_web_context'],
      }),
    ],
    expectedStates: ['external_web_context', 'context_only'],
    absentStates: ['claim_verified', 'unsupported_or_not_verified'],
  },
  {
    name: 'unknown unclassified snippet',
    content: 'Draft answer from snippet-only context.',
    evidenceLabels: ['unknown_unclassified'],
    sources: [
      source({
        title: 'Snippet-only context',
        snippet: 'Unclassified context without a resolvable source identity.',
        evidenceLabel: 'unknown_unclassified',
        evidenceLabels: ['unknown_unclassified'],
      }),
    ],
    actionPreview: {
      id: 'verify_source',
      name: 'Verify source',
      description: 'Resolve source identity before using this context.',
      args: { ticker: 'CSL' },
      requiresConfirmation: true,
    },
    expectedStates: ['unresolved_source', 'snippet_only', 'draft_only', 'unsupported_or_not_verified'],
    absentStates: ['claim_verified'],
  },
]

type HomeMatrixRow = {
  name: string
  item: Partial<NewsItem>
  reason: ReturnType<typeof getHomeSourceActionability>['reason']
  canAttachToChat: boolean
  hrefCarriesSource: boolean
}

const homeRows: HomeMatrixRow[] = [
  {
    name: 'claim-verified Home source',
    item: {
      trustLevel: 'CLAIM-VERIFIED',
      sourceLabel: 'claim_verified',
      evidenceLabels: ['claim_verified'],
      sourceId: 'claim:CSL:1',
      sourceKind: 'primary',
    },
    reason: 'SOURCE_READY',
    canAttachToChat: true,
    hrefCarriesSource: true,
  },
  {
    name: 'context-only Home source',
    item: {
      trustLevel: 'CONTEXT-ONLY',
      sourceLabel: 'context_only',
      evidenceLabels: ['context_only'],
      sourceId: 'youtube_transcript:CSL:1',
      sourceKind: 'ephemeral',
    },
    reason: 'SOURCE_READY',
    canAttachToChat: true,
    hrefCarriesSource: true,
  },
  {
    name: 'DATA_MISSING Home source',
    item: {
      trustLevel: 'MISSING-EVIDENCE',
      dataState: 'DATA_MISSING',
      sourceLabel: 'missing_required_evidence',
      evidenceLabels: ['missing_required_evidence'],
      sourceId: null,
      sourceKind: null,
      resolvable: false,
      chatBlockedReason: 'DATA_MISSING',
    },
    reason: 'DATA_MISSING',
    canAttachToChat: false,
    hrefCarriesSource: false,
  },
  {
    name: 'degraded-runtime Home source',
    item: {
      trustLevel: 'DEGRADED-RUNTIME',
      dataState: 'DEGRADED',
      degraded: true,
      sourceLabel: 'degraded_runtime',
      evidenceLabels: ['degraded_runtime'],
      chatBlockedReason: 'DEGRADED',
    },
    reason: 'DEGRADED',
    canAttachToChat: false,
    hrefCarriesSource: false,
  },
  {
    name: 'demo Home source',
    item: {
      trustLevel: 'CONTEXT-ONLY',
      sourceLabel: 'context_only',
      evidenceLabels: ['context_only'],
      sourceId: null,
      sourceKind: null,
      resolvable: false,
      isDemo: true,
    },
    reason: 'DEMO_ONLY',
    canAttachToChat: false,
    hrefCarriesSource: false,
  },
  {
    name: 'unknown unresolved Home source',
    item: {
      trustLevel: 'UNKNOWN-UNCLASSIFIED',
      sourceLabel: 'unknown_unclassified',
      evidenceLabels: ['unknown_unclassified'],
      sourceId: null,
      sourceKind: null,
      resolvable: false,
      chatBlockedReason: 'UNRESOLVABLE_SOURCE',
    },
    reason: 'UNRESOLVABLE_SOURCE',
    canAttachToChat: false,
    hrefCarriesSource: false,
  },
]

describe('source label fixture matrix - Chat actionability', () => {
  it.each(chatRows)('$name', (row) => {
    const result = deriveChatEvidenceActionability(assistant(row))

    for (const state of row.expectedStates) {
      expect(result.stateCodes, state).toContain(state)
    }
    for (const state of row.absentStates) {
      expect(result.stateCodes, state).not.toContain(state)
    }
  })
})

describe('source label fixture matrix - Home trust labels', () => {
  it.each(homeRows)('$name', (row) => {
    const item = homeNewsItem(row.item)
    const actionability = getHomeSourceActionability(item)
    const href = buildHomeChatDraftHref('Assess this source.', item)

    expect(actionability.reason).toBe(row.reason)
    expect(actionability.canAttachToChat).toBe(row.canAttachToChat)
    expect(href.includes('source_id=')).toBe(row.hrefCarriesSource)
  })
})

function assistant(row: ChatMatrixRow): ChatMessage {
  return {
    id: `fixture:${row.name}`,
    role: 'assistant',
    content: row.content,
    timestamp: new Date('2026-05-31T00:00:00Z'),
    metadata: {
      source: 'orchestrator',
      analyst: {
        evidenceLabels: row.evidenceLabels,
        claimVerifiedSourceCount: row.claimVerifiedSourceCount ?? 0,
        sourceCoverageStatus: row.sourceCoverageStatus,
      },
    },
    sources: row.sources,
    actionPreview: row.actionPreview,
  }
}

function source(overrides: Partial<Source>): Source {
  return {
    title: 'Fixture source',
    score: 1,
    claimVerified: false,
    ...overrides,
  }
}

function homeNewsItem(overrides: Partial<NewsItem>): NewsItem {
  return {
    id: 'home-news:fixture',
    ticker: 'CSL',
    headline: 'Fixture Home source',
    timestamp: '10:00 am',
    source: 'fixture',
    trustLevel: (overrides.trustLevel ?? 'CONTEXT-ONLY') as TrustLevel,
    relevance: 'medium',
    dataState: overrides.dataState ?? 'READY',
    degraded: overrides.degraded ?? false,
    dataMissing: [],
    sourceId: overrides.sourceId === undefined ? 'fixture:source' : overrides.sourceId,
    sourceKind: overrides.sourceKind === undefined ? 'ephemeral' : overrides.sourceKind,
    sourceLabel: (overrides.sourceLabel ?? 'context_only') as CockpitHomeBackendSourceLabel,
    evidenceLabels: (overrides.evidenceLabels ?? ['context_only']) as CockpitHomeBackendSourceLabel[],
    resolvable: overrides.resolvable ?? true,
    resolver: 'cockpit_chat_attached_sources',
    sourceUrl: null,
    ...overrides,
  }
}
