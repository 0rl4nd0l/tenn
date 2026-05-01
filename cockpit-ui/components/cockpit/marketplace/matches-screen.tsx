'use client'

import { useEffect, useState, useCallback } from 'react'
import { ExternalLink, ImageOff, RefreshCw } from 'lucide-react'
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
import { priceEvidenceForMatch, priceSourceLabel } from './price-evidence'

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

function valueBadgeVariant(
  label: string | null | undefined,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  const normalized = String(label || '').toLowerCase()
  if (normalized.includes('good') || normalized.includes('strong')) return 'default'
  if (normalized.includes('overpriced') || normalized.includes('poor')) return 'destructive'
  if (normalized.includes('unavailable') || normalized.includes('insufficient')) return 'outline'
  return 'secondary'
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

export function MarketplaceMatchesScreen({ apiKey }: MarketplaceMatchesScreenProps) {
  const [matches, setMatches] = useState<MarketplaceMatch[]>([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [bandFilter, setBandFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
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
            {matches.map((match) => {
              const media = listingMedia(match)
              const firstMedia = media[0] ?? null
              const priceEvidence = priceEvidenceForMatch(match)
              return (
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
                            {MATCH_STATUS_OPTIONS.map((option) => (
                              <SelectItem key={option.value} value={option.value} className="text-[10px]">
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pb-4">
                  <div className="mb-3 overflow-hidden rounded-md border border-border/60 bg-muted/20">
                    {firstMedia ? (
                      <img
                        src={firstMedia}
                        alt={`Listing photo for ${match.title}`}
                        className="h-40 w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-24 items-center justify-center gap-2 text-xs text-muted-foreground">
                        <ImageOff className="h-4 w-4" />
                        Listing photos unavailable
                      </div>
                    )}
                  </div>
                  <div className="mb-3">
                    <Badge variant="outline" className="text-[10px]">
                      photos: {media.length}
                    </Badge>
                    <Badge variant="outline" className="ml-2 text-[10px]">
                      {priceSourceLabel(priceEvidence)}
                    </Badge>
                  </div>
                  {priceEvidence?.warning && (
                    <p className="mb-3 text-[11px] text-amber-700 dark:text-amber-300">
                      {priceEvidence.warning}
                    </p>
                  )}
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
                  {match.value_context && (
                    <div className="mt-3 rounded-md border border-primary/20 bg-primary/5 p-3 text-[11px]">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
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
                      <div className="grid gap-1 sm:grid-cols-2">
                        <div>
                          Product:{' '}
                          <span className="font-medium">
                            {match.value_context.matched_candidate_name
                              || match.value_context.linked_tracked_product_name
                              || 'linked product'}
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
                      {match.value_context.explanation && (
                        <p className="mt-2 text-[11px] text-muted-foreground">
                          {match.value_context.explanation}
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
                    <div className="mt-3 rounded-md border border-border/60 bg-muted/20 p-3 text-[11px]">
                      <div className="mb-1 font-medium">New retail benchmark ({match.benchmark.source})</div>
                      <div className="grid gap-1 sm:grid-cols-2">
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
