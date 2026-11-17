'use client'

import { useEffect, useState, useCallback } from 'react'
import { BellOff, CheckSquare, ExternalLink, ImageOff, RefreshCw, ThumbsDown, ThumbsUp, X } from 'lucide-react'
import Link from 'next/link'

import {
  listMarketplaceMissions,
  listMarketplaceMatches,
  type MarketplaceAlertPolicy,
  type MarketplaceDealMetrics,
  type MarketplaceMatch,
  type MarketplaceMatchFeedbackValue,
  type MarketplaceMission,
  type MarketplacePriceComparison,
  updateMarketplaceMatch,
  updateMarketplaceMatchFeedback,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  comparisonHelpText,
  comparisonNeedsBenchmarkSetup,
  comparisonStatusLabel,
} from './price-comparison'
import { priceEvidenceForMatch, priceSourceLabel } from './price-evidence'
import {
  compareByFirstFoundDesc,
  firstFoundTimestamp,
  formatMatchClock,
  hasMaterialLastSeenUpdate,
  isNewOpportunity,
  lastSeenTimestamp,
  shouldShowCapturedTimestamp,
} from './match-recency'

interface PendingFeedback {
  matchId: string
  feedback: MarketplaceMatchFeedbackValue
  note: string
}

interface MarketplaceMatchesScreenProps {
  apiKey: string
}

const MATCH_STATUS_OPTIONS = [
  { value: 'new', label: 'New' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'won', label: 'Won' },
  { value: 'lost', label: 'Lost' },
] as const

const MATCH_SORT_OPTIONS = [
  { value: 'score', label: 'Best score' },
  { value: 'value', label: 'Best value' },
  { value: 'newest', label: 'Newest' },
  { value: 'cheapest', label: 'Cheapest' },
] as const

type MatchSortMode = (typeof MATCH_SORT_OPTIONS)[number]['value']

interface MarketplaceEmptyContext {
  reason: 'data_missing' | 'filter_excludes' | 'no_missions' | 'not_run' | 'zero_results'
  title: string
  detail: string
  actionLabel: string
  actionHref?: string
  showClearFilters?: boolean
}

