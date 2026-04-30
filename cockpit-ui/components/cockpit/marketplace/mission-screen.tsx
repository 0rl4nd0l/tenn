'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { AlertTriangle, ImageOff, Loader2, Play, RefreshCw, Store, Trash2, X } from 'lucide-react'

import {
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
  if (status === 'challenge_detected') return 'secondary'
  if (status === 'browser_not_running' || status === 'desktop_session_missing' || status === 'browser_unavailable') return 'destructive'
  return 'outline'
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

function missionAggressiveAlertingEnabled(mission: MarketplaceMission): boolean {
  return Boolean((mission.scan_config || {}).aggressive_alerting)
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
  const [stoppingJobId, setStoppingJobId] = useState<string | null>(null)
  const [refreshingBenchmarks, setRefreshingBenchmarks] = useState(false)
  const selectedScanJobIdRef = useRef<string | null>(null)
  const desktopSessionMissing = browserHealth?.status === 'desktop_session_missing'
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
      setNotice(`Mission "${mission.name}" created. Starting initial scan...`)
      await handleTriggerScan(mission.mission_id)
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

  async function handleTriggerScan(missionId: string) {
    setError(null)
    setNotice(null)
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

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <div>
                <CardTitle className="text-base">Listings & New Retail Benchmark Review</CardTitle>
                <CardDescription>
                  Compare captured listings against Centre Com new-retail references for GPUs, NVMe M.2, CPUs, and RAM kits.
                </CardDescription>
              </div>
              <Badge variant="outline">source: centre_com</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {benchmarkMatches.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                No captured listings are available yet. Run a scan to populate benchmark review cards.
              </p>
            ) : (
              <div className="grid gap-3 lg:grid-cols-2">
                {benchmarkMatches.slice(0, 10).map((match) => {
                  const benchmark = match.benchmark ?? null
                  const media = listingMediaForMatch(match)
                  const firstMedia = media[0] ?? null
                  return (
                    <div key={match.match_id} className="rounded-md border border-border/70 bg-muted/10 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-medium">{match.title}</div>
                          <div className="text-xs text-muted-foreground">
                            Listing price: <span className="font-mono">{match.price || 'n/a'}</span>
                          </div>
                        </div>
                        <Badge variant={benchmark?.low_confidence ? 'destructive' : 'secondary'}>
                          {benchmark?.low_confidence ? 'needs review' : 'benchmarked'}
                        </Badge>
                      </div>
                      <div className="mt-3 overflow-hidden rounded-md border border-border/60 bg-background/60">
                        {firstMedia ? (
                          <img
                            src={firstMedia}
                            alt={`Listing photo for ${match.title}`}
                            className="h-36 w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-24 items-center justify-center gap-2 text-xs text-muted-foreground">
                            <ImageOff className="h-4 w-4" />
                            Listing photos unavailable
                          </div>
                        )}
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">
                          photos: {media.length > 0 ? media.length : 0}
                        </Badge>
                      </div>
                      {benchmark ? (
                        <div className="mt-3 space-y-1 text-xs">
                          <div>
                            Matched product:{' '}
                            <span className="font-medium">
                              {benchmark.matched_product || 'No confident product match'}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>Current Centre Com: <span className="font-mono">{formatCurrency(benchmark.current_price)}</span></div>
                            <div>30d median: <span className="font-mono">{formatCurrency(benchmark.median_30d)}</span></div>
                            <div>Listing delta: <span className="font-mono">{formatDelta(benchmark.listing_delta_pct)}</span></div>
                            <div>Confidence: <span className="font-mono">{Math.round(benchmark.confidence * 100)}%</span></div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-[10px]">
                              freshness: {benchmarkFreshnessLabel(benchmark.freshness_hours)}
                            </Badge>
                            <Badge variant="outline" className="text-[10px]">
                              wording: {benchmark.wording || 'new retail benchmark'}
                            </Badge>
                            {benchmark.review_status && (
                              <Badge variant="outline" className="text-[10px]">
                                review: {benchmark.review_status}
                              </Badge>
                            )}
                          </div>
                          {benchmark.warning && (
                            <p className="text-[11px] text-destructive">{benchmark.warning}</p>
                          )}
                        </div>
                      ) : (
                        <p className="mt-2 text-xs text-muted-foreground">
                          Benchmark overlay unavailable for this listing yet.
                        </p>
                      )}
                      <div className="mt-3">
                        <a
                          href={`/marketplace/matches/${encodeURIComponent(match.match_id)}`}
                          className="text-xs text-primary underline-offset-2 hover:underline"
                        >
                          Open review details
                        </a>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <MarketplaceAssistant
          apiKey={apiKey}
          browserHealth={browserHealth}
          onMarketplaceStateChange={load}
          onScanQueued={handleAssistantScanQueued}
        />

        <div className={cn(
          "grid gap-6",
          isIPhoneScale ? "grid-cols-1" : "lg:grid-cols-[1fr_320px]"
        )}>
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Store className="h-5 w-5 text-primary" />
                  <CardTitle>Active Missions</CardTitle>
                </div>
                <CardDescription>Missions currently configured for automated scanning.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {missions.length === 0 ? (
                  <p className="py-10 text-center text-sm text-muted-foreground italic">No missions configured yet.</p>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {missions.map((mission) => {
                      const linkedProduct = missionLinkedProduct(mission)
                      const linkedProductId = missionLinkedProductId(mission)
                      const benchmarkState = mission.benchmark_state ?? null
                      const requirementProfile = missionRequirementProfile(mission)
                      const candidateProducts = mission.candidate_products ?? []
                      const linkedProductInOptions = trackedProducts.some(
                        (product) => product.tracked_product_id === linkedProductId,
                      )
                      return (
                      <Card key={mission.mission_id} className="bg-muted/5 transition-colors hover:bg-muted/10">
                        <CardHeader className="p-4">
                          <div className="flex items-start justify-between gap-2">
                            <CardTitle className="text-sm font-semibold">{mission.name}</CardTitle>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEditMission(mission)}
                                disabled={
                                  savingMissionId === mission.mission_id
                                  || deletingMissionId === mission.mission_id
                                }
                                className="h-7 text-[10px]"
                              >
                                Edit Mission
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => void handleDeleteMission(mission)}
                                disabled={
                                  savingMissionId === mission.mission_id
                                  || deletingMissionId === mission.mission_id
                                }
                                className="h-7 w-7 text-destructive hover:text-destructive"
                                title={`Delete mission ${mission.name}`}
                                aria-label={`Delete mission ${mission.name}`}
                              >
                                {deletingMissionId === mission.mission_id ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Trash2 className="h-3.5 w-3.5" />
                                )}
                              </Button>
                              <Badge variant={mission.status === 'active' ? 'default' : 'outline'} className="text-[10px]">
                                {mission.status}
                              </Badge>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent className="px-4 pb-4">
                          <p className="line-clamp-2 text-xs text-muted-foreground mb-4">
                            {mission.brief}
                          </p>
                          {isRequirementDrivenMission(mission) && (
                            <div className="mb-4 space-y-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-[11px]">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="outline" className="border-amber-500/40 text-[10px]">
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
                                        <Badge variant="secondary" className="text-[9px]">
                                          {candidate.fit_label.replace(/_/g, ' ')}
                                        </Badge>
                                      </div>
                                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
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
                          <div className="mb-4 space-y-3 rounded-md border border-border/60 bg-background/70 p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="text-[11px] font-medium text-foreground">
                                  Primary tracked product
                                </div>
                                <div className="truncate text-[10px] text-muted-foreground">
                                  {linkedProduct
                                    ? trackedProductDisplayName(linkedProduct)
                                    : linkedProductId || 'No primary tracked product linked'}
                                </div>
                              </div>
                              <Badge
                                variant={benchmarkStateBadgeVariant(benchmarkState)}
                                className="shrink-0 text-[9px]"
                              >
                                {linkedProductId
                                  ? benchmarkStateLabel(benchmarkState)
                                  : 'not linked'}
                              </Badge>
                            </div>

                            {linkedProductId && (
                              <div className="grid gap-1 text-[10px] text-muted-foreground sm:grid-cols-2">
                                <div>
                                  Fair range:{' '}
                                  <span className="font-mono">{fairRangeLabel(benchmarkState)}</span>
                                </div>
                                <div>
                                  Used median:{' '}
                                  <span className="font-mono">
                                    {formatCurrency(benchmarkState?.used_median)}
                                  </span>
                                </div>
                                <div>
                                  Samples:{' '}
                                  <span className="font-mono">
                                    {typeof benchmarkState?.sample_size === 'number'
                                      ? benchmarkState.sample_size
                                      : 'n/a'}
                                  </span>
                                </div>
                                <div>
                                  Confidence:{' '}
                                  <span className="font-mono">
                                    {benchmarkState?.confidence_label || 'unknown'}
                                  </span>
                                </div>
                              </div>
                            )}

                            {mission.primary_tracked_product?.warning && (
                              <p className="text-[10px] text-destructive">
                                {mission.primary_tracked_product.warning}
                              </p>
                            )}
                            {benchmarkState?.warnings && benchmarkState.warnings.length > 0 && (
                              <p className="text-[10px] text-muted-foreground">
                                {benchmarkState.warnings.slice(0, 2).join(' ')}
                              </p>
                            )}

                            {trackedProductsLoaded ? (
                              <div className="flex flex-wrap items-center gap-2">
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
                                className="h-8 text-[10px]"
                              >
                                {trackedProductsLoading ? (
                                  <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                                ) : (
                                  <RefreshCw className="mr-1.5 h-3 w-3" />
                                )}
                                Load tracked products
                              </Button>
                            )}
                          </div>
                          {editingMissionId === mission.mission_id && editForm && (
                            <div className="mb-4 space-y-4 rounded-md border border-border/60 bg-background/80 p-3">
                              <div className="grid gap-3 sm:grid-cols-2">
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Mission Name</label>
                                  <Input
                                    value={editForm.name}
                                    onChange={(event) => setEditForm({ ...editForm, name: event.target.value })}
                                    aria-label={`Edit name for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Max Price</label>
                                  <Input
                                    type="number"
                                    inputMode="numeric"
                                    value={editForm.priceMax}
                                    onChange={(event) => setEditForm({ ...editForm, priceMax: event.target.value })}
                                    aria-label={`Edit max price for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                              </div>
                              <div className="space-y-1">
                                <label className="text-[10px] font-medium text-muted-foreground">Brief</label>
                                <Textarea
                                  rows={3}
                                  value={editForm.brief}
                                  onChange={(event) => setEditForm({ ...editForm, brief: event.target.value })}
                                  aria-label={`Edit brief for ${mission.name}`}
                                  className="text-xs"
                                />
                              </div>
                              <div className="grid gap-3 sm:grid-cols-2">
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Include Keywords</label>
                                  <Input
                                    value={editForm.includeKeywords}
                                    onChange={(event) => setEditForm({ ...editForm, includeKeywords: event.target.value })}
                                    aria-label={`Edit include keywords for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Exclude Keywords</label>
                                  <Input
                                    value={editForm.excludeKeywords}
                                    onChange={(event) => setEditForm({ ...editForm, excludeKeywords: event.target.value })}
                                    aria-label={`Edit exclude keywords for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                              </div>
                              <div className="grid gap-3 sm:grid-cols-2">
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Preferred Brands</label>
                                  <Input
                                    value={editForm.preferredBrands}
                                    onChange={(event) => setEditForm({ ...editForm, preferredBrands: event.target.value })}
                                    aria-label={`Edit preferred brands for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Locations</label>
                                  <Input
                                    value={editForm.locationNames}
                                    onChange={(event) => setEditForm({ ...editForm, locationNames: event.target.value })}
                                    aria-label={`Edit locations for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                              </div>
                              <div className="grid gap-3 sm:grid-cols-2">
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Scan Every (Minutes)</label>
                                  <Input
                                    type="number"
                                    inputMode="numeric"
                                    min="1"
                                    value={editForm.scanIntervalMinutes}
                                    onChange={(event) => setEditForm({ ...editForm, scanIntervalMinutes: event.target.value })}
                                    aria-label={`Edit scan cadence for ${mission.name}`}
                                    className="h-8 text-xs"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[10px] font-medium text-muted-foreground">Auto Scan</label>
                                  <div className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2">
                                    <div className="text-[11px] text-muted-foreground">
                                      {editForm.autoScanEnabled ? 'Enabled' : 'Paused'}
                                    </div>
                                    <Switch
                                      aria-label={`Edit auto scan for ${mission.name}`}
                                      checked={editForm.autoScanEnabled}
                                      onCheckedChange={(checked) => setEditForm({ ...editForm, autoScanEnabled: checked })}
                                    />
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center justify-end gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={handleCancelMissionEdit}
                                  className="h-8 text-[10px]"
                                >
                                  Cancel
                                </Button>
                                <Button
                                  size="sm"
                                  onClick={() => void handleSaveMissionEdit(mission)}
                                  disabled={
                                    savingMissionId === mission.mission_id
                                    || !editForm.name.trim()
                                    || !editForm.brief.trim()
                                    || !editForm.locationNames.trim()
                                  }
                                  className="h-8 text-[10px]"
                                >
                                  Save Changes
                                </Button>
                              </div>
                            </div>
                          )}
                          <div className="mb-4 space-y-3 rounded-md border border-border/60 bg-muted/15 p-3">
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <div className="text-[11px] font-medium text-foreground">Auto scan</div>
                                <div className="text-[10px] text-muted-foreground">
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
                            <div className="flex items-end gap-2">
                              <div className="flex-1 space-y-1">
                                <label className="text-[10px] font-medium text-muted-foreground">
                                  Check every (minutes)
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
                                  className="h-8 text-xs"
                                  aria-label={`Scan cadence for ${mission.name}`}
                                />
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void handleSaveCadence(mission)}
                                disabled={savingMissionId === mission.mission_id}
                                className="h-8 text-[10px]"
                              >
                                Save cadence
                              </Button>
                            </div>
                            <div className="text-[10px] text-muted-foreground">
                              {mission.status === 'active'
                                ? `Auto scan is on. Next runs aim for every ${missionScanIntervalMinutes(mission)} minutes.`
                                : `Auto scan is off. Resume it to let the scheduler keep checking every ${missionScanIntervalMinutes(mission)} minutes.`}
                            </div>
                            {mission.last_scan_at && (
                              <div className="text-[10px] text-muted-foreground">
                                Last scan: <span className="font-mono">{formatClock(mission.last_scan_at)}</span>
                              </div>
                            )}
                            {missionAggressiveAlertingEnabled(mission) && (
                              <Badge variant="outline" className="text-[9px]">
                                aggressive alerting
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void handleTriggerScan(mission.mission_id)}
                                disabled={loading || savingMissionId === mission.mission_id || editingMissionId === mission.mission_id}
                                className="h-7 text-[10px]"
                              >
                                <Play className="mr-1.5 h-3 w-3" />
                                Scan Now
                              </Button>
                            </div>
                            <Badge variant="outline" className="text-[9px] font-mono">
                              every {missionScanIntervalMinutes(mission)} min
                            </Badge>
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
                        <div className="text-[11px] text-muted-foreground">
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
                      <Badge variant={healthBadgeVariant(browserHealth.status)} className="text-[10px] font-mono">
                        {browserHealth.status}
                      </Badge>
                    </div>
                    {browserHealth.detail && (
                      <p className="text-[10px] text-destructive italic">{browserHealth.detail}</p>
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
                        className={`group relative flex flex-col gap-1 rounded-md border px-2 py-2 transition-colors ${
                          selectedScanJobId === job.job_id
                            ? 'border-primary/40 bg-primary/5'
                            : 'border-border/50 hover:bg-muted/40'
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => void handleSelectScanJob(job.job_id)}
                          aria-pressed={selectedScanJobId === job.job_id}
                          aria-label={`Inspect scan ${job.job_id.slice(0, 8)}`}
                          className="w-full text-left space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-medium truncate max-w-[120px]">
                              Scan {job.job_id.slice(0, 8)}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <Badge variant={scanBadgeVariant(job.status)} className="text-[9px] px-1 h-4">
                                {job.status}
                              </Badge>
                            </div>
                          </div>
                          <div className="flex items-center justify-between gap-2 text-[9px] text-muted-foreground font-mono">
                            <span className="truncate">{formatClock(job.started_at)}</span>
                            <span className="truncate text-right">
                              {job.progress_stage || formatProgress(job.progress_pct) || 'idle'}
                            </span>
                          </div>
                          {job.progress_pct != null && (
                            <Progress value={clampProgress(job.progress_pct)} className="h-1" />
                          )}
                        </button>
                        {['queued', 'running'].includes(job.status) && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation()
                              void handleStopScan(job.job_id)
                            }}
                            disabled={stoppingJobId === job.job_id}
                            className="absolute -right-1 -top-1 h-6 w-6 rounded-full border bg-background shadow-sm hover:text-destructive"
                            title="Stop Scan"
                          >
                            {stoppingJobId === job.job_id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <X className="h-3 w-3" />
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
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground font-mono">
                      <span>{formatProgress(selectedScanJob.progress_pct)}</span>
                      <span className="truncate pl-3">
                        {selectedScanJob.progress_stage || 'working'}
                      </span>
                    </div>
                  </div>
                )}

                <div className="overflow-hidden rounded-md border border-border/60 bg-muted/20">
                  <ScrollArea className="h-[480px]">
                    <pre
                      className="whitespace-pre-wrap break-words p-4 font-mono text-[11px] leading-5 text-foreground/90"
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

      </div>
    </div>
  )
}
