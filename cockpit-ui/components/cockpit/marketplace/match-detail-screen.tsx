'use client'

import { useEffect, useState, useCallback } from 'react'
import { ArrowLeft, ExternalLink, RefreshCw } from 'lucide-react'
import Link from 'next/link'

import { getMarketplaceMatch, type MarketplaceMatch } from '@/lib/marketplace-api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

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

export function MarketplaceMatchDetailScreen({
  apiKey,
  matchId,
}: MarketplaceMatchDetailScreenProps) {
  const [match, setMatch] = useState<MarketplaceMatch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!apiKey || !matchId) return
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
                {match.listing_url && (
                  <Button variant="secondary" size="sm" asChild>
                    <a href={match.listing_url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View Listing
                    </a>
                  </Button>
                )}
              </CardHeader>
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
                  </dl>
                </CardContent>
              </Card>
            </div>

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