function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`
}

function missionScanCount(missions: MarketplaceMission[]): number {
  return missions.filter((mission) => Boolean(mission.last_scan_at)).length
}

function firstMissionError(missions: MarketplaceMission[]): string | null {
  const failedMission = missions.find((mission) => mission.last_error)
  if (!failedMission?.last_error) return null
  return `${failedMission.name}: ${failedMission.last_error}`
}

function emptyContextUnavailable(error: unknown, surface: 'matches' | 'alerts'): MarketplaceEmptyContext {
  const detail = error instanceof Error ? error.message : 'unknown error'
  return {
    reason: 'data_missing',
    title: 'DATA_MISSING: Marketplace mission context unavailable.',
    detail: `The ${surface} endpoint returned zero items, but mission/run evidence could not be loaded: ${detail}`,
    actionLabel: 'Open mission setup',
    actionHref: '/marketplace',
  }
}

function matchesEmptyContext(
  missions: MarketplaceMission[],
  unfilteredMatchCount: number,
  filtersActive: boolean,
): MarketplaceEmptyContext {
  if (filtersActive && unfilteredMatchCount > 0) {
    return {
      reason: 'filter_excludes',
      title: 'Filters are hiding existing matches.',
      detail: `Unfiltered Marketplace evidence contains ${pluralize(
        unfilteredMatchCount,
        'match',
        'matches',
      )}; the current filters returned zero.`,
      actionLabel: 'Clear filters',
      showClearFilters: true,
    }
  }

  if (missions.length === 0) {
    return {
      reason: 'no_missions',
      title: 'No Marketplace missions configured yet.',
      detail: 'Matches require a saved mission before Tenn can scan Marketplace listings.',
      actionLabel: 'Open mission setup',
      actionHref: '/marketplace',
    }
  }

  const missionError = firstMissionError(missions)
  if (missionError) {
    return {
      reason: 'data_missing',
      title: 'DATA_MISSING: Marketplace scan state is degraded.',
      detail: `Mission evidence is available, but at least one mission reports an error: ${missionError}`,
      actionLabel: 'Open mission setup',
      actionHref: '/marketplace',
    }
  }

  const scannedMissions = missionScanCount(missions)
  if (scannedMissions === 0) {
    return {
      reason: 'not_run',
      title: 'Marketplace missions exist, but no scan run is recorded.',
      detail: `${pluralize(missions.length, 'mission')} returned from the backend; none include last_scan_at.`,
      actionLabel: 'Open mission setup',
      actionHref: '/marketplace',
    }
  }

  return {
    reason: 'zero_results',
    title: 'Marketplace scans ran, but no matches were returned.',
    detail: `${pluralize(scannedMissions, 'mission')} include last_scan_at; the current result set is empty.`,
    actionLabel: 'Open mission setup',
    actionHref: '/marketplace',
  }
}

function decisionVariant(
  decisionBand: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (decisionBand === 'strong_match') return 'default'
  if (decisionBand === 'candidate') return 'secondary'
  if (decisionBand === 'reject') return 'destructive'
  return 'outline'
}

function formatCurrency(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'n/a'
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDelta(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'n/a'
  const rounded = Math.round(value * 10) / 10
  const sign = rounded > 0 ? '+' : ''
  return `${sign}${rounded}%`
}

function formatCapacity(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return 'n/a'
  if (value >= 1000) {
    const tb = value / 1000
    return `${Number.isInteger(tb) ? tb.toFixed(0) : tb.toFixed(1)}TB`
  }
  return `${Math.round(value)}GB`
}

function cleanLabel(value: string | null | undefined): string {
  return String(value || '').replace(/_/g, ' ')
}

function benchmarkAnchorLabel(comparison: MarketplacePriceComparison | null | undefined): string {
  if (typeof comparison?.used_market_median === 'number') return formatCurrency(comparison.used_market_median)
  if (typeof comparison?.retail_anchor_price === 'number') return formatCurrency(comparison.retail_anchor_price)
  if (typeof comparison?.listing_price === 'number' && comparisonNeedsBenchmarkSetup(comparison)) return 'Needs setup'
  return 'N/A'
}

function comparisonToneClass(comparison: MarketplacePriceComparison | null | undefined): string {
  const color = String(comparison?.color || '').toLowerCase()
  if (color === 'green' || color === 'emerald') {
    return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
  }
  if (color === 'red') {
    return 'border-destructive/35 bg-destructive/10 text-destructive'
  }
  if (color === 'amber') {
    return 'border-amber-500/35 bg-amber-500/10 text-amber-800 dark:text-amber-200'
  }
  return 'border-border/60 bg-muted/20 text-muted-foreground'
}

function valueBadgeVariant(
  label: string | null | undefined,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  const normalized = String(label || '').toLowerCase()
  if (normalized.includes('good') || normalized.includes('strong')) return 'default'
  if (normalized.includes('overpriced') || normalized.includes('poor')) return 'destructive'
  if (normalized.includes('unavailable') || normalized.includes('insufficient')) return 'outline'
  return 'secondary'
}

function dealMetricTone(metric: MarketplaceDealMetrics | null | undefined): string {
  const score = Number(metric?.deal_score)
  if (Number.isFinite(score)) {
    if (score >= 70) return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
    if (score < 50) return 'border-destructive/35 bg-destructive/10 text-destructive'
  }
  const usedDelta = Number(metric?.delta_vs_used_median?.percent)
  if (Number.isFinite(usedDelta)) {
    if (usedDelta <= -5) return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
    if (usedDelta > 10) return 'border-destructive/35 bg-destructive/10 text-destructive'
  }
  return 'border-border/60 bg-background text-muted-foreground'
}

function usedDeltaTone(percent: number): string {
  if (percent <= -5) return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
  if (percent > 10) return 'border-destructive/35 bg-destructive/10 text-destructive'
  return 'border-amber-500/35 bg-amber-500/10 text-amber-800 dark:text-amber-200'
}

function retailDeltaTone(percent: number): string {
  if (percent <= -15) return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
  if (percent >= 0) return 'border-destructive/35 bg-destructive/10 text-destructive'
  return 'border-amber-500/35 bg-amber-500/10 text-amber-800 dark:text-amber-200'
}

function benchmarkHealthTone(label: string | null | undefined): string {
  const normalized = String(label || '').toLowerCase()
  if (normalized === 'high') return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
  if (normalized === 'low') return 'border-destructive/35 bg-destructive/10 text-destructive'
  if (normalized === 'medium') return 'border-amber-500/35 bg-amber-500/10 text-amber-800 dark:text-amber-200'
  return 'border-border/60 bg-background text-muted-foreground'
}

function priceMovementTone(direction: string | null | undefined): string {
  if (direction === 'drop') return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200'
  if (direction === 'increase') return 'border-destructive/35 bg-destructive/10 text-destructive'
  return 'border-border/60 bg-background text-muted-foreground'
}

function listingMedia(match: MarketplaceMatch): string[] {
  const media = Array.isArray(match.listing_media) ? match.listing_media : []
  const urls = media
    .map((item) => String(item ?? '').trim())
    .filter((item) => /^https?:\/\//i.test(item))
  if (urls.length > 0) {
    return urls
  }
  if (match.screenshot_path && /^https?:\/\//i.test(match.screenshot_path)) {
    return [match.screenshot_path]
  }
  return []
}

function scoreValue(match: MarketplaceMatch): number {
  const score = Number(match.score)
  return Number.isFinite(score) ? score : -1
}

function valueScore(match: MarketplaceMatch): number {
  const valueContextScore = Number(match.value_context?.value_score)
  if (Number.isFinite(valueContextScore)) return valueContextScore
  const dealScore = Number(match.deal_metrics?.deal_score)
  if (Number.isFinite(dealScore)) return dealScore
  return scoreValue(match)
}

function priceValue(match: MarketplaceMatch): number {
  const explicitPrice = Number(match.price_value)
  if (Number.isFinite(explicitPrice) && explicitPrice > 0) return explicitPrice
  const comparisonPrice = Number(match.price_comparison?.listing_price)
  if (Number.isFinite(comparisonPrice) && comparisonPrice > 0) return comparisonPrice
  const dealPrice = Number(match.deal_metrics?.listing_price)
  if (Number.isFinite(dealPrice) && dealPrice > 0) return dealPrice
  return Number.POSITIVE_INFINITY
}

function alertPolicyForMatch(match: MarketplaceMatch): MarketplaceAlertPolicy | null {
  if (match.deal_metrics?.alert_policy) return match.deal_metrics.alert_policy
  const policy = match.metadata?.alert_policy
  return policy && typeof policy === 'object' ? (policy as MarketplaceAlertPolicy) : null
}

function isAboveRetail(match: MarketplaceMatch): boolean {
  const retailDelta =
    match.deal_metrics?.delta_vs_retail_anchor?.percent ??
    match.price_comparison?.delta_vs_retail_anchor?.percent
  return typeof retailDelta === 'number' && Number.isFinite(retailDelta) && retailDelta >= 0
}

function hasWeakBenchmark(match: MarketplaceMatch): boolean {
  const health = match.deal_metrics?.benchmark_health?.label
  if (health) return String(health).toLowerCase() === 'low'
  return comparisonNeedsBenchmarkSetup(match.price_comparison ?? null)
}

function sortMatches(items: MarketplaceMatch[], mode: MatchSortMode): MarketplaceMatch[] {
  return [...items].sort((left, right) => {
    if (mode === 'value') {
      const valueCompare = valueScore(right) - valueScore(left)
      if (valueCompare !== 0) return valueCompare
    } else if (mode === 'newest') {
      const timeCompare = compareByFirstFoundDesc(left, right)
      if (timeCompare !== 0) return timeCompare
    } else if (mode === 'cheapest') {
      const leftPrice = priceValue(left)
      const rightPrice = priceValue(right)
      if (leftPrice !== rightPrice) return leftPrice - rightPrice
    }
    const scoreCompare = scoreValue(right) - scoreValue(left)
    if (scoreCompare !== 0) return scoreCompare
    return compareByFirstFoundDesc(left, right)
  })
}

function DealMetricChips({
  comparison,
  dealMetrics,
  valueContext,
}: {
  comparison: MarketplacePriceComparison | null | undefined
  dealMetrics: MarketplaceDealMetrics | null | undefined
  valueContext: MarketplaceMatch['value_context']
}) {
  const value = Number(valueContext?.value_score ?? dealMetrics?.deal_score)
  const valueLabel = valueContext?.value_label || dealMetrics?.deal_label
  const usedDelta =
    dealMetrics?.delta_vs_used_median?.percent ??
    comparison?.delta_vs_used_median?.percent
  const retailDelta =
    dealMetrics?.delta_vs_retail_anchor?.percent ??
    comparison?.delta_vs_retail_anchor?.percent
  const pricePerTb = dealMetrics?.price_per_tb
  const capacity = dealMetrics?.capacity_gb
  const sampleSize =
    dealMetrics?.benchmark_sample_size ?? valueContext?.benchmark_sample_size
  const comparableGroup = dealMetrics?.comparable_group
  const benchmarkHealth = dealMetrics?.benchmark_health
  const priceMovement = dealMetrics?.price_movement
  const alertPolicy = dealMetrics?.alert_policy
  const blockedAlerts = alertPolicy?.blocked_reasons ?? []

  return (
    <div className="flex flex-wrap gap-1.5">
      {comparableGroup?.label && (
        <span className="rounded border border-border/60 bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
          Group {comparableGroup.label}
        </span>
      )}
      {Number.isFinite(value) && (
        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${dealMetricTone(dealMetrics)}`}>
          Value {Math.round(value)} {valueLabel ? `- ${cleanLabel(valueLabel)}` : ''}
        </span>
      )}
      {benchmarkHealth?.label && (
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${benchmarkHealthTone(benchmarkHealth.label)}`}>
          Bench {cleanLabel(benchmarkHealth.label)}
        </span>
      )}
      {priceMovement?.direction && typeof priceMovement.percent === 'number' && (
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${priceMovementTone(priceMovement.direction)}`}>
          {priceMovement.direction === 'drop' ? 'Drop' : 'Up'} {Math.round(Math.abs(priceMovement.percent) * 10) / 10}%
        </span>
      )}
      {typeof usedDelta === 'number' && !Number.isNaN(usedDelta) && (
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${usedDeltaTone(usedDelta)}`}>
          Vs used {formatDelta(usedDelta)}
        </span>
      )}
      {typeof retailDelta === 'number' && !Number.isNaN(retailDelta) && (
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${retailDeltaTone(retailDelta)}`}>
          Vs retail {formatDelta(retailDelta)}
        </span>
      )}
      {typeof pricePerTb === 'number' && !Number.isNaN(pricePerTb) && (
        <span className="rounded border border-border/60 bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
          {formatCurrency(pricePerTb)}/TB
        </span>
      )}
      {typeof capacity === 'number' && !Number.isNaN(capacity) && (
        <span className="rounded border border-border/60 bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
          {formatCapacity(capacity)}
        </span>
      )}
      {typeof sampleSize === 'number' && !Number.isNaN(sampleSize) && sampleSize > 0 && (
        <span className="rounded border border-border/60 bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
          n={Math.round(sampleSize)}
        </span>
      )}
      {blockedAlerts.length > 0 && (
        <span className="rounded border border-amber-500/35 bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-800 dark:text-amber-200">
          No alert: {blockedAlerts[0]}
        </span>
      )}
    </div>
  )
}

