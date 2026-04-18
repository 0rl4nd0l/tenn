'use client'

import { useEffect, useState, useCallback } from 'react'
import { ExternalLink, RefreshCw } from 'lucide-react'

import {
  listMarketplaceAlerts,
  type MarketplaceAlert,
  updateMarketplaceAlert,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface MarketplaceAlertsScreenProps {
  apiKey: string
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

export function MarketplaceAlertsScreen({ apiKey }: MarketplaceAlertsScreenProps) {
  const [alerts, setAlerts] = useState<MarketplaceAlert[]>([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const items = await listMarketplaceAlerts(apiKey, statusFilter === 'all' ? undefined : statusFilter)
      setAlerts(items)
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
          {alerts.length === 0 ? (
            <div className="rounded-md border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
              No Marketplace alerts found for the selected filter.
            </div>
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
