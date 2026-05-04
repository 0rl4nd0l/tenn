'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { ArrowLeft, ExternalLink, ImageOff, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react'
import Link from 'next/link'

import {
  getMarketplaceMatch,
  reviewMarketplaceBenchmarkMatch,
  type MarketplaceMatch,
  type MarketplaceMatchFeedbackValue,
  type MarketplacePriceComparison,
  updateMarketplaceMatchFeedback,
} from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { priceEvidenceForMatch, priceSourceLabel } from './price-evidence'

interface MarketplaceMatchDetailScreenProps {
  apiKey: string
  matchId: string
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

export function MarketplaceMatchDetailScreen({
  apiKey,
  matchId,
}: MarketplaceMatchDetailScreenProps) {
  const [match, setMatch] = useState<MarketplaceMatch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reviewSaving, setReviewSaving] = useState(false)
  const [feedbackSaving, setFeedbackSaving] = useState(false)
  const [pendingFeedback, setPendingFeedback] = useState<MarketplaceMatchFeedbackValue | null>(null)
  const [pendingNote, setPendingNote] = useState('')
  const noteRef = useRef<HTMLTextAreaElement>(null)
  const media = match ? listingMedia(match) : []
  const priceEvidence = match ? priceEvidenceForMatch(match) : null

  const load = useCallback(async () => {
    if (!matchId) {
      setLoading(false)
      setError('Marketplace match ID is missing')
      return
    }
    setLoading(true)
    setError(null)
    try {
      setMatch(await getMarketplaceMatch(apiKey, matchId))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load Marketplace match')
    } finally {
      setLoading(false)
    }
  }, [apiKey, matchId])

  useEffect(() => {
    void load()
  }, [load])

  async function handleBenchmarkReview(reviewStatus: 'accepted' | 'rejected' | 'pending_review') {
    if (!matchId) return
    setReviewSaving(true)
    setError(null)
    try {
      const updated = await reviewMarketplaceBenchmarkMatch(apiKey, matchId, {
        review_status: reviewStatus,
      })
      setMatch(updated)
    } catch (reviewError) {
      setError(
        reviewError instanceof Error
          ? reviewError.message
          : 'Failed to update benchmark review status',
      )
    } finally {
      setReviewSaving(false)
    }
  }

  function handleFeedback(feedback: MarketplaceMatchFeedbackValue) {
    if (pendingFeedback === feedback) {
      setPendingFeedback(null)
      setPendingNote('')
      return
    }
    setPendingFeedback(feedback)
    setPendingNote('')
    setTimeout(() => noteRef.current?.focus(), 0)
  }

