'use client'

import { useEffect, useState, useCallback } from 'react'
import { ExternalLink, RefreshCw } from 'lucide-react'
import Link from 'next/link'

import {
  listMarketplaceMatches,
  type MarketplaceMatch,
  updateMarketplaceMatch,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface MarketplaceMatchesScreenProps {
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

function decisionVariant(
  decisionBand: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (decisionBand === 'strong_match') return 'default'
  if (decisionBand === 'candidate') return 'secondary'
  if (decisionBand === 'reject') return 'destructive'
  return 'outline'
}

export function MarketplaceMatchesScreen({ apiKey }: MarketplaceMatchesScreenProps) {
  const [matches, setMatches] = useState<MarketplaceMatch[]>([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [bandFilter, setBandFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    setError(null)
    try {
      const items = await listMarketplaceMatches(apiKey, {
        status: statusFilter === 'all' ? undefined : statusFilter,
        decisionBand: bandFilter === 'all' ? undefined : bandFilter,
      })
      setMatches(items)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load Marketplace matches')
    } finally {
      setLoading(false)
    }
  }, [apiKey, statusFilter, bandFilter])

  useEffect(() => {
    void load()
  }, [load])

  async function handleStatus(matchId: string, status: string) {
    if (!apiKey) return
    setError(null)
    try {
      await updateMarketplaceMatch(apiKey, matchId, status)
      await load()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Match update failed')
    }
  }

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
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
                <SelectItem value="pending" className="text-xs">Pending</SelectItem>
                <SelectItem value="reviewed" className="text-xs">Reviewed</SelectItem>
                <SelectItem value="dismissed" className="text-xs">Dismissed</SelectItem>
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
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading && matches.length === 0 ? (
          <div className="flex items-center justify-center p-20">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : matches.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-20 text-center space-y-4">
            <RefreshCw className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-muted-foreground">No matches found for the current filters.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {matches.map((match) => (
              <Card key={match.match_id} className="overflow-hidden transition-colors hover:bg-muted/5">
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={decisionVariant(match.decision_band)}>
                          {match.decision_band.replace('_', ' ')}
                        </Badge>
                        <Badge variant="outline" className="font-mono text-[10px]">
                          Score: {match.score}
                        </Badge>
                      </div>
                      <CardTitle className="pt-1 text-base">{match.title}</CardTitle>
                      <CardDescription className="text-xs">{match.mission_name || 'Marketplace Match'}</CardDescription>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {formatClock(match.captured_at)}
                      </span>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-xs">
                          <Link href={`/marketplace/matches/${match.match_id}`}>
                            Details
                          </Link>
                        </Button>
                        <Select
                          value={match.status}
                          onValueChange={(val) => void handleStatus(match.match_id, val)}
                        >
                          <SelectTrigger className="h-7 w-[100px] text-[10px] font-medium">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="pending" className="text-[10px]">Pending</SelectItem>
                            <SelectItem value="reviewed" className="text-[10px]">Reviewed</SelectItem>
                            <SelectItem value="dismissed" className="text-[10px]">Dismissed</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pb-4">
                  {match.reasons_for && match.reasons_for.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-1">
                      {match.reasons_for.map((reason, i) => (
                        <Badge key={i} variant="secondary" className="text-[9px] px-1.5 h-4 font-normal">
                          {reason}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap items-center gap-4 text-xs">
                    {match.price && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-muted-foreground">Price:</span>
                        <span className="font-mono font-bold text-primary">{match.price}</span>
                      </div>
                    )}
                    {match.location && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-muted-foreground">Loc:</span>
                        <span>{match.location}</span>
                      </div>
                    )}
                    {match.listing_url && (
                      <a
                        href={match.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        View Listing
                      </a>
                    ) || (
                      <span className="text-muted-foreground font-mono">ID: {match.listing_id.slice(0, 12)}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
