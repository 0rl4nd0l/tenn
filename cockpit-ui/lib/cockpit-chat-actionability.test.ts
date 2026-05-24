import { describe, expect, it } from 'vitest'

import type { ChatMessage } from './cockpit-types'
import { deriveChatEvidenceActionability } from './cockpit-chat-actionability'

function assistant(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'assistant',
    content: 'CSL answer.',
    timestamp: new Date('2026-05-24T00:00:00Z'),
    ...overrides,
  }
}

describe('deriveChatEvidenceActionability', () => {
  it('marks CSL filing-only bearish price trend claims as missing market data', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        content: 'CSL looks bearish on the current price trend, while the filing shows a buy-back notice.',
        metadata: {
          source: 'orchestrator',
          analyst: {
            ticker: 'CSL',
            evidenceLabels: ['context_only'],
            sourceCoverageStatus: 'context_only',
            claimVerifiedSourceCount: 0,
          },
        },
        sources: [
          {
            title: 'CSL Appendix 3C buy-back notice',
            score: 0.91,
            kind: 'document',
            docType: 'asx_announcement',
            snippet: 'CSL lodged a buy-back notice.',
            evidenceLabel: 'context_only',
            evidenceLabels: ['context_only'],
            claimVerified: false,
          },
        ],
      }),
    )

    expect(result.hasMarketTrendClaim).toBe(true)
    expect(result.hasMarketPriceEvidence).toBe(false)
    expect(result.stateCodes).toContain('context_only')
    expect(result.stateCodes).toContain('market_data_missing')
    expect(result.stateCodes).toContain('unsupported_or_not_verified')
    expect(result.stateCodes).not.toContain('claim_verified')
    expect(result.gaps).toContain('market_data_missing')
    expect(result.suggestedActions).toContainEqual({ label: 'Pull market data', enabled: false })
  })

  it('does not mark trend language missing when visible price evidence exists', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        content: 'CSL price trend is weakening based on the visible price data.',
        sources: [
          {
            title: 'CSL price data',
            score: 1,
            kind: 'context',
            sourceId: 'price:CSL:1y:1d',
            snippet: 'Provider: yahoo; trend regime: bear',
            evidenceLabel: 'operational_trace',
            evidenceLabels: ['operational_trace'],
            claimVerified: false,
          },
        ],
      }),
    )

    expect(result.hasMarketTrendClaim).toBe(true)
    expect(result.hasMarketPriceEvidence).toBe(true)
    expect(result.stateCodes).not.toContain('market_data_missing')
  })

  it('does not treat filing text that mentions price as market-price evidence', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        content: 'CSL price trend is weakening, but the visible source is only a filing excerpt.',
        sources: [
          {
            title: 'CSL filing excerpt mentioning share price',
            score: 0.88,
            kind: 'document',
            docType: 'asx_announcement',
            snippet: 'The filing refers to share price only as background context.',
            evidenceLabel: 'context_only',
            evidenceLabels: ['context_only'],
            claimVerified: false,
          },
        ],
      }),
    )

    expect(result.hasMarketTrendClaim).toBe(true)
    expect(result.hasMarketPriceEvidence).toBe(false)
    expect(result.stateCodes).toContain('market_data_missing')
    expect(result.stateCodes).toContain('context_only')
    expect(result.stateCodes).toContain('unsupported_or_not_verified')
  })

  it('maps missing financial rows to metric extraction missing', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        content: 'I can discuss filings, but financial rows unavailable.',
        metadata: {
          source: 'orchestrator',
          analyst: {
            missingCategories: ['financials'],
            sufficientForAnalysis: false,
          },
        },
      }),
    )

    expect(result.stateCodes).toContain('metric_extraction_missing')
    expect(result.stateCodes).toContain('unsupported_or_not_verified')
    expect(result.gaps).toContain('metric_extraction_missing')
    expect(result.suggestedActions).toContainEqual({ label: 'Run metric extraction', enabled: false })
  })

  it('surfaces degraded runtime without hiding it', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        metadata: {
          source: 'local',
          analyst: {
            evidenceLabels: ['degraded_runtime'],
            sourceCoverageStatus: 'degraded_runtime',
          },
        },
      }),
    )

    expect(result.stateCodes).toContain('degraded_runtime')
    expect(result.gaps).toContain('degraded_runtime')
  })

  it('maps claim-verified source metadata without upgrading unrelated context states', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        content: 'Revenue is source-backed in the FY25 filing.',
        metadata: {
          source: 'orchestrator',
          analyst: {
            evidenceLabels: ['claim_verified', 'financial_truth'],
            claimVerifiedSourceCount: 1,
            sourceCoverageStatus: 'claim_verified',
          },
        },
        sources: [
          {
            title: 'CSL FY25 annual report',
            score: 0.96,
            kind: 'document',
            docType: 'annual_report',
            evidenceLabel: 'claim_verified',
            evidenceLabels: ['claim_verified', 'financial_truth'],
            claimVerified: true,
          },
        ],
      }),
    )

    expect(result.stateCodes).toContain('claim_verified')
    expect(result.stateCodes).not.toContain('context_only')
    expect(result.stateCodes).not.toContain('unsupported_or_not_verified')
  })

  it('maps the non-verified context taxonomy used by chat sources', () => {
    const result = deriveChatEvidenceActionability(
      assistant({
        content: 'Draft answer from demo context.',
        metadata: {
          source: 'orchestrator',
          analyst: {
            evidenceLabels: ['local_personal_data', 'memory_context', 'external_web_context', 'no_hit'],
            claimVerifiedSourceCount: 0,
            sourceCoverageStatus: 'no_hit',
          },
        },
        actionPreview: {
          id: 'verify_price',
          name: 'Verify price trend',
          description: 'Fetch market data before making trend claims.',
          args: { ticker: 'CSL' },
          requiresConfirmation: true,
        },
        sources: [
          {
            title: 'Snippet-only context',
            score: 0.1,
            snippet: 'A context snippet without a resolvable source identity.',
            evidenceLabel: 'unknown_unclassified',
            evidenceLabels: ['unknown_unclassified'],
            claimVerified: false,
          },
        ],
      }),
    )

    expect(result.stateCodes).toContain('no_hit')
    expect(result.stateCodes).toContain('local_personal_data')
    expect(result.stateCodes).toContain('memory_context')
    expect(result.stateCodes).toContain('external_web_context')
    expect(result.stateCodes).toContain('demo_mock')
    expect(result.stateCodes).toContain('unresolved_source')
    expect(result.stateCodes).toContain('snippet_only')
    expect(result.stateCodes).toContain('draft_only')
    expect(result.stateCodes).toContain('unsupported_or_not_verified')
  })
})
