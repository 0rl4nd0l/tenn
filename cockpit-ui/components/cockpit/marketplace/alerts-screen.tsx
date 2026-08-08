'use client'

import { useEffect, useState, useCallback } from 'react'
import { ExternalLink, RefreshCw } from 'lucide-react'
import Link from 'next/link'

import {
  listMarketplaceAlerts,
  listMarketplaceMissions,
  type MarketplaceAlert,
  type MarketplaceMission,
  updateMarketplaceAlert,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface MarketplaceAlertsScreenProps {
  apiKey: string
}

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

function emptyContextUnavailable(error: unknown): MarketplaceEmptyContext {
  const detail = error instanceof Error ? error.message : 'unknown error'
  return {
    reason: 'data_missing',
    title: 'DATA_MISSING: Marketplace mission context unavailable.',
    detail: `The alerts endpoint returned zero items, but mission/run evidence could not be loaded: ${detail}`,
    actionLabel: 'Open mission setup',
    actionHref: '/marketplace',
  }
}

function alertsEmptyContext(
  missions: MarketplaceMission[],
  unfilteredAlertCount: number,
  filtersActive: boolean,
): MarketplaceEmptyContext {
  if (filtersActive && unfilteredAlertCount > 0) {
    return {
      reason: 'filter_excludes',
      title: 'Filters are hiding existing alerts.',
      detail: `Unfiltered Marketplace evidence contains ${pluralize(
        unfilteredAlertCount,
        'alert',
        'alerts',
      )}; the selected status returned zero.`,
      actionLabel: 'Clear filters',
      showClearFilters: true,
    }
  }

  if (missions.length === 0) {
    return {
      reason: 'no_missions',
      title: 'No Marketplace missions configured yet.',
      detail: 'Alerts require a saved mission and match-generating scan before Tenn can raise notifications.',
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
    title: 'Marketplace scans ran, but no alerts were returned.',
    detail: `${pluralize(scannedMissions, 'mission')} include last_scan_at; no alert-triggering matches are available.`,
    actionLabel: 'Open mission setup',
    actionHref: '/marketplace',
  }
}

function formatClock(value: string): string {
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

function alertVariant(
  status: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'new') return 'default'
  if (status === 'acknowledged') return 'secondary'
  if (status === 'dismissed') return 'outline'
  return 'outline'
}

function AlertsEmptyState({
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
    detail: 'The alerts endpoint returned zero items, but no mission/run context was available to explain why.',
    actionLabel: 'Open mission setup',
    actionHref: '/marketplace',
  }

  return (
    <div className="rounded-md border border-dashed border-border px-4 py-6 text-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <p className="font-medium text-foreground">{resolved.title}</p>
          <p className="max-w-2xl text-muted-foreground">{resolved.detail}</p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
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
    </div>
  )
}

export function MarketplaceAlertsScreen({ apiKey }: MarketplaceAlertsScreenProps) {
  const [alerts, setAlerts] = useState<MarketplaceAlert[]>([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [emptyContext, setEmptyContext] = useState<MarketplaceEmptyContext | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setEmptyContext(null)
    try {
      const items = await listMarketplaceAlerts(apiKey, statusFilter === 'all' ? undefined : statusFilter)
      setAlerts(items)
      if (items.length === 0) {
        const filtersActive = statusFilter !== 'all'
        try {
          const [missions, unfilteredAlerts] = await Promise.all([
            listMarketplaceMissions(apiKey),
            filtersActive ? listMarketplaceAlerts(apiKey) : Promise.resolve<MarketplaceAlert[]>([]),
          ])
          setEmptyContext(alertsEmptyContext(missions, unfilteredAlerts.length, filtersActive))
        } catch (contextError) {
          setEmptyContext(emptyContextUnavailable(contextError))
        }
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load Marketplace alerts')
    } finally {
      setLoading(false)
    }
  }, [apiKey, statusFilter])

  useEffect(() => {
    void load()
  }, [load])

  async function handleStatus(alertId: string, status: string) {
    setError(null)
    try {
      await updateMarketplaceAlert(apiKey, alertId, status)
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Alert update failed')
    }
  }

  function clearAlertFilters() {
    setStatusFilter('all')
  }

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Marketplace Alerts</h2>
            <p className="text-sm text-muted-foreground">
              Immediate strong-match alerts and material listing changes that need review.
            </p>
          </div>
          <Button variant="outline" onClick={() => void load()} disabled={loading}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>

        {error ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Filter</CardTitle>
            <CardDescription>Focus on new alerts or the full alert history.</CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All alerts</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="acknowledged">Acknowledged</SelectItem>
                <SelectItem value="dismissed">Dismissed</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {loading && alerts.length === 0 ? (
            <div className="flex items-center justify-center p-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : alerts.length === 0 ? (
            <AlertsEmptyState
              context={emptyContext}
              onClearFilters={clearAlertFilters}
              onRefresh={() => void load()}
            />
          ) : (
            alerts.map((alert) => (
              <Card key={alert.alert_id}>
                <CardContent className="space-y-4 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-medium">{alert.match_title || 'Marketplace match'}</h3>
                        <Badge variant={alertVariant(alert.status)}>{alert.status}</Badge>
                        {alert.decision_band ? <Badge variant="outline">{alert.decision_band}</Badge> : null}
                      </div>
                      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                        {alert.price ? <span>{alert.price}</span> : null}
                        {alert.location ? <span>{alert.location}</span> : null}
                        {alert.mission_name ? <span>Mission: {alert.mission_name}</span> : null}
                        <span>Created: {formatClock(alert.created_at)}</span>
                      </div>
                    </div>
                    {alert.listing_url ? (
                      <Button variant="outline" size="sm" asChild>
                        <a href={alert.listing_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="mr-2 h-3.5 w-3.5" />
                          Open Listing
                        </a>
                      </Button>
                    ) : null}
                  </div>

                  <div className="rounded-md bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                    Trigger: {alert.trigger_reason}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => void handleStatus(alert.alert_id, 'acknowledged')}>
                      Acknowledge
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => void handleStatus(alert.alert_id, 'dismissed')}>
                      Dismiss
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