function ScoreGauge({ score, compact = false }: { score: number; compact?: boolean }) {
  const safeScore = Number.isFinite(score) ? score : 0
  const normalizedScore = Math.max(0, Math.min(100, safeScore))
  const radius = 40
  const circumference = Math.PI * radius
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference

  let colorClass = 'text-emerald-500'
  if (normalizedScore < 50) colorClass = 'text-destructive'
  else if (normalizedScore < 75) colorClass = 'text-amber-500'

  return (
    <div className={compact ? 'relative h-10 w-20' : 'relative h-16 w-32'}>
      <svg viewBox="0 0 100 50" className="w-full h-full overflow-visible">
        <path
          d="M 10 50 A 40 40 0 0 1 90 50"
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          className="text-muted/20"
        />
        <path
          d="M 10 50 A 40 40 0 0 1 90 50"
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={`transition-all duration-1000 ease-in-out ${colorClass}`}
        />
      </svg>
      <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center justify-end translate-y-1.5">
        <span className={`${compact ? 'text-lg' : 'text-2xl'} font-bold font-mono tracking-tighter`}>
          {normalizedScore}
        </span>
      </div>
    </div>
  )
}

function MatchesEmptyState({
  context,
  onClearFilters,
  onRefresh,
}: {
  context: MarketplaceEmptyContext | null
  onClearFilters: () => void
  onRefresh: () => void
}) {
  const resolved = context ?? {
    reason: 'data_missing',
    title: 'DATA_MISSING: Marketplace empty-state context unavailable.',
    detail: 'The matches endpoint returned zero items, but no mission/run context was available to explain why.',
    actionLabel: 'Open mission setup',
    actionHref: '/marketplace',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-md border border-dashed border-border px-6 py-16 text-center">
      <RefreshCw className="h-12 w-12 text-muted-foreground/30" />
      <div className="max-w-2xl space-y-2">
        <p className="text-base font-medium text-foreground">{resolved.title}</p>
        <p className="text-sm text-muted-foreground">{resolved.detail}</p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {resolved.showClearFilters ? (
          <Button size="sm" onClick={onClearFilters}>
            {resolved.actionLabel}
          </Button>
        ) : resolved.actionHref ? (
          <Button size="sm" asChild>
            <Link href={resolved.actionHref}>{resolved.actionLabel}</Link>
          </Button>
        ) : null}
        <Button size="sm" variant="outline" onClick={onRefresh}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>
    </div>
  )
}

