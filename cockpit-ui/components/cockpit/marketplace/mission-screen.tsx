'use client'

import { useEffect, useState, useCallback } from 'react'
import { Loader2, Play, RefreshCw, Store } from 'lucide-react'

import {
  createMarketplaceMission,
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
import { Textarea } from '@/components/ui/textarea'

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
  if (status === 'browser_not_running' || status === 'desktop_session_missing') return 'destructive'
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

export function MarketplaceMissionScreen({ apiKey }: MarketplaceMissionScreenProps) {
  const [browserHealth, setBrowserHealth] = useState<MarketplaceBrowserHealth | null>(null)
  const [missions, setMissions] = useState<MarketplaceMission[]>([])
  const [scanJobs, setScanJobs] = useState<MarketplaceScanJob[]>([])
  const [form, setForm] = useState<MissionFormState>(DEFAULT_FORM)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

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
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load Marketplace state')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

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
      await triggerMarketplaceScan(apiKey, missionId)
      setNotice('Scan triggered successfully.')
      await load()
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : 'Failed to trigger Marketplace scan')
    }
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
                      <div key={job.job_id} className="space-y-1 border-b border-border/50 pb-2 last:border-0 last:pb-0">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-medium truncate max-w-[120px]">{job.action_id}</span>
                          <Badge variant={scanBadgeVariant(job.status)} className="text-[9px] px-1 h-4">
                            {job.status}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between text-[9px] text-muted-foreground font-mono">
                          <span>{formatClock(job.started_at)}</span>
                          {job.progress_stage && <span>{job.progress_stage}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
