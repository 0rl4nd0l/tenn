'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Search, Newspaper, ChevronDown, ChevronUp, Database, ExternalLink, Calendar, CheckCircle2, AlertTriangle, CircleHelp } from 'lucide-react'
import { useCockpitStore } from '@/lib/cockpit-store'
import {
  getNewsEvidenceEnvelopeLabels,
  getNewsReadiness,
  getNewsResultReadiness,
  type NewsActionabilityResult,
  type NewsActionabilityTone,
  type NewsReadiness,
  type NewsResultReadiness,
} from '@/lib/cockpit-news-actionability'
import { cn } from '@/lib/utils'
import { Field, FieldLabel } from '@/components/ui/field'

function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`
  return `${Math.floor(diffMs / 86400000)}d ago`
}

function actionabilityToneClass(tone: NewsActionabilityTone): string {
  if (tone === 'ready') return 'border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400'
  if (tone === 'error') return 'border-destructive/30 bg-destructive/10 text-destructive'
  if (tone === 'warning') return 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
  return 'border-border bg-muted text-muted-foreground'
}

function actionabilityIcon(tone: NewsActionabilityTone) {
  if (tone === 'ready') return <CheckCircle2 className="h-3.5 w-3.5" />
  if (tone === 'error') return <AlertTriangle className="h-3.5 w-3.5" />
  if (tone === 'warning') return <AlertTriangle className="h-3.5 w-3.5" />
  return <CircleHelp className="h-3.5 w-3.5" />
}

function stringArray(value: unknown): string[] {
  if (typeof value === 'string') {
    return value.trim() ? [value.trim()] : []
  }
  if (!Array.isArray(value)) {
    return []
  }
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}

function optionalString(value: unknown): string | undefined {
  const text = String(value || '').trim()
  return text || undefined
}

function optionalNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : undefined
  }
  return undefined
}

function formatEvidenceEnvelopeLabel(label: string): string {
  if (label === 'DATA_MISSING:evidence_envelope') {
    return 'DATA_MISSING evidence envelope'
  }
  return label
    .replace(/:/g, ': ')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function NewsReadinessPanel({ readiness }: { readiness: NewsReadiness }) {
  return (
    <Card className={cn('border', actionabilityToneClass(readiness.tone))}>
      <CardContent className="py-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1.5 text-xs font-mono uppercase">
                {actionabilityIcon(readiness.tone)}
                News evidence state
              </span>
              <Badge variant="outline" className={cn('text-[10px] font-mono', actionabilityToneClass(readiness.tone))}>
                {readiness.label}
              </Badge>
            </div>
            <p className="text-sm text-foreground">{readiness.detail}</p>
            {readiness.duplicateGroups.length > 0 && (
              <div className="space-y-1 text-xs text-muted-foreground">
                {readiness.duplicateGroups.slice(0, 3).map((group) => (
                  <div key={group.key}>
                    {group.count}x {group.headline}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 sm:justify-end">
            {readiness.stats.map((stat) => (
              <Badge key={stat} variant="outline" className="text-[10px] font-mono">
                {stat}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function NewsResultActionabilityBadge({ readiness }: { readiness: NewsResultReadiness }) {
  return (
    <Badge
      variant="outline"
      className={cn('text-[10px] font-mono gap-1', actionabilityToneClass(readiness.tone))}
      title={readiness.detail}
    >
      {readiness.label}
    </Badge>
  )
}

interface NewsResultProps {
  result: NewsActionabilityResult
  results: NewsActionabilityResult[]
}

function NewsResult({ result, results }: NewsResultProps) {
  const [isOpen, setIsOpen] = useState(false)
  const readiness = getNewsResultReadiness(result, results)
  const evidenceEnvelopeLabels = getNewsEvidenceEnvelopeLabels(result)
  const primaryEnvelopeLabel = evidenceEnvelopeLabels[0]

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className={cn(
        'p-4 rounded-lg border border-border bg-card transition-colors',
        isOpen && 'border-primary/30'
      )}>
        <CollapsibleTrigger asChild>
          <div className="cursor-pointer">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {result.ticker && (
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {result.ticker}
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">{result.source}</span>
                  <span className="text-xs text-muted-foreground">|</span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {result.publishedAtMissing ? 'date missing' : formatTimeAgo(result.date)}
                  </span>
                </div>
                <h3 className="font-medium text-sm line-clamp-2">{result.headline}</h3>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge 
                  variant={result.relevanceScore > 0.8 ? 'default' : 'secondary'} 
                  className="text-[10px] font-mono"
                >
                  {(result.relevanceScore * 100).toFixed(0)}%
                </Badge>
                <NewsResultActionabilityBadge readiness={readiness} />
                {primaryEnvelopeLabel && (
                  <Badge
                    variant="outline"
                    className={cn(
                      'hidden text-[10px] font-mono sm:inline-flex',
                      primaryEnvelopeLabel.startsWith('DATA_MISSING')
                        ? 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                        : 'border-border bg-muted text-muted-foreground',
                    )}
                    title="Evidence envelope"
                  >
                    {formatEvidenceEnvelopeLabel(primaryEnvelopeLabel)}
                  </Badge>
                )}
                {isOpen ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </div>
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-4 pt-4 border-t border-border">
            {result.content && (
              <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                {result.content}
              </p>
            )}
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
              {readiness.detail}
            </p>
            <div aria-label="Evidence envelope" className="mb-3 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-mono uppercase text-muted-foreground">Evidence envelope</span>
              {evidenceEnvelopeLabels.map((label) => (
                <Badge
                  key={label}
                  variant="outline"
                  className={cn(
                    'text-[10px] font-mono',
                    label.startsWith('DATA_MISSING')
                      ? 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                      : 'border-border bg-muted text-muted-foreground',
                  )}
                >
                  {formatEvidenceEnvelopeLabel(label)}
                </Badge>
              ))}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {result.publishedAtMissing
                  ? 'published_at DATA_MISSING'
                  : `${result.date.toLocaleDateString()} at ${result.date.toLocaleTimeString()}`}
              </span>
              {result.url && (
                <Button variant="outline" size="sm" className="h-7 text-xs" asChild>
                  <a href={result.url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Open Source
                  </a>
                </Button>
              )}
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

export function NewsScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker } = useCockpitStore()
  
  const [query, setQuery] = useState('')
  const [ticker, setTicker] = useState('')
  const [lookback, setLookback] = useState('7d')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<NewsActionabilityResult[] | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchBackend, setSearchBackend] = useState<'qdrant' | 'sqlite'>('qdrant')

  // Wait for hydration to avoid SSR/CSR mismatch
  useEffect(() => {
    setHasHydrated(true)
    if (activeTicker) {
      setTicker(activeTicker)
    }
  }, [activeTicker])

  interface NewsChunkHit {
    score: number
    payload: {
      title?: string
      text?: string
      url?: string
      ticker?: string
      provider?: string
      published_at?: string
      chunk_id?: string
      source_label?: string
      evidence_label?: string
      evidence_labels?: unknown
      source_coverage_status?: string
      source_label_taxonomy_version?: string
      claim_verified_source_count?: number | string
    }
  }

  function mapHitsToNews(hits: NewsChunkHit[]): NewsActionabilityResult[] {
    return hits.map((h, i) => {
      const publishedAt = h.payload.published_at ? new Date(h.payload.published_at) : null
      const publishedAtMissing = !publishedAt || !Number.isFinite(publishedAt.getTime())
      return {
        id: h.payload.chunk_id || `news-${i}-${Date.now()}`,
        headline: h.payload.title || (h.payload.text || '').split('\n')[0].slice(0, 120),
        source: h.payload.provider || 'news',
        date: publishedAtMissing ? new Date(0) : publishedAt,
        relevanceScore: h.score,
        ticker: h.payload.ticker || undefined,
        content: h.payload.text || undefined,
        url: h.payload.url || undefined,
        sourceLabel: optionalString(h.payload.source_label || h.payload.evidence_label),
        evidenceLabels: stringArray(h.payload.evidence_labels),
        sourceCoverageStatus: optionalString(h.payload.source_coverage_status),
        sourceLabelTaxonomyVersion: optionalString(h.payload.source_label_taxonomy_version),
        claimVerifiedSourceCount: optionalNumber(h.payload.claim_verified_source_count),
        publishedAtMissing,
      }
    })
  }

  const newsReadiness = getNewsReadiness({ query, isSearching, searchError, results })

  const handleSearch = async () => {
    if (!query.trim()) return

    setIsSearching(true)
    setResults(null)
    setSearchError(null)

    try {
      const res = await fetch('/rag/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
        },
        body: JSON.stringify({
          query: query.trim(),
          source: 'news',
          ticker: ticker || undefined,
          top_k: 20,
        }),
      })

      if (!res.ok) {
        const body = await res.text()
        throw new Error(`${res.status} ${res.statusText}: ${body}`)
      }

      const data: { results: NewsChunkHit[] } = await res.json()
      const mapped = mapHitsToNews(data.results || [])

      setResults(mapped)
      setSearchBackend('qdrant')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Search request failed'
      setSearchError(message)
      setResults([])
    } finally {
      setIsSearching(false)
    }
  }

  if (!hasHydrated) return null

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-4xl mx-auto">
        {/* Search Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Search className="h-5 w-5 text-primary" />
              News Search
            </CardTitle>
            <CardDescription>
              Semantic search over news and announcements
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                placeholder="Search news articles..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1"
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} disabled={!query.trim() || isSearching}>
                <Search className="h-4 w-4 mr-2" />
                {isSearching ? 'Searching...' : 'Search'}
              </Button>
            </div>

            <div className="flex flex-wrap gap-4">
              <Field className="w-[150px]">
                <FieldLabel>Ticker Filter</FieldLabel>
                <Input
                  placeholder="e.g., BHP"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="font-mono"
                />
              </Field>

              <Field className="w-[150px]">
                <FieldLabel>Lookback</FieldLabel>
                <Select value={lookback} onValueChange={setLookback}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="24h">24 Hours</SelectItem>
                    <SelectItem value="7d">7 Days</SelectItem>
                    <SelectItem value="30d">30 Days</SelectItem>
                    <SelectItem value="all">All Time</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            </div>
          </CardContent>
        </Card>

        <NewsReadinessPanel readiness={newsReadiness} />

        {/* Results */}
        {/* Error Banner */}
        {searchError && (
          <Card className="border-destructive/50">
            <CardContent className="py-4">
              <p className="text-sm text-destructive">Search failed: {searchError}</p>
            </CardContent>
          </Card>
        )}

        {results && (
          <div className="space-y-4">
            {/* Results Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Newspaper className="h-5 w-5 text-primary" />
                <span className="font-medium">{results.length} Results</span>
              </div>
              <Badge variant="outline" className="text-xs gap-1">
                <Database className="h-3 w-3" />
                {searchBackend === 'qdrant' ? 'Qdrant' : 'SQLite Fallback'}
              </Badge>
            </div>

            {/* Results List */}
            {results.length > 0 ? (
              <div className="space-y-3">
                {results.map((result) => (
                  <NewsResult key={result.id} result={result} results={results} />
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center text-muted-foreground">
                    <Newspaper className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No results found for your search</p>
                    <p className="text-sm mt-1">Try adjusting your filters or search terms</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Empty State */}
        {!results && !isSearching && (
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-muted-foreground">
                <Search className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Enter a search query to find news articles</p>
                <p className="text-sm mt-1">Search recent company or market news. Try a ticker like A2M or a topic like lithium pricing.</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ScrollArea>
  )
}