export function MarketplaceMatchesScreen({ apiKey }: MarketplaceMatchesScreenProps) {
  const [matches, setMatches] = useState<MarketplaceMatch[]>([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [bandFilter, setBandFilter] = useState('all')
  const [sortMode, setSortMode] = useState<MatchSortMode>('newest')
  const [newOnly, setNewOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [feedbackSavingMatchId, setFeedbackSavingMatchId] = useState<string | null>(null)
  const [bulkSaving, setBulkSaving] = useState(false)
  const [selectedMatchIds, setSelectedMatchIds] = useState<Set<string>>(() => new Set())
  const [pendingFeedback, setPendingFeedback] = useState<PendingFeedback | null>(null)
  const [emptyContext, setEmptyContext] = useState<MarketplaceEmptyContext | null>(null)
  const serverSort = sortMode === 'newest' ? 'first_found_desc' : undefined

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setEmptyContext(null)
    try {
      const items = await listMarketplaceMatches(apiKey, {
        status: statusFilter === 'all' ? undefined : statusFilter,
        decisionBand: bandFilter === 'all' ? undefined : bandFilter,
        sort: serverSort,
      })
      setMatches(items)
      setSelectedMatchIds(new Set())
      if (items.length === 0) {
        const filtersActive = statusFilter !== 'all' || bandFilter !== 'all'
        try {
          const [missions, unfilteredMatches] = await Promise.all([
            listMarketplaceMissions(apiKey),
            filtersActive
              ? listMarketplaceMatches(apiKey, { sort: serverSort })
              : Promise.resolve<MarketplaceMatch[]>([]),
          ])
          setEmptyContext(matchesEmptyContext(missions, unfilteredMatches.length, filtersActive))
        } catch (contextError) {
          setEmptyContext(emptyContextUnavailable(contextError, 'matches'))
        }
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load Marketplace matches')
    } finally {
      setLoading(false)
    }
  }, [apiKey, statusFilter, bandFilter, serverSort])

  useEffect(() => {
    void load()
  }, [load])

  async function handleStatus(matchId: string, status: string) {
    setError(null)
    try {
      await updateMarketplaceMatch(apiKey, matchId, status)
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Match update failed')
    }
  }

  function handleFeedback(matchId: string, feedback: MarketplaceMatchFeedbackValue) {
    // Toggle: clicking the same button again while pending cancels the pending state
    if (pendingFeedback?.matchId === matchId && pendingFeedback.feedback === feedback) {
      setPendingFeedback(null)
      return
    }
    setPendingFeedback({ matchId, feedback, note: '' })
  }

  async function confirmFeedback() {
    if (!pendingFeedback) return
    const { matchId, feedback, note } = pendingFeedback
    setError(null)
    setFeedbackSavingMatchId(matchId)
    setPendingFeedback(null)
    try {
      const updated = await updateMarketplaceMatchFeedback(apiKey, matchId, feedback, note.trim() || null)
      if (feedback === 'not_interested') {
        setMatches((current) => current.filter((item) => item.match_id !== matchId))
      } else {
        setMatches((current) =>
          current.map((item) => (item.match_id === matchId ? updated : item)),
        )
      }
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Match feedback update failed')
    } finally {
      setFeedbackSavingMatchId(null)
    }
  }

  const newOpportunityCount = matches.filter((match) => isNewOpportunity(match)).length
  const filteredMatches = newOnly ? matches.filter((match) => isNewOpportunity(match)) : matches
  const visibleMatches = sortMatches(filteredMatches, sortMode)
  const selectedMatches = visibleMatches.filter((match) => selectedMatchIds.has(match.match_id))
  const aboveRetailMatches = visibleMatches.filter(isAboveRetail)
  const weakBenchmarkMatches = visibleMatches.filter(hasWeakBenchmark)

  function clearMatchFilters() {
    setStatusFilter('all')
    setBandFilter('all')
    setNewOnly(false)
    setSelectedMatchIds(new Set())
  }

  function toggleMatchSelection(matchId: string) {
    setSelectedMatchIds((current) => {
      const next = new Set(current)
      if (next.has(matchId)) {
        next.delete(matchId)
      } else {
        next.add(matchId)
      }
      return next
    })
  }

  async function bulkUpdateStatus(targets: MarketplaceMatch[], status: string) {
    if (targets.length === 0) return
    setError(null)
    setBulkSaving(true)
    try {
      await Promise.all(targets.map((match) => updateMarketplaceMatch(apiKey, match.match_id, status)))
      setSelectedMatchIds(new Set())
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Bulk match update failed')
    } finally {
      setBulkSaving(false)
    }
  }

  async function bulkMarkNotInterested(targets: MarketplaceMatch[], note: string) {
    if (targets.length === 0) return
    setError(null)
    setBulkSaving(true)
    try {
      await Promise.all(
        targets.map((match) =>
          updateMarketplaceMatchFeedback(apiKey, match.match_id, 'not_interested', note),
        ),
      )
      const targetIds = new Set(targets.map((match) => match.match_id))
      setMatches((current) => current.filter((match) => !targetIds.has(match.match_id)))
      setSelectedMatchIds(new Set())
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Bulk feedback update failed')
    } finally {
      setBulkSaving(false)
    }
  }

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-5 p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Marketplace Matches</h2>
            <p className="text-sm text-muted-foreground">
              Review saved matches from active Marketplace missions.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Status:</span>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-8 w-[140px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all" className="text-xs">All Status</SelectItem>
                {MATCH_STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value} className="text-xs">
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Band:</span>
            <Select value={bandFilter} onValueChange={setBandFilter}>
              <SelectTrigger className="h-8 w-[140px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all" className="text-xs">All Bands</SelectItem>
                <SelectItem value="strong_match" className="text-xs">Strong Match</SelectItem>
                <SelectItem value="candidate" className="text-xs">Candidate</SelectItem>
                <SelectItem value="reject" className="text-xs">Reject</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Sort:</span>
            <Select value={sortMode} onValueChange={(value) => setSortMode(value as MatchSortMode)}>
              <SelectTrigger className="h-8 w-[140px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MATCH_SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value} className="text-xs">
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <label className="flex h-8 items-center gap-2 rounded-md border border-border/60 bg-background px-2 text-xs font-medium text-muted-foreground">
            <input
              type="checkbox"
              checked={newOnly}
              onChange={(event) => {
                setNewOnly(event.target.checked)
                setSelectedMatchIds(new Set())
              }}
              className="h-3.5 w-3.5 rounded border-border accent-primary"
            />
            New only
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-foreground">
              {newOpportunityCount}
            </span>
          </label>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {(selectedMatches.length > 0 || aboveRetailMatches.length > 0 || weakBenchmarkMatches.length > 0) && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-border/60 bg-muted/10 px-3 py-2">
            <span className="mr-1 text-xs font-medium text-muted-foreground">
              {selectedMatches.length} selected
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[11px]"
              disabled={bulkSaving || selectedMatches.length === 0}
              onClick={() => void bulkUpdateStatus(selectedMatches, 'dismissed')}
            >
              <BellOff className="mr-1 h-3 w-3" />
              Dismiss
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[11px]"
              disabled={bulkSaving || selectedMatches.length === 0}
              onClick={() => void bulkMarkNotInterested(selectedMatches, 'Bulk hidden from matches tab')}
            >
              <ThumbsDown className="mr-1 h-3 w-3" />
              Not interested
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[11px]"
              disabled={bulkSaving || aboveRetailMatches.length === 0}
              onClick={() => void bulkUpdateStatus(aboveRetailMatches, 'dismissed')}
            >
              <BellOff className="mr-1 h-3 w-3" />
              Hide above retail ({aboveRetailMatches.length})
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[11px]"
              disabled={bulkSaving || weakBenchmarkMatches.length === 0}
              onClick={() => void bulkUpdateStatus(weakBenchmarkMatches, 'dismissed')}
            >
              <CheckSquare className="mr-1 h-3 w-3" />
              Hide weak benchmark ({weakBenchmarkMatches.length})
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto h-7 px-2 text-[11px]"
              disabled={bulkSaving || selectedMatches.length === 0}
              onClick={() => setSelectedMatchIds(new Set())}
            >
              <X className="mr-1 h-3 w-3" />
              Clear
            </Button>
          </div>
        )}

        {loading && matches.length === 0 ? (
          <div className="flex items-center justify-center p-20">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : matches.length === 0 ? (
          <MatchesEmptyState
            context={emptyContext}
            onClearFilters={clearMatchFilters}
            onRefresh={() => void load()}
          />
        ) : visibleMatches.length === 0 ? (
          <MatchesEmptyState
            context={{
              reason: 'filter_excludes',
              title: 'New only is hiding existing matches.',
              detail: `Marketplace returned ${pluralize(matches.length, 'match', 'matches')}, but none qualify as new.`,
              actionLabel: 'Clear filters',
              showClearFilters: true,
            }}
            onClearFilters={clearMatchFilters}
            onRefresh={() => void load()}
          />
        ) : (
          <div data-testid="marketplace-match-grid" className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {visibleMatches.map((match) => {
              const media = listingMedia(match)
              const firstMedia = media[0] ?? null
              const priceEvidence = priceEvidenceForMatch(match)
              const comparison = match.price_comparison ?? null
              const baseDealMetrics = match.deal_metrics ?? null
              const alertPolicy = alertPolicyForMatch(match)
              const dealMetrics =
                baseDealMetrics && alertPolicy && !baseDealMetrics.alert_policy
                  ? { ...baseDealMetrics, alert_policy: alertPolicy }
                  : baseDealMetrics
              const userFeedback = match.user_feedback?.feedback ?? null
              const isSelected = selectedMatchIds.has(match.match_id)
              const firstFoundAt = firstFoundTimestamp(match)
              const lastSeenAt = lastSeenTimestamp(match)
              const showCapturedAt = shouldShowCapturedTimestamp(match)
              return (
                <Card
                  key={match.match_id}
                  data-testid="marketplace-match-card"
                  className="gap-0 overflow-hidden rounded-lg border-border/50 py-0 transition-colors hover:bg-muted/5"
                >
                  <div className="border-b border-border/50 bg-muted/10 px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                        <input
                          type="checkbox"
                          aria-label={`Select ${match.title}`}
                          checked={isSelected}
                          onChange={() => toggleMatchSelection(match.match_id)}
                          className="h-4 w-4 shrink-0 rounded border-border accent-primary"
                        />
                        <Badge variant={decisionVariant(match.decision_band)} className="h-5 text-[10px]">
                          {match.decision_band.replace('_', ' ')}
                        </Badge>
                        {isNewOpportunity(match) && (
                          <Badge className="h-5 border-transparent bg-emerald-600 text-[10px] text-white hover:bg-emerald-600">
                            NEW
                          </Badge>
                        )}
                        {hasMaterialLastSeenUpdate(match) && (
                          <Badge
                            variant="outline"
                            className="h-5 border-sky-500/35 bg-sky-500/10 text-[10px] text-sky-800 dark:text-sky-200"
                          >
                            RECENTLY SEEN
                          </Badge>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-[11px]">
                          <Link href={`/marketplace/matches/${match.match_id}`}>
                            Details
                          </Link>
                        </Button>
                        {match.listing_url && (
                          <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-[11px] text-primary">
                            <a href={match.listing_url} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="mr-1 h-3 w-3" />
                              View
                            </a>
                          </Button>
                        )}
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <Select
                        value={match.status}
                        onValueChange={(val) => void handleStatus(match.match_id, val)}
                      >
                        <SelectTrigger className="h-7 w-[92px] text-[11px] font-medium">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {MATCH_STATUS_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value} className="text-[11px]">
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        variant={
                          pendingFeedback?.matchId === match.match_id && pendingFeedback.feedback === 'interested'
                            ? 'default'
                            : userFeedback === 'interested' ? 'default' : 'outline'
                        }
                        size="sm"
                        disabled={feedbackSavingMatchId === match.match_id}
                        onClick={() => handleFeedback(match.match_id, 'interested')}
                        className="h-7 px-2 text-[11px]"
                      >
                        <ThumbsUp className="mr-1 h-3 w-3" />
                        Interested
                      </Button>
                      <Button
                        variant={
                          pendingFeedback?.matchId === match.match_id && pendingFeedback.feedback === 'not_interested'
                            ? 'secondary'
                            : userFeedback === 'not_interested' ? 'secondary' : 'outline'
                        }
                        size="sm"
                        disabled={feedbackSavingMatchId === match.match_id}
                        onClick={() => handleFeedback(match.match_id, 'not_interested')}
                        className="h-7 px-2 text-[11px]"
                      >
                        <ThumbsDown className="mr-1 h-3 w-3" />
                        Not interested
                      </Button>
                    </div>
                  </div>

                  {/* Inline note panel */}
                  {pendingFeedback?.matchId === match.match_id && (
                    <div className="flex flex-col gap-2 border-b border-border/50 bg-muted/10 px-3 py-2">
                      <p className="text-xs text-muted-foreground">
                        {pendingFeedback.feedback === 'not_interested'
                          ? 'Why not? (optional — helps the system learn)'
                          : 'What do you like about this? (optional)'}
                      </p>
                      <Textarea
                        autoFocus
                        rows={2}
                        placeholder={
                          pendingFeedback.feedback === 'not_interested'
                            ? 'e.g. wrong brand, too old, price too high…'
                            : 'e.g. great condition, good price for spec…'
                        }
                        value={pendingFeedback.note}
                        onChange={(e) =>
                          setPendingFeedback((p) => p ? { ...p, note: e.target.value } : p)
                        }
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void confirmFeedback()
                          if (e.key === 'Escape') setPendingFeedback(null)
                        }}
                        className="text-xs resize-none"
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" className="h-7 text-xs" onClick={() => void confirmFeedback()}>
                          Confirm
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs"
                          onClick={() => setPendingFeedback(null)}
                        >
                          Cancel
                        </Button>
                        <span className="text-xs text-muted-foreground">Cmd+Enter to confirm; Esc to cancel</span>
                      </div>
                    </div>
                  )}

                  {/* Existing note */}
                  {!pendingFeedback && match.user_feedback?.note && (
                    <div className="border-b border-border/50 bg-muted/5 px-3 py-2">
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium">Your note:</span> {match.user_feedback.note}
                      </p>
                    </div>
                  )}

                  <CardContent className="flex flex-1 flex-col p-0">
                    <div className="space-y-2 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 space-y-1">
                          <h3 className="line-clamp-2 text-sm font-semibold leading-snug">{match.title}</h3>
                          <div className="grid gap-x-3 gap-y-1 text-[11px] text-muted-foreground sm:grid-cols-2">
                            <div className="min-w-0 truncate">
                              Brand:{' '}
                              <span className="font-medium text-foreground">
                                {String(match.metadata?.brand || 'Unknown')}
                              </span>
                            </div>
                            <div className="min-w-0 truncate">
                              Location:{' '}
                              <span className="font-medium text-foreground">
                                {match.location || 'Unknown'}
                              </span>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
                            <span>
                              {match.first_found_at ? 'First found' : 'First found (capture)'}{' '}
                              <span className="font-mono text-foreground/80">
                                {formatMatchClock(firstFoundAt)}
                              </span>
                            </span>
                            <span>
                              Last seen{' '}
                              <span className="font-mono text-foreground/80">
                                {formatMatchClock(lastSeenAt)}
                              </span>
                            </span>
                            {showCapturedAt && (
                              <span>
                                Captured{' '}
                                <span className="font-mono text-foreground/80">
                                  {formatMatchClock(match.captured_at)}
                                </span>
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="shrink-0 pt-1">
                          <ScoreGauge score={match.score} compact />
                        </div>
                      </div>
                    </div>

                    <div className="relative aspect-[16/9] w-full overflow-hidden border-y border-border/50 bg-muted/20 p-2">
                      {firstMedia ? (
                        <>
                          {/* Marketplace captures can come from arbitrary external CDNs. */}
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={firstMedia}
                            alt={`Listing photo for ${match.title}`}
                            className="h-full w-full object-contain"
                          />
                        </>
                      ) : (
                        <div className="flex h-full min-h-32 items-center justify-center gap-2 text-xs text-muted-foreground">
                          <ImageOff className="h-4 w-4" />
                          Listing photos unavailable
                        </div>
                      )}
                      <div className="absolute bottom-2 left-2 flex flex-wrap gap-1.5">
                        <Badge variant="outline" className="bg-background/85 text-[10px] backdrop-blur-sm">
                          photos: {media.length}
                        </Badge>
                        <Badge variant="outline" className="bg-background/85 text-[10px] backdrop-blur-sm">
                          {priceSourceLabel(priceEvidence)}
                        </Badge>
                      </div>
                    </div>

                  <div className="space-y-2 border-b border-border/50 bg-muted/5 p-3">
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="min-w-0">
                        <span className="block text-muted-foreground">List price</span>
                        <span className="block truncate text-base font-semibold text-primary">
                          {match.price || 'N/A'}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <span className="block text-muted-foreground">Benchmark</span>
                        <span className="block truncate font-medium text-foreground">
                          {benchmarkAnchorLabel(comparison)}
                        </span>
                      </div>
                    </div>
                    <DealMetricChips
                      comparison={comparison}
                      dealMetrics={dealMetrics}
                      valueContext={match.value_context}
                    />
                    <div>
                      <span className="mb-1.5 block text-[11px] font-medium text-muted-foreground">
                        Features
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {match.reasons_for && match.reasons_for.length > 0 ? (
                          match.reasons_for.slice(0, 3).map((reason, i) => (
                            <Badge key={i} variant="secondary" className="h-5 px-1.5 text-[10px] font-normal">
                              {reason}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">None listed</span>
                        )}
                      </div>
                    </div>
                    <p className="line-clamp-2 text-[11px] text-muted-foreground">
                      {match.value_context?.explanation || match.reasons_for?.[0] || 'Score based on fit and price.'}
                    </p>
                  </div>

                  {/* Additional Context Sections */}
                  {(match.value_context || match.benchmark || comparison || priceEvidence?.warning) && (
                    <div className="space-y-2 bg-muted/5 p-3">
                      {priceEvidence?.warning && (
                        <p className="text-[11px] text-amber-700 dark:text-amber-300">
                          {priceEvidence.warning}
                        </p>
                      )}
                      
                      {comparison && (
                        <div className={`rounded-md border bg-background p-2.5 text-[11px] ${comparisonToneClass(comparison)}`}>
                          <div className="mb-2 flex flex-wrap items-center gap-1.5">
                            <span className="font-semibold">Price comparison</span>
                            <Badge variant="outline" className="bg-background/70 text-[10px]">
                              {comparisonStatusLabel(comparison)}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 gap-1">
                            <div>
                              Listing:{' '}
                              <span className="font-mono font-semibold">
                                {formatCurrency(comparison.listing_price)}
                              </span>
                            </div>
                            <div>
                              Marketplace avg:{' '}
                              <span className="font-mono">
                                {formatCurrency(comparison.used_market_median)}
                              </span>
                            </div>
                            <div>
                              Retail/RRP:{' '}
                              <span className="font-mono">
                                {formatCurrency(comparison.retail_anchor_price)}
                              </span>
                            </div>
                            <div>
                              Vs avg:{' '}
                              <span className="font-mono">
                                {formatDelta(comparison.delta_vs_used_median?.percent)}
                              </span>
                            </div>
                          </div>
                          {comparisonHelpText(comparison) && (
                            <p className="mt-2 text-[11px] text-muted-foreground">
                              {comparisonHelpText(comparison)}
                            </p>
                          )}
                        </div>
                      )}

                      {match.value_context && (
                        <div className="rounded-md border border-primary/20 bg-background p-2.5 text-[11px] shadow-sm">
                          <div className="mb-2 flex flex-wrap items-center gap-1.5">
                            <span className="font-medium">Used-market value</span>
                            <Badge
                              variant={valueBadgeVariant(match.value_context.value_label)}
                              className="text-[10px]"
                            >
                              {match.value_context.value_label}
                            </Badge>
                            <Badge variant="outline" className="text-[10px]">
                              confidence: {match.value_context.value_confidence}
                            </Badge>
                            {typeof match.value_context.value_score === 'number' && (
                              <Badge variant="outline" className="font-mono text-[10px]">
                                value: {match.value_context.value_score}
                              </Badge>
                            )}
                          </div>
                          <div className="grid grid-cols-2 gap-1">
                            <div>
                              Product:{' '}
                              <span className="font-medium">
                                {match.value_context.matched_candidate_name ||
                                  match.value_context.linked_tracked_product_name ||
                                  'linked product'}
                              </span>
                            </div>
                            <div>
                              Source:{' '}
                              <span className="font-mono">
                                {match.value_context.value_source === 'matched_candidate_benchmark'
                                  ? 'matched candidate'
                                  : match.value_context.value_source || 'primary product'}
                              </span>
                            </div>
                            <div>
                              State:{' '}
                              <span className="font-mono">
                                {match.value_context.state.replace(/_/g, ' ')}
                              </span>
                            </div>
                            <div>
                              Fair range:{' '}
                              <span className="font-mono">
                                {typeof match.value_context.fair_low === 'number' &&
                                typeof match.value_context.fair_high === 'number'
                                  ? `${formatCurrency(match.value_context.fair_low)} - ${formatCurrency(match.value_context.fair_high)}`
                                  : 'n/a'}
                              </span>
                            </div>
                            <div>
                              Used median:{' '}
                              <span className="font-mono">
                                {formatCurrency(match.value_context.used_median)}
                              </span>
                            </div>
                            {typeof match.value_context.candidate_match_confidence === 'number' && (
                              <div>
                                Candidate match:{' '}
                                <span className="font-mono">
                                  {Math.round(match.value_context.candidate_match_confidence * 100)}%
                                </span>
                              </div>
                            )}
                          </div>
                          {match.value_context.price_movement_summary && (
                            <p className="mt-2 text-[11px] text-muted-foreground">
                              {match.value_context.price_movement_summary}
                            </p>
                          )}
                          {match.value_context.warnings && match.value_context.warnings.length > 0 && (
                            <p className="mt-2 text-[11px] text-destructive">
                              {match.value_context.warnings.slice(0, 2).join(' ')}
                            </p>
                          )}
                        </div>
                      )}

                      {match.benchmark && (
                        <div className="rounded-md border border-border/60 bg-background p-2.5 text-[11px] shadow-sm">
                          <div className="mb-1 font-medium">New retail benchmark ({match.benchmark.source})</div>
                          <div className="grid grid-cols-2 gap-1">
                            <div>
                              Product: <span className="font-medium">{match.benchmark.matched_product || 'unmatched'}</span>
                            </div>
                            <div>
                              Confidence: <span className="font-mono">{Math.round(match.benchmark.confidence * 100)}%</span>
                            </div>
                            <div>
                              Current: <span className="font-mono">{formatCurrency(match.benchmark.current_price)}</span>
                            </div>
                            <div>
                              30d median: <span className="font-mono">{formatCurrency(match.benchmark.median_30d)}</span>
                            </div>
                            <div>
                              Listing delta: <span className="font-mono">{formatDelta(match.benchmark.listing_delta_pct)}</span>
                            </div>
                            <div>
                              Freshness: <span className="font-mono">
                                {typeof match.benchmark.freshness_hours === 'number'
                                  ? `${Math.round(match.benchmark.freshness_hours)}h`
                                  : 'unknown'}
                              </span>
                            </div>
                          </div>
                          {match.benchmark.review_status && (
                            <div className="mt-2">
                              <Badge variant="outline" className="text-[10px]">
                                review: {match.benchmark.review_status}
                              </Badge>
                            </div>
                          )}
                          {match.benchmark.warning && (
                            <p className="mt-2 text-[11px] text-destructive">{match.benchmark.warning}</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
