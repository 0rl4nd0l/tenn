'use client'

import { useEffect, useState, useCallback } from 'react'
import { ExternalLink, ImageOff, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react'
import Link from 'next/link'

import {
  listMarketplaceMatches,
  type MarketplaceMatch,
  type MarketplaceMatchFeedbackValue,
  type MarketplacePriceComparison,
  updateMarketplaceMatch,
  updateMarketplaceMatchFeedback,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
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

function verdictLabel(value: string | null | undefined): string {
  return String(value || 'unavailable').replace(/_/g, ' ')
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

function ScoreGauge({ score }: { score: number }) {
  const normalizedScore = Math.max(0, Math.min(100, score))
  const radius = 40
  const circumference = Math.PI * radius
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference

  let colorClass = 'text-emerald-500'
  if (normalizedScore < 50) colorClass = 'text-destructive'
  else if (normalizedScore < 75) colorClass = 'text-amber-500'

  return (
    <div className="relative w-32 h-16">
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
        <span className="text-2xl font-bold font-mono tracking-tighter">{normalizedScore}</span>
      </div>
    </div>
  )
}

export function MarketplaceMatchesScreen({ apiKey }: MarketplaceMatchesScreenProps) {
  const [matches, setMatches] = useState<MarketplaceMatch[]>([])
  const [statusFilter, setStatusFilter] = useState('all')
  const [bandFilter, setBandFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [feedbackSavingMatchId, setFeedbackSavingMatchId] = useState<string | null>(null)

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

  async function handleFeedback(matchId: string, feedback: MarketplaceMatchFeedbackValue) {
    setError(null)
    setFeedbackSavingMatchId(matchId)
    try {
      const updated = await updateMarketplaceMatchFeedback(apiKey, matchId, feedback)
      setMatches((current) =>
        current.map((item) => (item.match_id === matchId ? updated : item)),
      )
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Match feedback update failed')
    } finally {
      setFeedbackSavingMatchId(null)
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
              const comparison = match.price_comparison ?? null
              const userFeedback = match.user_feedback?.feedback ?? null
              return (
              <Card key={match.match_id} className="overflow-hidden transition-colors hover:bg-muted/5 border-border/50">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/50 bg-muted/10 px-5 py-3">
                  <div className="flex items-center gap-2">
                    <Badge variant={decisionVariant(match.decision_band)}>
                      {match.decision_band.replace('_', ' ')}
                    </Badge>
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatClock(match.captured_at)}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-xs">
                      <Link href={`/marketplace/matches/${match.match_id}`}>
                        Details
                      </Link>
                    </Button>
                    {match.listing_url && (
                      <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-xs text-primary">
                        <a href={match.listing_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="mr-1 h-3 w-3" />
                          View
                        </a>
                      </Button>
                    )}
                    <Select
                      value={match.status}
                      onValueChange={(val) => void handleStatus(match.match_id, val)}
                    >
                      <SelectTrigger className="h-7 w-[100px] text-xs font-medium">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MATCH_STATUS_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value} className="text-xs">
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant={userFeedback === 'interested' ? 'default' : 'outline'}
                      size="sm"
                      disabled={feedbackSavingMatchId === match.match_id}
                      onClick={() => void handleFeedback(match.match_id, 'interested')}
                      className="h-7 px-2 text-xs"
                    >
                      <ThumbsUp className="mr-1 h-3 w-3" />
                      Interested
                    </Button>
                    <Button
                      variant={userFeedback === 'not_interested' ? 'secondary' : 'outline'}
                      size="sm"
                      disabled={feedbackSavingMatchId === match.match_id}
                      onClick={() => void handleFeedback(match.match_id, 'not_interested')}
                      className="h-7 px-2 text-xs"
                    >
                      <ThumbsDown className="mr-1 h-3 w-3" />
                      Not interested
                    </Button>
                  </div>
                </div>

                <CardContent className="p-0">
                  <div className="grid grid-cols-1 md:grid-cols-[1fr_300px]">
                    {/* Left Column */}
                    <div className="flex flex-col border-r border-border/50">
                      <div className="space-y-1 p-5 pb-4">
                        <h3 className="text-lg font-semibold leading-tight">{match.title}</h3>
                        <div className="text-sm text-muted-foreground">
                          Brand: <span className="font-medium text-foreground">{String(match.metadata?.brand || 'Unknown')}</span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Location: <span className="font-medium text-foreground">{match.location || 'Unknown'}</span>
                        </div>
                      </div>
                      <div className="relative aspect-video w-full overflow-hidden border-t border-border/50 bg-muted/20 p-4">
                        {firstMedia ? (
                          <img
                            src={firstMedia}
                            alt={`Listing photo for ${match.title}`}
                            className="h-full w-full object-contain md:h-64"
                          />
                        ) : (
                          <div className="flex h-32 items-center justify-center gap-2 text-xs text-muted-foreground md:h-64">
                            <ImageOff className="h-4 w-4" />
                            Listing photos unavailable
                          </div>
                        )}
                        <div className="absolute bottom-2 left-2 flex flex-wrap gap-2">
                          <Badge variant="outline" className="text-xs bg-background/80 backdrop-blur-sm">
                            photos: {media.length}
                          </Badge>
                          <Badge variant="outline" className="text-xs bg-background/80 backdrop-blur-sm">
                            {priceSourceLabel(priceEvidence)}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {/* Right Column */}
                    <div className="flex flex-col">
                      <div className="space-y-3 border-b border-border/50 bg-muted/5 p-5">
                        <div className="flex items-baseline justify-between text-sm">
                          <span className="text-muted-foreground">List Price:</span>
                          <span className="text-lg font-semibold text-primary">{match.price || 'N/A'}</span>
                        </div>
                        <div className="flex items-baseline justify-between text-sm">
                          <span className="text-muted-foreground">Avg Price Identical:</span>
                          <span className="font-medium text-foreground">
                            {comparison?.used_market_median ? formatCurrency(comparison.used_market_median) : 'N/A'}
                          </span>
                        </div>
                        <div className="pt-1">
                          <span className="mb-2 block text-xs font-medium text-muted-foreground">Features:</span>
                          <div className="flex flex-wrap gap-1">
                            {match.reasons_for && match.reasons_for.length > 0 ? (
                              match.reasons_for.slice(0, 4).map((reason, i) => (
                                <Badge key={i} variant="secondary" className="h-5 px-1.5 text-xs font-normal">
                                  {reason}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">None listed</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Score Gauge */}
                      <div className="flex grow flex-col items-center justify-center bg-background p-5">
                        <ScoreGauge score={match.score} />
                        <div className="mt-5 max-w-[200px] text-center text-xs text-muted-foreground">
                          {match.value_context?.explanation || match.reasons_for?.[0] || 'Score based on fit and price.'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Additional Context Sections */}
                  {(match.value_context || match.benchmark || comparison || priceEvidence?.warning) && (
                    <div className="border-t border-border/50 bg-muted/5 p-4">
                      {priceEvidence?.warning && (
                        <p className="mb-3 text-xs text-amber-700 dark:text-amber-300">
                          {priceEvidence.warning}
                        </p>
                      )}
                      
                      {comparison && (
                        <div className={`mb-3 rounded-md border p-3 text-xs ${comparisonToneClass(comparison)} bg-background`}>
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className="font-semibold">Price comparison</span>
                            <Badge variant="outline" className="bg-background/70 text-xs">
                              {verdictLabel(comparison.verdict)}
                            </Badge>
                          </div>
                          <div className="grid gap-1 sm:grid-cols-4">
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
                        </div>
                      )}

                      {match.value_context && (
                        <div className="mb-3 rounded-md border border-primary/20 bg-background p-3 text-xs shadow-sm">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className="font-medium">Used-market value</span>
                            <Badge
                              variant={valueBadgeVariant(match.value_context.value_label)}
                              className="text-xs"
                            >
                              {match.value_context.value_label}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              confidence: {match.value_context.value_confidence}
                            </Badge>
                            {typeof match.value_context.value_score === 'number' && (
                              <Badge variant="outline" className="font-mono text-xs">
                                value: {match.value_context.value_score}
                              </Badge>
                            )}
                          </div>
                          <div className="grid gap-1 sm:grid-cols-2">
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
                            <p className="mt-2 text-xs text-muted-foreground">
                              {match.value_context.price_movement_summary}
                            </p>
                          )}
                          {match.value_context.warnings && match.value_context.warnings.length > 0 && (
                            <p className="mt-2 text-xs text-destructive">
                              {match.value_context.warnings.slice(0, 2).join(' ')}
                            </p>
                          )}
                        </div>
                      )}

                      {match.benchmark && (
                        <div className="rounded-md border border-border/60 bg-background p-3 text-xs shadow-sm">
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
                              <Badge variant="outline" className="text-xs">
                                review: {match.benchmark.review_status}
                              </Badge>
                            </div>
                          )}
                          {match.benchmark.warning && (
                            <p className="mt-2 text-xs text-destructive">{match.benchmark.warning}</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
