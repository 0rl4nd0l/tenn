'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { AlertTriangle, ImageOff, Loader2, Play, RefreshCw, Store, Trash2, X } from 'lucide-react'

import {
  calibrateMarketplaceProduct,
  syncEbaySoldData,
  createMarketplaceMission,
  deleteMarketplaceMission,
  linkMarketplaceMissionTrackedProduct,
  listMarketplaceMatches,
  getMarketplaceScanJob,
  getMarketplaceBrowserHealth,
  launchMarketplaceBrowser,
  listMarketplaceMissions,
  listMarketplaceScanJobs,
  listMarketplaceTrackedProducts,
  refreshMarketplaceBenchmarks,
  stopMarketplaceScanJob,
  type MarketplaceBenchmarkState,
  type MarketplaceCandidateProduct,
  type MarketplaceMatch,
  type MarketplaceBrowserHealth,
  type MarketplaceMission,
  type MarketplaceRequirementProfile,
  type MarketplaceScanJob,
  type MarketplaceTrackedProduct,
  triggerMarketplaceScan,
  unlinkMarketplaceMissionTrackedProduct,
  updateMarketplaceMission,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { MarketplaceAssistant } from './marketplace-assistant'
import { useCockpitStore } from '@/lib/cockpit-store'
import {
  comparisonHelpText,
  comparisonNeedsBenchmarkSetup,
  comparisonStatusLabel,
} from './price-comparison'
import { priceEvidenceForMatch, priceSourceLabel } from './price-evidence'
import { cn } from '@/lib/utils'

interface MarketplaceMissionScreenProps {
  apiKey: string
}

type MissionFormState = {
  name: string
  brief: string
  includeKeywords: string
  excludeKeywords: string
  preferredBrands: string
  locationNames: string
  priceMax: string
  scanIntervalMinutes: string
  autoScanEnabled: boolean
  aggressiveAlerting: boolean
}

type BenchmarkSortMode = 'mission' | 'missing' | 'newest' | 'value' | 'confidence'

const DEFAULT_FORM: MissionFormState = {
  name: '',
  brief: '',
  includeKeywords: '',
  excludeKeywords: '',
  preferredBrands: '',
  locationNames: '',
  priceMax: '',
  scanIntervalMinutes: '15',
  autoScanEnabled: true,
  aggressiveAlerting: false,
}

function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function csvFromValue(value: unknown): string {
  if (!Array.isArray(value)) {
    return ''
  }
  return value
    .map((item) => String(item ?? '').trim())
    .filter(Boolean)
    .join(', ')
}

function boolFromConfig(config: Record<string, unknown> | undefined, key: string): boolean {
  return Boolean(config?.[key])
}

function numberStringFromConfig(
  config: Record<string, unknown> | undefined,
  key: string,
  fallback = '',
): string {
  const raw = config?.[key]
  if (raw == null || raw === '') return fallback
  const parsed = Number(raw)
  if (!Number.isFinite(parsed)) return fallback
  return String(parsed)
}

function missionFormFromRecord(mission: MarketplaceMission): MissionFormState {
  const hard = (mission.hard_filters || {}) as Record<string, unknown>
  const soft = (mission.soft_preferences || {}) as Record<string, unknown>
  const scan = (mission.scan_config || {}) as Record<string, unknown>

  return {
    name: mission.name,
    brief: mission.brief,
    includeKeywords: csvFromValue(hard.include_keywords),
    excludeKeywords: csvFromValue(hard.exclude_keywords),
    preferredBrands: csvFromValue(soft.preferred_brands),
    locationNames: csvFromValue(hard.location_names),
    priceMax: numberStringFromConfig(hard, 'price_max'),
    scanIntervalMinutes: numberStringFromConfig(scan, 'scan_interval_minutes', '15'),
    autoScanEnabled: mission.status === 'active',
    aggressiveAlerting: boolFromConfig(scan, 'aggressive_alerting'),
  }
}

function marketplacePayloadFromForm(
  form: MissionFormState,
  existingMission?: MarketplaceMission,
): Record<string, unknown> {
  const hard = ((existingMission?.hard_filters || {}) as Record<string, unknown>) ?? {}
  const soft = ((existingMission?.soft_preferences || {}) as Record<string, unknown>) ?? {}
  const search = ((existingMission?.search_config || {}) as Record<string, unknown>) ?? {}
  const scan = ((existingMission?.scan_config || {}) as Record<string, unknown>) ?? {}

  return {
    name: form.name,
    brief: form.brief,
    status: form.autoScanEnabled ? 'active' : 'paused',
    category_hint: existingMission?.category_hint ?? null,
    hard_filters: {
      ...hard,
      include_keywords: splitCsv(form.includeKeywords),
      exclude_keywords: splitCsv(form.excludeKeywords),
      location_names: splitCsv(form.locationNames),
      price_max: form.priceMax ? Number(form.priceMax) : null,
    },
    soft_preferences: {
      ...soft,
      preferred_brands: splitCsv(form.preferredBrands),
    },
    search_config: {
      ...search,
    },
    scan_config: {
      ...scan,
      scan_interval_minutes: form.scanIntervalMinutes ? Number(form.scanIntervalMinutes) : 15,
      aggressive_alerting: form.aggressiveAlerting,
    },
  }
}

function formatClock(value: string | null | undefined): string {
  if (!value) return 'never'
  try {
    return new Date(value).toLocaleString('en-AU', {
      hour12: false,
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function healthBadgeVariant(
  status: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'ready') return 'default'
  if (status === 'challenge_detected') return 'destructive'
  if (status === 'browser_not_running' || status === 'desktop_session_missing' || status === 'browser_unavailable') return 'destructive'
  return 'outline'
}

function browserHealthAllowsScan(health: MarketplaceBrowserHealth | null): boolean {
  if (!health) return false
  if (typeof health.scan_allowed === 'boolean') return health.scan_allowed
  return health.status === 'ready' && !health.challenge_detected
}

function browserHealthScanBlocker(health: MarketplaceBrowserHealth | null): string {
  if (!health) return 'Marketplace browser health is unavailable.'
  if (health.scan_blocker) return health.scan_blocker
  if (health.challenge_detected || health.status === 'challenge_detected') {
    return health.detail || 'Resolve the Facebook checkpoint or challenge before scanning.'
  }
  return health.detail || `Marketplace browser status is ${health.status}.`
}

function scanBadgeVariant(
  status: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'success') return 'default'
  if (status === 'running' || status === 'queued') return 'secondary'
  if (status === 'cancelled') return 'outline'
  if (status === 'failed') return 'destructive'
  return 'outline'
}

function formatProgress(value: number | null | undefined): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) return null
  return `${Math.max(0, Math.min(100, Math.round(value)))}%`
}

function clampProgress(value: number | null | undefined): number {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0
  return Math.max(0, Math.min(100, value))
}

function pickScanJobId(
  jobs: MarketplaceScanJob[],
  preferredJobId: string | null,
): string | null {
  const activeJob = jobs.find((job) => job.status === 'running' || job.status === 'queued')
  if (preferredJobId) {
    const preferred = jobs.find((job) => job.job_id === preferredJobId)
    if (preferred) {
      const preferredIsActive =
        preferred.status === 'running' || preferred.status === 'queued'
      if (preferredIsActive || !activeJob) {
        return preferredJobId
      }
    }
  }
  return activeJob?.job_id ?? jobs[0]?.job_id ?? null
}

function scanOutputPlaceholder(job: MarketplaceScanJob | null): string {
  if (!job) return 'Select a Marketplace scan to inspect live output.'
  if (job.status === 'queued') return 'Scan is queued. Output will appear when the worker starts.'
  if (job.status === 'running') return 'Scanner is running. Waiting for stdout...'
  if (job.status === 'failed') return 'Scan failed, but no stderr/stdout was captured.'
  return 'Scan completed, but no stdout was captured.'
}

function missionScanIntervalMinutes(mission: MarketplaceMission): number {
  const raw = Number((mission.scan_config || {}).scan_interval_minutes)
  if (!Number.isFinite(raw) || raw <= 0) {
    return 15
  }
  return Math.round(raw)
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

function trackedProductDisplayName(product: MarketplaceTrackedProduct | null | undefined): string {
  if (!product) return 'Unknown tracked product'
  const parts = [product.brand, product.model_family, product.variant]
    .map((part) => String(part ?? '').trim())
    .filter(Boolean)
  return parts.length > 0 ? parts.join(' ') : product.canonical_key || product.tracked_product_id
}

function missionLinkedProduct(mission: MarketplaceMission): MarketplaceTrackedProduct | null {
  return mission.primary_tracked_product?.tracked_product ?? null
}

function missionLinkedProductId(mission: MarketplaceMission): string {
  return mission.primary_tracked_product?.tracked_product_id ?? ''
}

function missionRequirementProfile(mission: MarketplaceMission): MarketplaceRequirementProfile | null {
  return mission.requirement_profile ?? null
}

function isRequirementDrivenMission(mission: MarketplaceMission): boolean {
  return missionRequirementProfile(mission)?.mode === 'requirement_driven'
}

function constraintLabel(item: Record<string, unknown>): string {
  const field = String(item.field ?? '').replace(/_/g, ' ')
  const operator = String(item.operator ?? '=')
  const value = item.value == null ? '' : String(item.value)
  const unit = item.unit == null ? '' : ` ${String(item.unit)}`
  return [field, operator, `${value}${unit}`].filter(Boolean).join(' ')
}

function requirementSummary(profile: MarketplaceRequirementProfile | null): string {
  if (!profile) return 'n/a'
  const parts = [
    profile.category,
    profile.intended_use ? profile.intended_use.replace(/_/g, ' ') : null,
    ...(profile.hard_constraints ?? []).slice(0, 2).map(constraintLabel),
  ]
    .map((part) => String(part ?? '').trim())
    .filter(Boolean)
  return parts.length > 0 ? parts.join(' · ') : profile.mode
}

function candidateProductName(candidate: MarketplaceCandidateProduct): string {
  return candidate.tracked_product
    ? trackedProductDisplayName(candidate.tracked_product)
    : candidate.candidate_key
}

function benchmarkStateBadgeVariant(
  state: MarketplaceBenchmarkState | null | undefined,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (!state || state.status === 'value_unavailable' || state.status === 'no_snapshot') {
    return 'outline'
  }
  if (state.freshness_status === 'stale' || state.status === 'stale_benchmark') {
    return 'secondary'
  }
  if (state.status === 'scored' || state.status === 'ready') {
    return 'default'
  }
  return 'outline'
}

function benchmarkStateLabel(state: MarketplaceBenchmarkState | null | undefined): string {
  if (!state) return 'benchmark unavailable'
  if (state.status === 'scored' || state.status === 'ready') {
    return state.freshness_status || 'ready'
  }
  return state.status.replace(/_/g, ' ')
}

function fairRangeLabel(state: MarketplaceBenchmarkState | null | undefined): string {
  if (!state) return 'n/a'
  if (typeof state.fair_low === 'number' && typeof state.fair_high === 'number') {
    return `${formatCurrency(state.fair_low)} - ${formatCurrency(state.fair_high)}`
  }
  return 'n/a'
}

function benchmarkFreshnessLabel(hours: number | null | undefined): string {
  if (typeof hours !== 'number' || Number.isNaN(hours)) return 'unknown'
  if (hours <= 24) return 'fresh'
  if (hours <= 24 * 7) return 'stale'
  return 'old'
}

function listingMediaForMatch(match: MarketplaceMatch): string[] {
  const raw = Array.isArray(match.listing_media) ? match.listing_media : []
  const cleaned = raw
    .map((item) => String(item ?? '').trim())
    .filter((item) => /^https?:\/\//i.test(item))
  if (cleaned.length > 0) {
    return cleaned
  }
  if (match.screenshot_path && /^https?:\/\//i.test(match.screenshot_path)) {
    return [match.screenshot_path]
  }
  return []
}

function missionNameForMatch(match: MarketplaceMatch): string {
  const name = String(match.mission_name ?? '').trim()
  if (name) return name
  const id = String(match.mission_id ?? '').trim()
  return id || 'Unknown mission'
}

function timeValue(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function benchmarkConfidence(match: MarketplaceMatch): number {
  const benchmarkConfidenceValue = match.benchmark?.confidence
  if (typeof benchmarkConfidenceValue === 'number' && Number.isFinite(benchmarkConfidenceValue)) {
    return benchmarkConfidenceValue
  }
  const matchConfidence = match.confidence
  if (typeof matchConfidence === 'number' && Number.isFinite(matchConfidence)) {
    return matchConfidence
  }
  return -1
}

function listingPriceLabel(match: MarketplaceMatch): string {
  const evidence = priceEvidenceForMatch(match)
  const text = String(match.price || evidence?.resolved_price_text || '').trim()
  if (text) return text
  const numeric = match.price_value ?? evidence?.resolved_price_value
  if (typeof numeric === 'number' && Number.isFinite(numeric)) {
    return formatCurrency(numeric)
  }
  return 'Missing'
}

function benchmarkMissingReasons(match: MarketplaceMatch): string[] {
  const benchmark = match.benchmark ?? null
  const comparison = match.price_comparison ?? null
  const evidence = priceEvidenceForMatch(match)
  const reasons: string[] = []
  const hasListingPrice =
    Boolean(String(match.price || evidence?.resolved_price_text || '').trim()) ||
    (typeof match.price_value === 'number' && Number.isFinite(match.price_value)) ||
    (typeof evidence?.resolved_price_value === 'number' && Number.isFinite(evidence.resolved_price_value))

  if (comparison?.comparison_state === 'missing_listing_price' || !hasListingPrice) {
    reasons.push('Listing price missing')
  }
  if (comparisonNeedsBenchmarkSetup(comparison)) {
    reasons.push(comparisonStatusLabel(comparison))
    return reasons
  }
  if (!benchmark) {
    reasons.push('Benchmark overlay missing')
    return reasons
  }
  if (!benchmark.matched_product) {
    reasons.push('No confident product match')
  }
  if (benchmark.current_price == null) {
    reasons.push('Current retail price missing')
  }
  if (benchmark.median_30d == null) {
    reasons.push('30d median missing')
  }
  if (benchmark.listing_delta_pct == null) {
    reasons.push('Listing delta unavailable')
  }
  return reasons
}

function benchmarkNeedsReview(match: MarketplaceMatch): boolean {
  const benchmark = match.benchmark ?? null
  if (!benchmark) return true
  if (benchmark.low_confidence) return true
  return /pending|review/i.test(benchmark.review_status || '')
}

function benchmarkReviewLabel(match: MarketplaceMatch): string {
  if (comparisonNeedsBenchmarkSetup(match.price_comparison)) return 'needs setup'
  const benchmark = match.benchmark ?? null
  if (!benchmark) return 'benchmark missing'
  if (benchmark.low_confidence || /pending|review/i.test(benchmark.review_status || '')) {
    return 'needs review'
  }
  if (benchmarkMissingReasons(match).length > 0) {
    return 'incomplete'
  }
  return 'benchmarked'
}

function benchmarkReviewBadgeVariant(
  match: MarketplaceMatch,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  const benchmark = match.benchmark ?? null
  if (!benchmark) return 'outline'
  if (benchmark.low_confidence || /pending|review/i.test(benchmark.review_status || '')) {
    return 'destructive'
  }
  if (benchmarkMissingReasons(match).length > 0) return 'secondary'
  return 'default'
}

function sortBenchmarkMatches(
  matches: MarketplaceMatch[],
  sortMode: BenchmarkSortMode,
): MarketplaceMatch[] {
  return [...matches].sort((left, right) => {
    if (sortMode === 'mission') {
      const missionCompare = missionNameForMatch(left).localeCompare(missionNameForMatch(right))
      if (missionCompare !== 0) return missionCompare
      return timeValue(right.captured_at) - timeValue(left.captured_at)
    }
    if (sortMode === 'missing') {
      const missingCompare =
        benchmarkMissingReasons(right).length - benchmarkMissingReasons(left).length
      if (missingCompare !== 0) return missingCompare
      const reviewCompare = Number(benchmarkNeedsReview(right)) - Number(benchmarkNeedsReview(left))
      if (reviewCompare !== 0) return reviewCompare
      return timeValue(right.captured_at) - timeValue(left.captured_at)
    }
    if (sortMode === 'value') {
      const leftDelta = left.benchmark?.listing_delta_pct
      const rightDelta = right.benchmark?.listing_delta_pct
      const safeLeftDelta = typeof leftDelta === 'number' && Number.isFinite(leftDelta) ? leftDelta : Infinity
      const safeRightDelta = typeof rightDelta === 'number' && Number.isFinite(rightDelta) ? rightDelta : Infinity
      if (safeLeftDelta !== safeRightDelta) return safeLeftDelta - safeRightDelta
      return timeValue(right.captured_at) - timeValue(left.captured_at)
    }
    if (sortMode === 'confidence') {
      const confidenceCompare = benchmarkConfidence(right) - benchmarkConfidence(left)
      if (confidenceCompare !== 0) return confidenceCompare
      return timeValue(right.captured_at) - timeValue(left.captured_at)
    }
    return timeValue(right.captured_at) - timeValue(left.captured_at)
  })
}

export function MarketplaceMissionScreen({ apiKey }: MarketplaceMissionScreenProps) {
  const { preferences } = useCockpitStore()
  const isIPhoneScale = preferences.iphoneScale

  const [browserHealth, setBrowserHealth] = useState<MarketplaceBrowserHealth | null>(null)
  const [missions, setMissions] = useState<MarketplaceMission[]>([])
  const [scanJobs, setScanJobs] = useState<MarketplaceScanJob[]>([])
  const [benchmarkMatches, setBenchmarkMatches] = useState<MarketplaceMatch[]>([])
  const [trackedProducts, setTrackedProducts] = useState<MarketplaceTrackedProduct[]>([])
  const [trackedProductsLoaded, setTrackedProductsLoaded] = useState(false)
  const [trackedProductsLoading, setTrackedProductsLoading] = useState(false)
  const [selectedScanJobId, setSelectedScanJobId] = useState<string | null>(null)
  const [selectedScanJob, setSelectedScanJob] = useState<MarketplaceScanJob | null>(null)
  const [scanOutputLoading, setScanOutputLoading] = useState(false)
  const [scanOutputError, setScanOutputError] = useState<string | null>(null)
  const [form, setForm] = useState<MissionFormState>(DEFAULT_FORM)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [missionIntervalDrafts, setMissionIntervalDrafts] = useState<Record<string, string>>({})
  const [savingMissionId, setSavingMissionId] = useState<string | null>(null)
  const [editingMissionId, setEditingMissionId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<MissionFormState | null>(null)
  const [deletingMissionId, setDeletingMissionId] = useState<string | null>(null)
  const [linkingMissionId, setLinkingMissionId] = useState<string | null>(null)
  const [calibratingProductId, setCalibratingProductId] = useState<string | null>(null)
  const [syncingEbayProductId, setSyncingEbayProductId] = useState<string | null>(null)
  const [stoppingJobId, setStoppingJobId] = useState<string | null>(null)
  const [refreshingBenchmarks, setRefreshingBenchmarks] = useState(false)
  const [benchmarkSortMode, setBenchmarkSortMode] = useState<BenchmarkSortMode>('mission')
  const selectedScanJobIdRef = useRef<string | null>(null)
  const desktopSessionMissing = browserHealth?.status === 'desktop_session_missing'
  const scanAllowed = browserHealthAllowsScan(browserHealth)
  const scanBlocked = Boolean(browserHealth && !scanAllowed)
  const scanBlocker = browserHealthScanBlocker(browserHealth)
  const challengeScanBlocked =
    browserHealth?.status === 'challenge_detected' || Boolean(browserHealth?.challenge_detected)
  const headlessProbeBlocked =
    browserHealth?.status === 'browser_unavailable' &&
    /headless mode|timed out during cdp attach/i.test(browserHealth?.detail || '')

  const loadSelectedScanJob = useCallback(
    async (jobId: string | null) => {
      if (!jobId) {
        setSelectedScanJob(null)
        setScanOutputError(null)
        setScanOutputLoading(false)
        return
      }
      setScanOutputLoading(true)
      try {
        const job = await getMarketplaceScanJob(apiKey, jobId)
        setSelectedScanJob(job)
        setScanOutputError(null)
      } catch (scanError) {
        setSelectedScanJob(null)
        setScanOutputError(
          scanError instanceof Error ? scanError.message : 'Failed to load scan output',
        )
      } finally {
        setScanOutputLoading(false)
      }
    },
    [apiKey],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [healthResult, missionsResult, jobsResult, matchesResult] = await Promise.allSettled([
        getMarketplaceBrowserHealth(apiKey),
        listMarketplaceMissions(apiKey),
        listMarketplaceScanJobs(apiKey),
        listMarketplaceMatches(apiKey),
      ])
      if (missionsResult.status !== 'fulfilled') {
        throw missionsResult.reason
      }

      const missionItems = missionsResult.value
      setMissions(missionItems)

      if (healthResult.status === 'fulfilled') {
        setBrowserHealth(healthResult.value)
      } else {
        setBrowserHealth(null)
      }

      const jobs = jobsResult.status === 'fulfilled' ? jobsResult.value : []
      setScanJobs(jobs)

      const matches =
        matchesResult.status === 'fulfilled'
          ? matchesResult.value
          : []
      const safeMatches = Array.isArray(matches) ? matches : []
      setBenchmarkMatches(safeMatches.slice(0, 18))
      setMissionIntervalDrafts((current) => {
        const next = { ...current }
        for (const mission of missionItems) {
          next[mission.mission_id] = String(missionScanIntervalMinutes(mission))
        }
        return next
      })
      const nextSelectedJobId = pickScanJobId(jobs, selectedScanJobIdRef.current)
      selectedScanJobIdRef.current = nextSelectedJobId
      setSelectedScanJobId(nextSelectedJobId)
      await loadSelectedScanJob(nextSelectedJobId)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load Marketplace state')
    } finally {
      setLoading(false)
    }
  }, [apiKey, loadSelectedScanJob])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const hasActiveScan = scanJobs.some((job) => job.status === 'running' || job.status === 'queued')
    const interval = window.setInterval(
      () => {
        void load()
      },
      hasActiveScan ? 3_000 : 15_000,
    )
    return () => window.clearInterval(interval)
  }, [apiKey, scanJobs, load])

  async function handleCreateMission() {
    if (splitCsv(form.locationNames).length === 0) {
      setError('Mission location is required. Add at least one location before creating the mission.')
      setNotice(null)
      return
    }
    setCreating(true)
    setError(null)
    setNotice(null)
    try {
      const mission = await createMarketplaceMission(apiKey, marketplacePayloadFromForm(form))
      setForm(DEFAULT_FORM)
      if (scanBlocked) {
        setNotice(`Mission "${mission.name}" created. Scan skipped: ${scanBlocker}`)
        await load()
      } else {
        setNotice(`Mission "${mission.name}" created. Starting initial scan...`)
        await handleTriggerScan(mission.mission_id)
      }
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Failed to create Marketplace mission')
    } finally {
      setCreating(false)
    }
  }

  async function handleLaunchBrowser() {
    setError(null)
    setNotice(null)
    try {
      await launchMarketplaceBrowser(apiKey)
      setNotice('Browser launch request sent.')
      await load()
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : 'Failed to launch Marketplace browser')
    }
  }

  async function handleRefreshBenchmarks() {
    setRefreshingBenchmarks(true)
    setError(null)
    setNotice(null)
    try {
      const summary = await refreshMarketplaceBenchmarks(apiKey)
      const live = typeof summary.live_observations_added === 'number' ? summary.live_observations_added : 0
      const fallback =
        typeof summary.fallback_observations_added === 'number' ? summary.fallback_observations_added : 0
      const failureCount = Array.isArray(summary.fetch_failures) ? summary.fetch_failures.length : 0
      setNotice(
        `Centre Com benchmark refresh complete: ${summary.price_observations_added} observations (${live} live, ${fallback} fallback).${failureCount > 0 ? ` ${failureCount} live fetches failed; fallback benchmarks were applied.` : ''}`,
      )
      await load()
    } catch (refreshError) {
      setError(
        refreshError instanceof Error ? refreshError.message : 'Failed to refresh Centre Com benchmarks',
      )
    } finally {
      setRefreshingBenchmarks(false)
    }
  }

  async function ensureTrackedProductsLoaded() {
    if (trackedProductsLoaded || trackedProductsLoading) {
      return
    }
    setTrackedProductsLoading(true)
    setError(null)
    try {
      const products = await listMarketplaceTrackedProducts(apiKey)
      setTrackedProducts(products)
      setTrackedProductsLoaded(true)
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Failed to load Marketplace tracked products',
      )
    } finally {
      setTrackedProductsLoading(false)
    }
  }

  async function handleTrackedProductLink(mission: MarketplaceMission, trackedProductId: string) {
    const currentId = missionLinkedProductId(mission)
    if (trackedProductId === currentId) {
      return
    }

    setLinkingMissionId(mission.mission_id)
    setError(null)
    setNotice(null)
    try {
      if (trackedProductId) {
        const product = trackedProducts.find((item) => item.tracked_product_id === trackedProductId)
        await linkMarketplaceMissionTrackedProduct(apiKey, mission.mission_id, trackedProductId)
        setNotice(`Linked ${mission.name} to ${trackedProductDisplayName(product)}.`)
      } else {
        await unlinkMarketplaceMissionTrackedProduct(apiKey, mission.mission_id)
        setNotice(`Unlinked tracked product from ${mission.name}.`)
      }
      await load()
    } catch (linkError) {
      setError(
        linkError instanceof Error ? linkError.message : 'Tracked product link update failed',
      )
    } finally {
      setLinkingMissionId(null)
    }
  }

  async function handleCalibrateProduct(trackedProductId: string) {
    if (!trackedProductId) return
    setCalibratingProductId(trackedProductId)
    setError(null)
    setNotice(null)
    try {
      const queued = await calibrateMarketplaceProduct(apiKey, trackedProductId)
      if (queued.job_id) {
        selectedScanJobIdRef.current = queued.job_id
        setSelectedScanJobId(queued.job_id)
      }
      setNotice('Benchmark calibration triggered.')
      await load()
    } catch (calError) {
      setError(calError instanceof Error ? calError.message : 'Calibration failed')
    } finally {
      setCalibratingProductId(null)
    }
  }

  async function handleSyncEbay(trackedProductId: string) {
    if (!trackedProductId) return
    setSyncingEbayProductId(trackedProductId)
    setError(null)
    setNotice(null)
    try {
      const stats = await syncEbaySoldData(apiKey, trackedProductId)
      setNotice(`eBay sync complete: Ingested ${stats.observations_ingested} sold items.`)
      await load()
    } catch (syncError) {
      setError(syncError instanceof Error ? syncError.message : 'eBay sync failed')
    } finally {
      setSyncingEbayProductId(null)
    }
  }

  async function handleTriggerScan(missionId: string) {
    setError(null)
    setNotice(null)
    if (scanBlocked) {
      setError(scanBlocker)
      return
    }
    try {
      const queued = await triggerMarketplaceScan(apiKey, missionId)
      if (queued.job_id) {
        selectedScanJobIdRef.current = queued.job_id
        setSelectedScanJobId(queued.job_id)
      }
      setNotice('Scan triggered successfully.')
      await load()
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : 'Failed to trigger Marketplace scan')
    }
  }

  async function handleSelectScanJob(jobId: string) {
    selectedScanJobIdRef.current = jobId
    setSelectedScanJobId(jobId)
    setSelectedScanJob(null)
    setScanOutputError(null)
    await loadSelectedScanJob(jobId)
  }

  function handleEditMission(mission: MarketplaceMission) {
    setEditingMissionId(mission.mission_id)
    setEditForm(missionFormFromRecord(mission))
    setError(null)
    setNotice(null)
  }

  function handleCancelMissionEdit() {
    setEditingMissionId(null)
    setEditForm(null)
  }

  async function handleSaveMissionEdit(mission: MarketplaceMission) {
    if (!editForm) return
    if (splitCsv(editForm.locationNames).length === 0) {
      setError('Mission location is required. Add at least one location before saving.')
      setNotice(null)
      return
    }
    setSavingMissionId(mission.mission_id)
    setError(null)
    setNotice(null)
    try {
      await updateMarketplaceMission(
        apiKey,
        mission.mission_id,
        marketplacePayloadFromForm(editForm, mission),
      )
      setNotice(`Saved changes for ${mission.name}.`)
      setEditingMissionId(null)
      setEditForm(null)
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Mission update failed')
    } finally {
      setSavingMissionId(null)
    }
  }

  async function handleDeleteMission(mission: MarketplaceMission) {
    const missionHasActiveScan = scanJobs.some(
      (job) =>
        job.mission_id === mission.mission_id &&
        (job.status === 'queued' || job.status === 'running'),
    )
    if (missionHasActiveScan) {
      setError('Mission has an active scan. Cancel the running scan before deleting this mission.')
      setNotice(null)
      return
    }

    const confirmed = window.confirm(
      `Delete mission "${mission.name}"? This removes its mission, match, and alert records from Marketplace UI.`,
    )
    if (!confirmed) {
      return
    }

    setDeletingMissionId(mission.mission_id)
    setError(null)
    setNotice(null)
    try {
      await deleteMarketplaceMission(apiKey, mission.mission_id)
      if (editingMissionId === mission.mission_id) {
        setEditingMissionId(null)
        setEditForm(null)
      }
      setNotice(`Deleted mission ${mission.name}.`)
      await load()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Mission delete failed')
    } finally {
      setDeletingMissionId(null)
    }
  }

  async function handleAutoScanToggle(mission: MarketplaceMission, enabled: boolean) {
    setSavingMissionId(mission.mission_id)
    setError(null)
    setNotice(null)
    try {
      await updateMarketplaceMission(apiKey, mission.mission_id, {
        status: enabled ? 'active' : 'paused',
      })
      setNotice(enabled ? 'Auto scan enabled.' : 'Auto scan paused.')
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Mission update failed')
    } finally {
      setSavingMissionId(null)
    }
  }

  async function handleSaveCadence(mission: MarketplaceMission) {
    const raw = missionIntervalDrafts[mission.mission_id] ?? String(missionScanIntervalMinutes(mission))
    const intervalMinutes = Number(raw)
    if (!Number.isFinite(intervalMinutes) || intervalMinutes <= 0) {
      setError('Scan cadence must be a positive number of minutes.')
      return
    }

    setSavingMissionId(mission.mission_id)
    setError(null)
    setNotice(null)
    try {
      await updateMarketplaceMission(apiKey, mission.mission_id, {
        scan_config: {
          ...(mission.scan_config || {}),
          scan_interval_minutes: Math.round(intervalMinutes),
        },
      })
      setNotice(`Auto scan cadence updated to every ${Math.round(intervalMinutes)} minutes.`)
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Cadence update failed')
    } finally {
      setSavingMissionId(null)
    }
  }

  async function handleStopScan(jobId: string) {
    setStoppingJobId(jobId)
    setError(null)
    setNotice(null)
    try {
      const queued = await stopMarketplaceScanJob(apiKey, jobId)
      setNotice(
        queued.status === 'cancelling'
          ? 'Scan cancellation requested.'
          : `Scan status: ${queued.status}.`,
      )
      await load()
    } catch (stopError) {
      setError(stopError instanceof Error ? stopError.message : 'Failed to stop Marketplace scan')
    } finally {
      setStoppingJobId(null)
    }
  }

  function handleAssistantScanQueued(jobId: string | null) {
    if (!jobId) {
      return
    }
    selectedScanJobIdRef.current = jobId
    setSelectedScanJobId(jobId)
  }

  const sortedBenchmarkMatches = sortBenchmarkMatches(benchmarkMatches, benchmarkSortMode)
  const benchmarkMissingCount = benchmarkMatches.filter(
    (match) => benchmarkMissingReasons(match).length > 0,
  ).length
  const benchmarkReviewCount = benchmarkMatches.filter(benchmarkNeedsReview).length

  return (
    <div className="h-full overflow-auto">
      <div className={cn(
        "mx-auto max-w-5xl flex flex-col",
        isIPhoneScale ? "p-3 gap-3" : "p-6 gap-6"
      )}>
        <div className={cn(
          "flex items-center justify-between gap-3",
          isIPhoneScale ? "flex-col items-start" : "flex-wrap"
        )}>
          <div>
            <h2 className="text-xl font-semibold">Marketplace Missions</h2>
            <p className="text-sm text-muted-foreground">
              Configure and monitor automated Marketplace scan missions.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleRefreshBenchmarks()}
              disabled={refreshingBenchmarks}
            >
              {refreshingBenchmarks && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Refresh Benchmarks
            </Button>
            <Button variant="secondary" size="sm" onClick={handleLaunchBrowser}>
              Launch Browser
            </Button>
          </div>
        </div>

        {(error || notice) && (
          <div className={`rounded-lg border p-4 text-sm ${
            error ? 'border-destructive/50 bg-destructive/10 text-destructive' : 'border-primary/50 bg-primary/10 text-primary'
          }`}>
            {error || notice}
          </div>
        )}

        {desktopSessionMissing && (
          <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-medium">Launch Browser needs a graphical desktop session.</p>
              {browserHealth?.detail && <p>{browserHealth.detail}</p>}
              <p className="text-xs text-destructive/80">
                Start <span className="font-mono">marketplace_browser_helper.py</span> from a
                desktop login on this machine, or launch Chrome manually with remote debugging on
                port 9222, then refresh.
              </p>
            </div>
          </div>
        )}

        {headlessProbeBlocked && (
          <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-medium">Headless Chrome is exposing CDP, but Marketplace probing is not attachable yet.</p>
              {browserHealth?.detail && <p>{browserHealth.detail}</p>}
              <p className="text-xs text-destructive/80">
                The current Marketplace scanner still needs a CDP session that Playwright can attach to. This headless Chrome session is visible on port 9222, but Cockpit cannot scan until that attach step succeeds.
              </p>
            </div>
          </div>
        )}

        {challengeScanBlocked && (
          <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-medium">Facebook checkpoint is blocking Marketplace scans.</p>
              <p>{scanBlocker}</p>
              <p className="text-xs text-destructive/80">
                Open the Marketplace browser, clear the checkpoint or challenge, then refresh browser health before scanning.
              </p>
            </div>
          </div>
        )}

        <MarketplaceAssistant
          apiKey={apiKey}
          browserHealth={browserHealth}
          onMarketplaceStateChange={load}
          onScanQueued={handleAssistantScanQueued}
        />

        <div className={cn(
          "grid gap-6",
          isIPhoneScale ? "grid-cols-1" : "lg:grid-cols-[1fr_380px]"
        )}>
          <div className="space-y-6">
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Store className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">Active Missions</CardTitle>
                </div>
                <CardDescription>Missions currently configured for automated scanning.</CardDescription>
              </CardHeader>
              <CardContent>
                {missions.length === 0 ? (
                  <p className="py-12 text-center text-sm text-muted-foreground italic">No missions configured yet.</p>
                ) : (
                  <div className="grid gap-6 xl:grid-cols-2">
                    {missions.map((mission) => {
                      const linkedProduct = missionLinkedProduct(mission)
                      const linkedProductId = missionLinkedProductId(mission)
                      const benchmarkState = mission.benchmark_state ?? null
                      const requirementProfile = missionRequirementProfile(mission)
                      const candidateProducts = mission.candidate_products ?? []
                      const linkedProductInOptions = trackedProducts.some(
                        (product) => product.tracked_product_id === linkedProductId,
                      )

                      if (editingMissionId === mission.mission_id && editForm) {
                        return (
                          <Card key={mission.mission_id} className="border-primary/40 bg-primary/5 shadow-sm">
                            <CardHeader className="p-5 pb-3">
                              <CardTitle className="text-base font-semibold">Edit Mission</CardTitle>
                            </CardHeader>
                            <CardContent className="px-5 pb-5 space-y-4">
                              <div className="space-y-3">
                                <div className="space-y-1.5">
                                  <label className="text-xs font-medium text-muted-foreground">Name</label>
                                  <Input
                                    value={editForm.name}
                                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                    className="h-9 text-sm"
                                    aria-label={`Edit name for ${mission.name}`}
                                  />
                                </div>
                                <div className="space-y-1.5">
                                  <label className="text-xs font-medium text-muted-foreground">Brief / Instructions</label>
                                  <Textarea
                                    value={editForm.brief}
                                    onChange={(e) => setEditForm({ ...editForm, brief: e.target.value })}
                                    className="min-h-[80px] text-sm"
                                    aria-label={`Edit brief for ${mission.name}`}
                                  />
                                </div>
                                <div className="grid gap-3 sm:grid-cols-2">
                                  <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Include Keywords (CSV)</label>
                                    <Input
                                      value={editForm.includeKeywords}
                                      onChange={(e) => setEditForm({ ...editForm, includeKeywords: e.target.value })}
                                      placeholder="e.g. RTX 3090, 4090"
                                      className="h-9 text-sm"
                                      aria-label={`Edit include keywords for ${mission.name}`}
                                    />
                                  </div>
                                  <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Exclude Keywords (CSV)</label>
                                    <Input
                                      value={editForm.excludeKeywords}
                                      onChange={(e) => setEditForm({ ...editForm, excludeKeywords: e.target.value })}
                                      placeholder="e.g. fake, homage"
                                      className="h-9 text-sm"
                                      aria-label={`Edit exclude keywords for ${mission.name}`}
                                    />
                                  </div>
                                </div>
                                <div className="grid gap-3 sm:grid-cols-2">
                                  <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Preferred Brands (CSV)</label>
                                    <Input
                                      value={editForm.preferredBrands}
                                      onChange={(e) => setEditForm({ ...editForm, preferredBrands: e.target.value })}
                                      placeholder="e.g. MSI, ASUS, Gigabyte"
                                      className="h-9 text-sm"
                                      aria-label={`Edit preferred brands for ${mission.name}`}
                                    />
                                  </div>
                                  <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Locations (CSV)</label>
                                    <Input
                                      value={editForm.locationNames}
                                      onChange={(e) => setEditForm({ ...editForm, locationNames: e.target.value })}
                                      placeholder="e.g. Melbourne, Richmond"
                                      className="h-9 text-sm"
                                      aria-label={`Edit locations for ${mission.name}`}
                                    />
                                  </div>
                                  <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Max Price</label>
                                    <Input
                                      type="number"
                                      value={editForm.priceMax}
                                      onChange={(e) => setEditForm({ ...editForm, priceMax: e.target.value })}
                                      placeholder="e.g. 1500"
                                      className="h-9 text-sm"
                                      aria-label={`Edit max price for ${mission.name}`}
                                    />
                                  </div>
                                </div>
                                <div className="grid gap-3 sm:grid-cols-2">
                                  <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-muted-foreground">Scan Cadence (min)</label>
                                    <Input
                                      type="number"
                                      value={editForm.scanIntervalMinutes}
                                      onChange={(e) => setEditForm({ ...editForm, scanIntervalMinutes: e.target.value })}
                                      className="h-9 text-sm"
                                      aria-label={`Edit scan cadence for ${mission.name}`}
                                    />
                                  </div>
                                </div>
                                <div className="flex items-center justify-between gap-3 rounded-md border border-border/60 bg-background/50 p-3">
                                  <div className="space-y-0.5">
                                    <div className="text-sm font-medium">Auto scan</div>
                                    <div className="text-xs text-muted-foreground">
                                      Enable automated periodic scanning for this mission.
                                    </div>
                                  </div>
                                  <Switch
                                    checked={editForm.autoScanEnabled}
                                    onCheckedChange={(checked) => setEditForm({ ...editForm, autoScanEnabled: checked })}
                                    aria-label={`Edit auto scan for ${mission.name}`}
                                  />
                                </div>
                              </div>
                              <div className="flex items-center gap-2 pt-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={handleCancelMissionEdit}
                                  className="flex-1"
                                >
                                  Cancel
                                </Button>
                                <Button
                                  variant="default"
                                  size="sm"
                                  onClick={() => handleSaveMissionEdit(mission)}
                                  disabled={savingMissionId === mission.mission_id}
                                  className="flex-1"
                                >
                                  {savingMissionId === mission.mission_id && (
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                  )}
                                  Save Changes
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        )
                      }

                      return (
                      <Card key={mission.mission_id} className="bg-muted/5 transition-colors hover:bg-muted/10 border-border/50">
                        <CardHeader className="p-5 pb-3">
                          <div className="flex items-start justify-between gap-3">
                            <CardTitle className="text-base font-semibold leading-tight">{mission.name}</CardTitle>
                            <div className="flex flex-wrap items-center justify-end gap-2 shrink-0">
                              <Badge variant={mission.status === 'active' ? 'default' : 'secondary'} className="text-xs px-2 py-0.5">
                                {mission.status}
                              </Badge>
                              <div className="flex items-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleEditMission(mission)}
                                  disabled={
                                    savingMissionId === mission.mission_id
                                    || deletingMissionId === mission.mission_id
                                  }
                                  className="h-8 text-xs px-2"
                                  aria-label={`Edit mission ${mission.name}`}
                                >
                                  Edit
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => void handleDeleteMission(mission)}
                                  disabled={
                                    savingMissionId === mission.mission_id
                                    || deletingMissionId === mission.mission_id
                                  }
                                  className="h-8 w-8 text-muted-foreground hover:text-destructive transition-colors"
                                  title={`Delete mission ${mission.name}`}
                                  aria-label={`Delete mission ${mission.name}`}
                                >
                                  {deletingMissionId === mission.mission_id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <Trash2 className="h-4 w-4" />
                                  )}
                                </Button>
                              </div>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="px-5 pb-5 space-y-4">
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {mission.brief}
                          </p>
                          {isRequirementDrivenMission(mission) && (
                            <div className="mb-4 space-y-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="outline" className="border-amber-500/40 text-xs">
                                  Requirement-driven
                                </Badge>
                                <span className="text-muted-foreground">
                                  {requirementSummary(requirementProfile)}
                                </span>
                              </div>
                              {candidateProducts.length > 0 && (
                                <div className="grid gap-2 md:grid-cols-2">
                                  {candidateProducts.slice(0, 4).map((candidate) => (
                                    <div
                                      key={`${mission.mission_id}-${candidate.tracked_product_id}`}
                                      className="rounded border border-border/60 bg-background/70 px-2 py-1.5"
                                    >
                                      <div className="flex items-center justify-between gap-2">
                                        <span className="min-w-0 truncate font-medium">
                                          {candidateProductName(candidate)}
                                        </span>
                                        <Badge variant="secondary" className="text-xs">
                                          {candidate.fit_label.replace(/_/g, ' ')}
                                        </Badge>
                                      </div>
                                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                                        <span>fit {Math.round(candidate.fit_score)}</span>
                                        <span>{benchmarkStateLabel(candidate.benchmark_state)}</span>
                                        {candidate.warning && (
                                          <span className="text-destructive">{candidate.warning}</span>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                          <div className="space-y-3 rounded-md border border-border/60 bg-background/70 p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="text-xs font-semibold text-foreground uppercase tracking-wider">
                                  Primary tracked product
                                </div>
                                <div className="truncate text-sm font-medium mt-1">
                                  {linkedProduct
                                    ? trackedProductDisplayName(linkedProduct)
                                    : linkedProductId || 'No primary tracked product linked'}
                                </div>
                              </div>
                              <Badge
                                variant={benchmarkStateBadgeVariant(benchmarkState)}
                                className="shrink-0 text-xs px-2"
                              >
                                {linkedProductId
                                  ? benchmarkStateLabel(benchmarkState)
                                  : 'not linked'}
                              </Badge>
                            </div>

                            {linkedProductId && (
                              <div className="grid gap-x-4 gap-y-2 text-xs sm:grid-cols-2 pt-1 border-t border-border/40">
                                <div className="flex justify-between sm:block">
                                  <span className="text-muted-foreground">Fair range:</span>{' '}
                                  <span className="font-mono font-medium">{fairRangeLabel(benchmarkState)}</span>
                                </div>
                                <div className="flex justify-between sm:block">
                                  <span className="text-muted-foreground">Used median:</span>{' '}
                                  <span className="font-mono font-medium">
                                    {formatCurrency(benchmarkState?.used_median)}
                                  </span>
                                </div>
                                <div className="flex justify-between sm:block">
                                  <span className="text-muted-foreground">Samples:</span>{' '}
                                  <span className="font-mono font-medium">
                                    {typeof benchmarkState?.sample_size === 'number'
                                      ? benchmarkState.sample_size
                                      : 'n/a'}
                                  </span>
                                </div>
                                <div className="flex justify-between sm:block">
                                  <span className="text-muted-foreground">Confidence:</span>{' '}
                                  <span className="font-mono font-medium uppercase">
                                    {benchmarkState?.confidence_label || 'unknown'}
                                  </span>
                                </div>
                              </div>
                            )}

                            {mission.primary_tracked_product?.warning && (
                              <p className="text-xs text-destructive font-medium">
                                {mission.primary_tracked_product.warning}
                              </p>
                            )}
                            {benchmarkState?.warnings && benchmarkState.warnings.length > 0 && (
                              <p className="text-xs text-muted-foreground italic">
                                {benchmarkState.warnings.slice(0, 2).join(' ')}
                              </p>
                            )}

                            {trackedProductsLoaded ? (
                              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/40">
                                <select
                                  aria-label={`Linked tracked product for ${mission.name}`}
                                  value={linkedProductId}
                                  onChange={(event) =>
                                    void handleTrackedProductLink(mission, event.target.value)
                                  }
                                  disabled={
                                    linkingMissionId === mission.mission_id
                                    || savingMissionId === mission.mission_id
                                    || deletingMissionId === mission.mission_id
                                  }
                                  className="h-8 min-w-0 flex-1 rounded-md border border-input bg-background px-2 text-xs"
                                >
                                  <option value="">No tracked product</option>
                                  {linkedProductId && !linkedProductInOptions && (
                                    <option value={linkedProductId}>
                                      {linkedProduct
                                        ? trackedProductDisplayName(linkedProduct)
                                        : linkedProductId}
                                    </option>
                                  )}
                                  {trackedProducts.map((product) => (
                                    <option
                                      key={product.tracked_product_id}
                                      value={product.tracked_product_id}
                                    >
                                      {trackedProductDisplayName(product)}
                                    </option>
                                  ))}
                                </select>
                                {linkingMissionId === mission.mission_id && (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                                )}
                              </div>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void ensureTrackedProductsLoaded()}
                                disabled={trackedProductsLoading}
                                className="h-8 text-xs w-full mt-1"
                              >
                                {trackedProductsLoading ? (
                                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                                ) : (
                                  <RefreshCw className="mr-1.5 h-3 w-3" />
                                )}
                                Load tracked products
                              </Button>
                            )}

                            {linkedProductId && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void handleCalibrateProduct(linkedProductId)}
                                disabled={calibratingProductId === linkedProductId || scanBlocked}
                                className="h-8 text-xs w-full mt-1.5 bg-background/50 hover:bg-background"
                              >
                                {calibratingProductId === linkedProductId ? (
                                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                                ) : (
                                  <RefreshCw className="mr-1.5 h-3 w-3" />
                                )}
                                {benchmarkState?.sample_size && benchmarkState.sample_size > 0
                                  ? 'Recalibrate Price'
                                  : 'Bootstrap Benchmark'}
                              </Button>
                            )}

                            {linkedProductId && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void handleSyncEbay(linkedProductId)}
                                disabled={syncingEbayProductId === linkedProductId || scanBlocked}
                                className="h-8 text-xs w-full mt-1.5 bg-background/50 hover:bg-background"
                              >
                                {syncingEbayProductId === linkedProductId ? (
                                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                                ) : (
                                  <Store className="mr-1.5 h-3 w-3" />
                                )}
                                Sync eBay Sold Data
                              </Button>
                            )}
                          </div>

                          <div className="space-y-4 rounded-md border border-border/60 bg-muted/20 p-4">
                            <div className="flex items-center justify-between gap-4">
                              <div className="space-y-1">
                                <div className="text-xs font-semibold text-foreground uppercase tracking-wider">Auto scan status</div>
                                <div className="text-xs text-muted-foreground">
                                  Scheduler checks active missions continuously.
                                </div>
                              </div>
                              <Switch
                                aria-label={`Auto scan ${mission.name}`}
                                checked={mission.status === 'active'}
                                onCheckedChange={(checked) => void handleAutoScanToggle(mission, checked)}
                                disabled={savingMissionId === mission.mission_id}
                              />
                            </div>
                            
                            <div className="flex flex-col sm:flex-row items-end gap-3 pt-2 border-t border-border/40">
                              <div className="w-full space-y-1.5">
                                <label className="text-xs font-medium text-muted-foreground">
                                  Check cadence (minutes)
                                </label>
                                <Input
                                  type="number"
                                  inputMode="numeric"
                                  min="1"
                                  value={
                                    missionIntervalDrafts[mission.mission_id]
                                    ?? String(missionScanIntervalMinutes(mission))
                                  }
                                  onChange={(event) =>
                                    setMissionIntervalDrafts((current) => ({
                                      ...current,
                                      [mission.mission_id]: event.target.value,
                                    }))
                                  }
                                  className="h-9 text-sm bg-background"
                                  aria-label={`Scan cadence for ${mission.name}`}
                                />
                              </div>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => void handleSaveCadence(mission)}
                                disabled={savingMissionId === mission.mission_id}
                                className="h-9 px-4 text-xs font-medium"
                                aria-label={`Save cadence for ${mission.name}`}
                              >
                                Update
                              </Button>
                            </div>
                            
                            <div className="space-y-1 text-xs">
                              <div className="flex items-center gap-1.5 text-muted-foreground">
                                <div className={cn(
                                  "h-1.5 w-1.5 rounded-full",
                                  mission.status === 'active' ? "bg-emerald-500" : "bg-muted-foreground/40"
                                )} />
                                {mission.status === 'active'
                                  ? `Scanning every ${missionScanIntervalMinutes(mission)} minutes`
                                  : `Auto scan is paused`}
                              </div>
                              {mission.last_scan_at && (
                                <div className="text-muted-foreground pl-3">
                                  Last run: <span className="font-mono">{formatClock(mission.last_scan_at)}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center justify-between gap-4 pt-2">
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => void handleTriggerScan(mission.mission_id)}
                              disabled={
                                loading
                                || scanBlocked
                                || savingMissionId === mission.mission_id
                                || editingMissionId === mission.mission_id
                              }
                              className="flex-1 h-10 text-sm font-medium"
                            >
                              <Play className="mr-2 h-4 w-4" />
                              Run Scan Now
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Create New Mission</CardTitle>
                <CardDescription>Define a new search objective for the Marketplace engine.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Mission Name</label>
                    <Input
                      placeholder="e.g. Vintage Watches"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Max Price (Optional)</label>
                    <Input
                      type="number"
                      placeholder="e.g. 1500"
                      value={form.priceMax}
                      onChange={(e) => setForm({ ...form, priceMax: e.target.value })}
                    />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Auto Scan</label>
                    <div className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2">
                      <div>
                        <div className="text-xs font-medium">
                          {form.autoScanEnabled ? 'Enabled' : 'Paused'}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Active missions are scanned by the scheduler on this cadence.
                        </div>
                      </div>
                      <Switch
                        aria-label="Auto scan for new mission"
                        checked={form.autoScanEnabled}
                        onCheckedChange={(checked) => setForm({ ...form, autoScanEnabled: checked })}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Scan Every (Minutes)</label>
                    <Input
                      type="number"
                      inputMode="numeric"
                      min="1"
                      placeholder="e.g. 5"
                      value={form.scanIntervalMinutes}
                      onChange={(e) => setForm({ ...form, scanIntervalMinutes: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium">Search Brief / Goal</label>
                  <Textarea
                    placeholder="Describe what you are looking for..."
                    rows={3}
                    value={form.brief}
                    onChange={(e) => setForm({ ...form, brief: e.target.value })}
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Include Keywords (CSV)</label>
                    <Input
                      placeholder="rolex, omega, tudor"
                      value={form.includeKeywords}
                      onChange={(e) => setForm({ ...form, includeKeywords: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Exclude Keywords (CSV)</label>
                    <Input
                      placeholder="fake, homage, mod"
                      value={form.excludeKeywords}
                      onChange={(e) => setForm({ ...form, excludeKeywords: e.target.value })}
                    />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Preferred Brands (CSV)</label>
                    <Input
                      placeholder="asus, msi, gigabyte"
                      value={form.preferredBrands}
                      onChange={(e) => setForm({ ...form, preferredBrands: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Locations (CSV)</label>
                    <Input
                      placeholder="Melbourne, Richmond, Box Hill"
                      value={form.locationNames}
                      onChange={(e) => setForm({ ...form, locationNames: e.target.value })}
                    />
                  </div>
                </div>
                <Button
                  className="w-full"
                  onClick={handleCreateMission}
                  disabled={creating || !form.name || !form.brief || !form.locationNames.trim()}
                >
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create Mission
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader className="p-4">
                <CardTitle className="text-sm font-semibold">Browser Health</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {browserHealth ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">Status</span>
                      <Badge variant={healthBadgeVariant(browserHealth.status)} className="text-xs font-mono">
                        {browserHealth.status}
                      </Badge>
                    </div>
                    {browserHealth.detail && (
                      <p className="text-xs text-destructive italic">{browserHealth.detail}</p>
                    )}
                    {!scanAllowed && (
                      <p className="text-xs text-destructive italic">
                        Scan blocked: {scanBlocker}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">Health data unavailable.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold">Recent Scans</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {scanJobs.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">No recent scan history.</p>
                ) : (
                    <div className="space-y-3">
                    {scanJobs.slice(0, 30).map((job) => (
                      <div
                        key={job.job_id}
                        className={`group relative flex flex-col gap-1 rounded-md border transition-all ${
                          selectedScanJobId === job.job_id
                            ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
                            : 'border-border/50 hover:border-border hover:bg-muted/40'
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => void handleSelectScanJob(job.job_id)}
                          aria-pressed={selectedScanJobId === job.job_id}
                          aria-label={`Inspect scan ${job.job_id.slice(0, 8)}`}
                          className="w-full text-left p-3 space-y-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-bold font-mono text-foreground">
                              #{job.job_id.slice(0, 8)}
                            </span>
                            <Badge variant={scanBadgeVariant(job.status)} className="text-xs uppercase font-bold px-1.5 h-4">
                              {job.status}
                            </Badge>
                          </div>
                          
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1">
                                {formatClock(job.started_at)}
                              </span>
                              <span className="font-medium text-foreground">
                                {job.progress_stage || (job.progress_pct != null ? formatProgress(job.progress_pct) : 'idle')}
                              </span>
                            </div>
                            {job.progress_pct != null && (
                              <Progress value={clampProgress(job.progress_pct)} className="h-1.5 bg-muted" />
                            )}
                          </div>
                        </button>
                        {['queued', 'running'].includes(job.status) && (
                          <Button
                            variant="secondary"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation()
                              void handleStopScan(job.job_id)
                            }}
                            disabled={stoppingJobId === job.job_id}
                            className="absolute -right-2 -top-2 h-7 w-7 rounded-full border bg-background shadow-md hover:text-destructive transition-transform hover:scale-110"
                            title="Stop Scan"
                          >
                            {stoppingJobId === job.job_id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <X className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base">Scan Output</CardTitle>
                <CardDescription>
                  Live scanner output and persisted progress for the selected Marketplace scan.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {selectedScanJob && ['queued', 'running'].includes(selectedScanJob.status) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void handleStopScan(selectedScanJob.job_id)}
                    disabled={stoppingJobId === selectedScanJob.job_id}
                  >
                    {stoppingJobId === selectedScanJob.job_id && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Stop Scan
                  </Button>
                )}
                {selectedScanJobId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void loadSelectedScanJob(selectedScanJobId)}
                    disabled={scanOutputLoading}
                  >
                    <RefreshCw className={`mr-2 h-4 w-4 ${scanOutputLoading ? 'animate-spin' : ''}`} />
                    Refresh Output
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedScanJobId && (
              <p className="text-sm text-muted-foreground italic">
                No Marketplace scan selected yet.
              </p>
            )}

            {selectedScanJobId && scanOutputError && (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
                {scanOutputError}
              </div>
            )}

            {selectedScanJobId && !scanOutputError && scanOutputLoading && !selectedScanJob && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading scan output…
              </div>
            )}

            {selectedScanJob && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={scanBadgeVariant(selectedScanJob.status)}>
                    {selectedScanJob.status}
                  </Badge>
                  <Badge variant="outline" className="font-mono">
                    {selectedScanJob.job_id}
                  </Badge>
                  {selectedScanJob.progress_stage && (
                    <Badge variant="outline">{selectedScanJob.progress_stage}</Badge>
                  )}
                  {formatProgress(selectedScanJob.progress_pct) && (
                    <Badge variant="outline" className="font-mono">
                      {formatProgress(selectedScanJob.progress_pct)}
                    </Badge>
                  )}
                </div>

                <div className="grid gap-3 text-xs text-muted-foreground sm:grid-cols-4">
                  <div>
                    <div className="font-medium text-foreground">Started</div>
                    <div className="font-mono">{formatClock(selectedScanJob.started_at)}</div>
                  </div>
                  <div>
                    <div className="font-medium text-foreground">Finished</div>
                    <div className="font-mono">{formatClock(selectedScanJob.ended_at)}</div>
                  </div>
                  <div>
                    <div className="font-medium text-foreground">Exit Code</div>
                    <div className="font-mono">
                      {selectedScanJob.exit_code == null ? 'running' : selectedScanJob.exit_code}
                    </div>
                  </div>
                  <div>
                    <div className="font-medium text-foreground">Stdout Log</div>
                    <div className="truncate font-mono">
                      {selectedScanJob.stdout_path || 'not available'}
                    </div>
                  </div>
                </div>

                {selectedScanJob.progress_pct != null && (
                  <div className="space-y-1">
                    <Progress value={clampProgress(selectedScanJob.progress_pct)} className="h-2" />
                    <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
                      <span>{formatProgress(selectedScanJob.progress_pct)}</span>
                      <span className="truncate pl-3">
                        {selectedScanJob.progress_stage || 'working'}
                      </span>
                    </div>
                  </div>
                )}

                <div className="overflow-hidden rounded-md border border-border/60 bg-muted/20">
                  <ScrollArea className="h-[320px]">
                    <pre
                      className="whitespace-pre-wrap break-words p-4 font-mono text-xs leading-5 text-foreground/90"
                      role="log"
                      aria-label="Marketplace scan output"
                    >
                      {selectedScanJob.result || scanOutputPlaceholder(selectedScanJob)}
                    </pre>
                  </ScrollArea>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle className="text-base">Listings & New Retail Benchmark Review</CardTitle>
                <CardDescription>
                  Captured listings stay down here for review after the mission controls and scan output.
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">source: centre_com</Badge>
                <label htmlFor="benchmark-review-sort" className="text-xs font-medium text-muted-foreground">
                  Sort
                </label>
                <select
                  id="benchmark-review-sort"
                  aria-label="Sort benchmark review listings"
                  value={benchmarkSortMode}
                  onChange={(event) => setBenchmarkSortMode(event.target.value as BenchmarkSortMode)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                >
                  <option value="mission">Mission</option>
                  <option value="missing">Missing data</option>
                  <option value="value">Best price gap</option>
                  <option value="confidence">Confidence</option>
                  <option value="newest">Newest captured</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {benchmarkMatches.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                No captured listings are available yet. Run a scan to populate benchmark review cards.
              </p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="text-xs">
                    {benchmarkMatches.length} listings loaded
                  </Badge>
                  <Badge variant={benchmarkReviewCount > 0 ? 'secondary' : 'outline'} className="text-xs">
                    {benchmarkReviewCount} need review
                  </Badge>
                  <Badge variant={benchmarkMissingCount > 0 ? 'secondary' : 'outline'} className="text-xs">
                    {benchmarkMissingCount} with missing data
                  </Badge>
                </div>
                <div className="grid gap-3 xl:grid-cols-2">
                  {sortedBenchmarkMatches.slice(0, 18).map((match) => {
                    const benchmark = match.benchmark ?? null
                    const comparison = match.price_comparison ?? null
                    const comparisonHelp = comparisonHelpText(comparison)
                    const retailAnchorIgnored = comparison?.comparison_state === 'retail_anchor_needs_review'
                    const media = listingMediaForMatch(match)
                    const firstMedia = media[0] ?? null
                    const priceEvidence = priceEvidenceForMatch(match)
                    const missingReasons = benchmarkMissingReasons(match)
                    const confidenceLabel =
                      typeof benchmark?.confidence === 'number' && Number.isFinite(benchmark.confidence)
                        ? `${Math.round(benchmark.confidence * 100)}%`
                        : 'unknown'
                    return (
                      <div
                        key={match.match_id}
                        data-testid="marketplace-benchmark-listing"
                        className="rounded-md border border-border/70 bg-muted/10 p-3"
                      >
                        <div className="flex flex-col gap-3 sm:flex-row">
                          <div className="relative overflow-hidden rounded-md border border-border/60 bg-muted/30 sm:w-48 sm:shrink-0">
                            {firstMedia ? (
                              <img
                                src={firstMedia}
                                alt={`Listing photo for ${match.title}`}
                                className="aspect-video w-full object-contain sm:aspect-square sm:h-full"
                              />
                            ) : (
                              <div className="flex aspect-video items-center justify-center gap-2 text-xs text-muted-foreground sm:aspect-square sm:h-full">
                                <ImageOff className="h-4 w-4" />
                                No photos
                              </div>
                            )}
                          </div>
                          <div className="min-w-0 flex-1 space-y-3">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="outline" className="max-w-full truncate text-xs">
                                    {missionNameForMatch(match)}
                                  </Badge>
                                  <Badge
                                    variant={benchmarkReviewBadgeVariant(match)}
                                    className="text-xs"
                                  >
                                    {benchmarkReviewLabel(match)}
                                  </Badge>
                                </div>
                                <div className="mt-1 line-clamp-2 text-sm font-medium">{match.title}</div>
                                <div className="text-xs text-muted-foreground">
                                  Captured {formatClock(match.captured_at)}
                                </div>
                              </div>
                            </div>

                            <div className="grid gap-2 text-xs grid-cols-2 lg:grid-cols-4">
                              <div className="rounded-md border border-border/60 bg-background/70 p-2">
                                <div className="text-xs uppercase text-muted-foreground">Listing</div>
                                <div className="mt-1 font-mono font-semibold">{listingPriceLabel(match)}</div>
                                <div className="mt-1 text-xs text-muted-foreground">
                                  {priceSourceLabel(priceEvidence)}
                                </div>
                              </div>
                              <div className="rounded-md border border-border/60 bg-background/70 p-2">
                                <div className="text-xs uppercase text-muted-foreground">Current retail</div>
                                <div className="mt-1 font-mono font-semibold">
                                  {benchmark?.current_price == null
                                    ? 'Missing'
                                    : formatCurrency(benchmark.current_price)}
                                </div>
                                <div className="mt-1 text-xs text-muted-foreground">
                                  {retailAnchorIgnored ? 'ignored pending review' : 'Centre Com now'}
                                </div>
                              </div>
                              <div className="rounded-md border border-border/60 bg-background/70 p-2">
                                <div className="text-xs uppercase text-muted-foreground">30d median</div>
                                <div className="mt-1 font-mono font-semibold">
                                  {benchmark?.median_30d == null
                                    ? 'Missing'
                                    : formatCurrency(benchmark.median_30d)}
                                </div>
                                <div className="mt-1 text-xs text-muted-foreground">
                                  New-retail history
                                </div>
                              </div>
                              <div className="rounded-md border border-border/60 bg-background/70 p-2">
                                <div className="text-xs uppercase text-muted-foreground">Delta</div>
                                <div className="mt-1 font-mono font-semibold">
                                  {retailAnchorIgnored
                                    ? 'Review first'
                                    : benchmark?.listing_delta_pct == null
                                    ? 'Unavailable'
                                    : formatDelta(benchmark.listing_delta_pct)}
                                </div>
                                <div className="mt-1 text-xs text-muted-foreground">
                                  vs benchmark
                                </div>
                              </div>
                            </div>

                            <div className="grid gap-2 text-xs sm:grid-cols-2">
                              <div>
                                <span className="text-muted-foreground">Matched product: </span>
                                <span className="font-medium">
                                  {benchmark?.matched_product || 'No confident product match'}
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Confidence: </span>
                                <span className="font-mono">{confidenceLabel}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Freshness: </span>
                                <span>{benchmarkFreshnessLabel(benchmark?.freshness_hours)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Photos: </span>
                                <span className="font-mono">{media.length}</span>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                wording: {benchmark?.wording || 'new retail benchmark'}
                              </Badge>
                              {benchmark?.review_status && (
                                <Badge variant="outline" className="text-xs">
                                  review: {benchmark.review_status}
                                </Badge>
                              )}
                              {missingReasons.map((reason) => (
                                <Badge key={`${match.match_id}-${reason}`} variant="secondary" className="text-xs">
                                  {reason}
                                </Badge>
                              ))}
                            </div>

                            {(priceEvidence?.warning || benchmark?.warning) && (
                              <div className="space-y-1 text-xs">
                                {priceEvidence?.warning && (
                                  <p className="text-amber-700 dark:text-amber-300">
                                    {priceEvidence.warning}
                                  </p>
                                )}
                                {benchmark?.warning && (
                                  <p className="text-destructive">{benchmark.warning}</p>
                                )}
                              </div>
                            )}

                            {comparisonHelp && (
                              <p className="text-xs text-muted-foreground">{comparisonHelp}</p>
                            )}

                            {benchmark?.rationale && benchmark.rationale.length > 0 && (
                              <p className="text-xs text-muted-foreground">
                                {benchmark.rationale.slice(0, 2).join(' ')}
                              </p>
                            )}

                            <a
                              href={`/marketplace/matches/${encodeURIComponent(match.match_id)}`}
                              className="inline-flex text-xs text-primary underline-offset-2 hover:underline"
                            >
                              Open review details
                            </a>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </CardContent>
        </Card>

      </div>
    </div>
  )
}
