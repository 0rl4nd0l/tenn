'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { AlertTriangle, Loader2, Play, RefreshCw, Store } from 'lucide-react'

import {
  createMarketplaceMission,
  getMarketplaceScanJob,
  getMarketplaceBrowserHealth,
  launchMarketplaceBrowser,
  listMarketplaceMissions,
  listMarketplaceScanJobs,
  type MarketplaceBrowserHealth,
  type MarketplaceMission,
  type MarketplaceScanJob,
  triggerMarketplaceScan,
  updateMarketplaceMission,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { MarketplaceAssistant } from './marketplace-assistant'

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
  aggressiveAlerting: false,
}

function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
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
  if (status === 'login_required' || status === 'challenge_detected') return 'secondary'
  if (status === 'browser_not_running' || status === 'desktop_session_missing' || status === 'browser_unavailable') return 'destructive'
  return 'outline'
}

function scanBadgeVariant(
  status: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'success') return 'default'
  if (status === 'running' || status === 'queued') return 'secondary'
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
  if (preferredJobId && jobs.some((job) => job.job_id === preferredJobId)) {
    return preferredJobId
  }
  const activeJob = jobs.find((job) => job.status === 'running' || job.status === 'queued')
  return activeJob?.job_id ?? jobs[0]?.job_id ?? null
}

function scanOutputPlaceholder(job: MarketplaceScanJob | null): string {
  if (!job) return 'Select a Marketplace scan to inspect live output.'
  if (job.status === 'queued') return 'Scan is queued. Output will appear when the worker starts.'
  if (job.status === 'running') return 'Scanner is running. Waiting for stdout...'
  if (job.status === 'failed') return 'Scan failed, but no stderr/stdout was captured.'
  return 'Scan completed, but no stdout was captured.'
}

export function MarketplaceMissionScreen({ apiKey }: MarketplaceMissionScreenProps) {
  const [browserHealth, setBrowserHealth] = useState<MarketplaceBrowserHealth | null>(null)
  const [missions, setMissions] = useState<MarketplaceMission[]>([])
  const [scanJobs, setScanJobs] = useState<MarketplaceScanJob[]>([])
  const [selectedScanJobId, setSelectedScanJobId] = useState<string | null>(null)
  const [selectedScanJob, setSelectedScanJob] = useState<MarketplaceScanJob | null>(null)
  const [scanOutputLoading, setScanOutputLoading] = useState(false)
  const [scanOutputError, setScanOutputError] = useState<string | null>(null)
  const [form, setForm] = useState<MissionFormState>(DEFAULT_FORM)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
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
      const [health, missionItems, jobs] = await Promise.all([
        getMarketplaceBrowserHealth(apiKey),
        listMarketplaceMissions(apiKey),
        listMarketplaceScanJobs(apiKey),
      ])
      setBrowserHealth(health)
      setMissions(missionItems)
      setScanJobs(jobs)
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
    setCreating(true)
    setError(null)
    setNotice(null)
    try {
      await createMarketplaceMission(apiKey, {
        name: form.name,
        brief: form.brief,
        hard_filters: {
          include_keywords: splitCsv(form.includeKeywords),
          exclude_keywords: splitCsv(form.excludeKeywords),
          location_names: splitCsv(form.locationNames),
          price_max: form.priceMax ? Number(form.priceMax) : null,
          preferred_brands: splitCsv(form.preferredBrands),
        },
        aggressive_alerting: form.aggressiveAlerting,
      })
      setForm(DEFAULT_FORM)
      setNotice('Mission created successfully.')
      await load()
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

  async function handleStatus(missionId: string, status: string) {
    setError(null)
    try {
      await updateMarketplaceMission(apiKey, missionId, { status })
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Mission update failed')
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
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
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

        <MarketplaceAssistant
          apiKey={apiKey}
          browserHealth={browserHealth}
          onMarketplaceStateChange={load}
          onScanQueued={handleAssistantScanQueued}
        />

        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
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
                    {missions.map((mission) => (
                      <Card key={mission.mission_id} className="bg-muted/5 transition-colors hover:bg-muted/10">
                        <CardHeader className="p-4">
                          <div className="flex items-start justify-between gap-2">
                            <CardTitle className="text-sm font-semibold">{mission.name}</CardTitle>
                            <Badge variant={mission.status === 'active' ? 'default' : 'outline'} className="text-[10px]">
                              {mission.status}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="px-4 pb-4">
                          <p className="line-clamp-2 text-xs text-muted-foreground mb-4">
                            {mission.brief}
                          </p>
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void handleTriggerScan(mission.mission_id)}
                                disabled={loading}
                                className="h-7 text-[10px]"
                              >
                                <Play className="mr-1.5 h-3 w-3" />
                                Scan Now
                              </Button>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void handleStatus(mission.mission_id, mission.status === 'active' ? 'paused' : 'active')}
                              className="h-7 text-[10px]"
                            >
                              {mission.status === 'active' ? 'Pause' : 'Resume'}
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
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
                <Button className="w-full" onClick={handleCreateMission} disabled={creating || !form.name || !form.brief}>
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
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">Logged In</span>
                      <span className="text-[10px] font-mono">{browserHealth.logged_in ? 'Yes' : 'No'}</span>
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
                <CardTitle className="text-sm font-semibold">Recent Scans</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {scanJobs.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">No recent scan history.</p>
                ) : (
                  <div className="space-y-3">
                    {scanJobs.slice(0, 10).map((job) => (
                      <button
                        key={job.job_id}
                        type="button"
                        onClick={() => void handleSelectScanJob(job.job_id)}
                        aria-pressed={selectedScanJobId === job.job_id}
                        aria-label={`Inspect scan ${job.job_id.slice(0, 8)}`}
                        className={`w-full space-y-1 rounded-md border px-2 py-2 text-left transition-colors ${
                          selectedScanJobId === job.job_id
                            ? 'border-primary/40 bg-primary/5'
                            : 'border-border/50 hover:bg-muted/40'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-medium truncate max-w-[120px]">
                            Scan {job.job_id.slice(0, 8)}
                          </span>
                          <Badge variant={scanBadgeVariant(job.status)} className="text-[9px] px-1 h-4">
                            {job.status}
                          </Badge>
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
                  <ScrollArea className="h-[320px]">
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