  async function confirmFeedback() {
    if (!matchId || !pendingFeedback) return
    setFeedbackSaving(true)
    setError(null)
    const feedback = pendingFeedback
    const note = pendingNote.trim() || null
    setPendingFeedback(null)
    setPendingNote('')
    try {
      setMatch(await updateMarketplaceMatchFeedback(apiKey, matchId, feedback, note))
    } catch (feedbackError) {
      setError(
        feedbackError instanceof Error
          ? feedbackError.message
          : 'Failed to update match feedback',
      )
    } finally {
      setFeedbackSaving(false)
    }
  }

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/marketplace/matches">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Matches
              </Link>
            </Button>
            <div>
              <h2 className="text-xl font-semibold">Marketplace Match Detail</h2>
              <p className="text-sm text-muted-foreground">
                Score breakdown, evidence, and review context for one saved Marketplace match.
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading && !match ? (
          <div className="flex items-center justify-center p-20">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : match ? (
          <div className="grid gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Listing Photos</CardTitle>
                <CardDescription>Marketplace listing media captured with this match.</CardDescription>
              </CardHeader>
              <CardContent>
                {media.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {media.map((src, index) => (
                      <a
                        key={`${src}-${index}`}
                        href={src}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="relative flex items-center justify-center overflow-hidden rounded-md border border-border/60 bg-muted/30 transition-colors hover:bg-muted/40"
                      >
                        <img
                          src={src}
                          alt={`Listing photo ${index + 1} for ${match.title}`}
                          className="max-h-[600px] w-full object-contain"
                        />
                      </a>
                    ))}
                  </div>
                ) : (
                  <div className="flex h-32 items-center justify-center gap-2 rounded-md border border-dashed text-sm text-muted-foreground">
                    <ImageOff className="h-4 w-4" />
                    Listing photos unavailable for this capture.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={decisionVariant(match.decision_band)}>
                      {match.decision_band.replace('_', ' ')}
                    </Badge>
                    <Badge variant="outline" className="font-mono">
                      Score: {match.score}
                    </Badge>
                  </div>
                  <CardTitle className="pt-2 text-2xl font-bold">{match.title}</CardTitle>
                  <CardDescription className="font-mono text-xs">
                    Match ID: {match.match_id} | Captured: {formatClock(match.captured_at)}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    variant={
                      pendingFeedback === 'interested' || match.user_feedback?.feedback === 'interested'
                        ? 'default'
                        : 'outline'
                    }
                    size="sm"
                    disabled={feedbackSaving}
                    onClick={() => handleFeedback('interested')}
                  >
                    <ThumbsUp className="mr-2 h-4 w-4" />
                    Interested
                  </Button>
                  <Button
                    variant={
                      pendingFeedback === 'not_interested' || match.user_feedback?.feedback === 'not_interested'
                        ? 'secondary'
                        : 'outline'
                    }
                    size="sm"
                    disabled={feedbackSaving}
                    onClick={() => handleFeedback('not_interested')}
                  >
                    <ThumbsDown className="mr-2 h-4 w-4" />
                    Not interested
                  </Button>
                  {match.listing_url && (
                    <Button variant="secondary" size="sm" asChild>
                      <a href={match.listing_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        View Listing
                      </a>
                    </Button>
                  )}
                </div>
              </CardHeader>

              {/* Inline note panel */}
              {pendingFeedback && (
                <div className="border-t border-border/50 bg-muted/10 px-6 py-4 flex flex-col gap-3">
                  <p className="text-sm text-muted-foreground">
                    {pendingFeedback === 'not_interested'
                      ? 'Why not? (optional — helps the system learn what to avoid)'
                      : 'What do you like about this? (optional)'}
                  </p>
                  <Textarea
                    ref={noteRef}
                    rows={2}
                    placeholder={
                      pendingFeedback === 'not_interested'
                        ? 'e.g. wrong brand, too old, price too high…'
                        : 'e.g. great condition, good price for spec…'
                    }
                    value={pendingNote}
                    onChange={(e) => setPendingNote(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void confirmFeedback()
                      if (e.key === 'Escape') { setPendingFeedback(null); setPendingNote('') }
                    }}
                    className="text-sm resize-none"
                  />
                  <div className="flex items-center gap-2">
                    <Button size="sm" onClick={() => void confirmFeedback()} disabled={feedbackSaving}>
                      Confirm
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => { setPendingFeedback(null); setPendingNote('') }}
                    >
                      Cancel
                    </Button>
                    <span className="text-xs text-muted-foreground">⌘↵ to confirm · Esc to cancel</span>
                  </div>
                </div>
              )}

              {/* Existing note */}
              {!pendingFeedback && match.user_feedback?.note && (
                <div className="border-t border-border/50 bg-muted/5 px-6 py-3">
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium">Your note:</span> {match.user_feedback.note}
                  </p>
                </div>
              )}

              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      Reasons For Match
                    </h3>
                    <ul className="mt-2 list-inside list-disc space-y-1 text-sm">
                      {match.reasons_for.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                  {match.reasons_against.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                        Reasons Against
                      </h3>
                      <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-muted-foreground">
                        {match.reasons_against.map((reason, i) => (
                          <li key={i}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Metadata & Context</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-y-2 text-sm">
                    {Object.entries(match.metadata).map(([key, value]) => (
                      <div key={key} className="flex justify-between border-b border-border/40 py-1 last:border-0">
                        <dt className="text-muted-foreground">{key}</dt>
                        <dd className="font-mono text-xs font-medium">{String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Listing Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-y-2 text-sm">
                    <div className="flex justify-between border-b border-border/40 py-1">
                      <dt className="text-muted-foreground">Mission</dt>
                      <dd className="font-medium">{match.mission_name || match.mission_id}</dd>
                    </div>
                    <div className="flex justify-between border-b border-border/40 py-1">
                      <dt className="text-muted-foreground">Seller</dt>
                      <dd className="font-medium">{match.seller_name || 'Unknown'}</dd>
                    </div>
                    <div className="flex justify-between border-b border-border/40 py-1">
                      <dt className="text-muted-foreground">Location</dt>
                      <dd className="font-medium">{match.location || 'Unknown'}</dd>
                    </div>
                    <div className="flex justify-between py-1">
                      <dt className="text-muted-foreground">Price</dt>
                      <dd className="font-mono font-bold text-primary">{match.price || 'n/a'}</dd>
                    </div>
                    <div className="flex justify-between border-t border-border/40 py-1">
                      <dt className="text-muted-foreground">Price source</dt>
                      <dd className="font-mono text-xs">{priceSourceLabel(priceEvidence)}</dd>
                    </div>
                  </dl>
                  {priceEvidence?.warning && (
                    <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">
                      {priceEvidence.warning}
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            {match.price_comparison && (
              <Card className={`border ${comparisonToneClass(match.price_comparison)}`}>
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">Price Comparison</CardTitle>
                      <CardDescription>
                        Backend-computed listing price against used-market and retail/RRP anchors.
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="bg-background/70">
                      {verdictLabel(match.price_comparison.verdict)}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 text-sm md:grid-cols-4">
                  <div>
                    <div className="text-xs text-muted-foreground">Listing</div>
                    <div className="font-mono text-lg font-semibold">
                      {formatCurrency(match.price_comparison.listing_price)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Marketplace avg</div>
                    <div className="font-mono text-lg font-semibold">
                      {formatCurrency(match.price_comparison.used_market_median)}
                    </div>
                    <div className="font-mono text-xs">
                      {formatDelta(match.price_comparison.delta_vs_used_median?.percent)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">
                      Retail/RRP{match.price_comparison.retail_anchor_label
                        ? ` (${match.price_comparison.retail_anchor_label})`
                        : ''}
                    </div>
                    <div className="font-mono text-lg font-semibold">
                      {formatCurrency(match.price_comparison.retail_anchor_price)}
                    </div>
                    <div className="font-mono text-xs">
                      {formatDelta(match.price_comparison.delta_vs_retail_anchor?.percent)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Fair range</div>
                    <div className="font-mono text-sm font-semibold">
                      {typeof match.price_comparison.fair_range_low === 'number' &&
                      typeof match.price_comparison.fair_range_high === 'number'
                        ? `${formatCurrency(match.price_comparison.fair_range_low)} - ${formatCurrency(match.price_comparison.fair_range_high)}`
                        : 'n/a'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Text Snapshot</CardTitle>
                <CardDescription>Raw text extracted from the marketplace listing</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="whitespace-pre-wrap rounded bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-300">
                  {match.raw_text_snapshot}
                </pre>
              </CardContent>
            </Card>

            {match.value_context && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Used-Market Value</CardTitle>
                  <CardDescription>
                    {match.value_context.value_source === 'matched_candidate_benchmark'
                      ? 'Value overlay from the matched candidate benchmark snapshot.'
                      : 'Value overlay from the mission primary tracked product benchmark snapshot.'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={valueBadgeVariant(match.value_context.value_label)}>
                      {match.value_context.value_label}
                    </Badge>
                    <Badge variant="outline">
                      confidence: {match.value_context.value_confidence}
                    </Badge>
                    <Badge variant="outline">
                      state: {match.value_context.state.replace(/_/g, ' ')}
                    </Badge>
                    {typeof match.value_context.value_score === 'number' && (
                      <Badge variant="outline" className="font-mono">
                        value score: {match.value_context.value_score}
                      </Badge>
                    )}
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      Linked product:{' '}
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
                      Benchmark snapshot:{' '}
                      <span className="font-mono">
                        {match.value_context.benchmark_snapshot_id || 'n/a'}
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
                    <div>
                      Retail anchor:{' '}
                      <span className="font-mono">
                        {formatCurrency(match.value_context.retail_anchor_price)}
                      </span>
                    </div>
                    <div>
                      Benchmark freshness:{' '}
                      <span className="font-mono">
                        {match.value_context.benchmark_freshness_status || 'unknown'}
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
                    {typeof match.value_context.requirement_fit_score === 'number' && (
                      <div>
                        Requirement fit:{' '}
                        <span className="font-mono">
                          {Math.round(match.value_context.requirement_fit_score)}
                        </span>
                      </div>
                    )}
                  </div>

                  {match.value_context.price_movement_summary && (
                    <p className="text-sm text-muted-foreground">
                      {match.value_context.price_movement_summary}
                    </p>
                  )}
                  {match.value_context.explanation && (
                    <p className="text-sm text-muted-foreground">
                      {match.value_context.explanation}
                    </p>
                  )}
                  {match.value_context.warnings && match.value_context.warnings.length > 0 && (
                    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                      {match.value_context.warnings.join(' ')}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {match.benchmark && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">New Retail Benchmark Overlay</CardTitle>
                  <CardDescription>
                    Centre Com comparison for operational pricing context only.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      Matched product:{' '}
                      <span className="font-medium">
                        {match.benchmark.matched_product || 'No confident product match'}
                      </span>
                    </div>
                    <div>
                      Match confidence:{' '}
                      <span className="font-mono">
                        {Math.round(match.benchmark.confidence * 100)}%
                      </span>
                    </div>
                    <div>
                      Current Centre Com:{' '}
                      <span className="font-mono">
                        {typeof match.benchmark.current_price === 'number'
                          ? `$${Math.round(match.benchmark.current_price)}`
                          : 'n/a'}
                      </span>
                    </div>
                    <div>
                      30-day median:{' '}
                      <span className="font-mono">
                        {typeof match.benchmark.median_30d === 'number'
                          ? `$${Math.round(match.benchmark.median_30d)}`
                          : 'n/a'}
                      </span>
                    </div>
                    <div>
                      Listing delta:{' '}
                      <span className="font-mono">
                        {typeof match.benchmark.listing_delta_pct === 'number'
                          ? `${Math.round(match.benchmark.listing_delta_pct * 10) / 10}%`
                          : 'n/a'}
                      </span>
                    </div>
                    <div>
                      Freshness:{' '}
                      <span className="font-mono">
                        {typeof match.benchmark.freshness_hours === 'number'
                          ? `${Math.round(match.benchmark.freshness_hours)}h`
                          : 'unknown'}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={match.benchmark.low_confidence ? 'destructive' : 'secondary'}>
                      {match.benchmark.low_confidence ? 'low confidence' : 'high confidence'}
                    </Badge>
                    <Badge variant="outline">
                      review: {match.benchmark.review_status || 'pending_review'}
                    </Badge>
                    <Badge variant="outline">
                      wording: {match.benchmark.wording || 'new retail benchmark'}
                    </Badge>
                  </div>

                  {match.benchmark.warning && (
                    <p className="text-sm text-destructive">{match.benchmark.warning}</p>
                  )}

                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={reviewSaving}
                      onClick={() => void handleBenchmarkReview('accepted')}
                    >
                      Mark Match Accepted
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={reviewSaving}
                      onClick={() => void handleBenchmarkReview('rejected')}
                    >
                      Mark Match Rejected
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={reviewSaving}
                      onClick={() => void handleBenchmarkReview('pending_review')}
                    >
                      Return to Pending Review
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-20 text-center space-y-4">
            <RefreshCw className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-muted-foreground">Match details unavailable.</p>
          </div>
        )}
      </div>
    </div>
  )
}
