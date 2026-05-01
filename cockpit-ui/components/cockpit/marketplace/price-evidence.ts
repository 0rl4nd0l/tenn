import type { MarketplaceMatch } from '@/lib/marketplace-api'

export interface MarketplacePriceEvidence {
  detail_price_text?: string | null
  card_price_text?: string | null
  resolved_price_text?: string | null
  resolved_price_value?: number | null
  source?: string | null
  warning?: string | null
}

function asPriceEvidence(value: unknown): MarketplacePriceEvidence | null {
  if (!value || typeof value !== 'object') return null
  return value as MarketplacePriceEvidence
}

export function priceEvidenceForMatch(match: MarketplaceMatch): MarketplacePriceEvidence | null {
  return asPriceEvidence(match.metadata?.price_evidence)
}

export function priceSourceLabel(evidence: MarketplacePriceEvidence | null): string {
  if (!evidence?.source) return 'source: unknown'
  if (evidence.source === 'detail') return 'source: detail'
  if (evidence.source === 'search_card') return 'source: search card'
  return `source: ${evidence.source.replace(/_/g, ' ')}`
}
