import type { MarketplacePriceComparison } from '@/lib/marketplace-api'

export function comparisonVerdictLabel(value: string | null | undefined): string {
  return String(value || 'unavailable').replace(/_/g, ' ')
}

export function comparisonStatusLabel(
  comparison: MarketplacePriceComparison | null | undefined,
): string {
  if (comparison?.comparison_state === 'missing_benchmark_anchor') return 'benchmark unavailable'
  if (comparison?.comparison_state === 'retail_anchor_needs_review') return 'retail anchor needs review'
  if (comparison?.comparison_state === 'missing_listing_price') return 'listing price missing'
  return comparisonVerdictLabel(comparison?.verdict)
}

export function comparisonHelpText(
  comparison: MarketplacePriceComparison | null | undefined,
): string | null {
  const reason = String(comparison?.unavailable_reason || '').trim()
  const action = String(comparison?.next_action || '').trim()
  if (reason && action) return `${reason} ${action}`
  return reason || action || null
}

export function comparisonNeedsBenchmarkSetup(
  comparison: MarketplacePriceComparison | null | undefined,
): boolean {
  return (
    comparison?.comparison_state === 'missing_benchmark_anchor' ||
    comparison?.comparison_state === 'retail_anchor_needs_review'
  )
}
