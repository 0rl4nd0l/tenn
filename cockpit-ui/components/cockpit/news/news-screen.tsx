'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Search, Newspaper, ChevronDown, ChevronUp, Database, ExternalLink, Calendar } from 'lucide-react'
import { useCockpitStore } from '@/lib/cockpit-store'
import type { RagResult } from '@/lib/cockpit-types'
import type { NewsSearchResult } from '@/lib/cockpit-types'
import { cn } from '@/lib/utils'
import { Field, FieldLabel } from '@/components/ui/field'

function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`
  return `${Math.floor(diffMs / 86400000)}d ago`
}

interface NewsResultProps {
  result: NewsSearchResult
}

function NewsResult({ result }: NewsResultProps) {
  const [isOpen, setIsOpen] = useState(false)

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
                    {formatTimeAgo(result.date)}
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
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {result.date.toLocaleDateString()} at {result.date.toLocaleTimeString()}
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
  const { activeTicker, sessionId } = useCockpitStore()
  
  const [query, setQuery] = useState('')
  const [ticker, setTicker] = useState('')
  const [lookback, setLookback] = useState('7d')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<NewsSearchResult[] | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchBackend, setSearchBackend] = useState<'qdrant' | 'sqlite'>('qdrant')

  // Wait for hydration to avoid SSR/CSR mismatch
  useEffect(() => {
    setHasHydrated(true)
    if (activeTicker) {
      setTicker(activeTicker)
    }
  }, [activeTicker])

  function mapRagToNews(ragResults: RagResult[]): NewsSearchResult[] {
    return ragResults.map((r, i) => ({
      id: `rag-${i}-${Date.now()}`,
      headline: r.title || r.snippet.split('\n')[0].slice(0, 120),
      source: (r.metadata?.source as string) || 'RAG',
      date: r.metadata?.date ? new Date(r.metadata.date as string) : new Date(),
      relevanceScore: r.score,
      ticker: r.metadata?.ticker as string | undefined,
      content: r.snippet,
      url: r.metadata?.url as string | undefined,
    }))
  }

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
          collection: 'commentary_chunks',
          top_k: 20,
          session_id: sessionId,
        }),
      })

      if (!res.ok) {
        const body = await res.text()
        throw new Error(`${res.status} ${res.statusText}: ${body}`)
      }

      const ragResults: RagResult[] = await res.json()

      let mapped = mapRagToNews(ragResults)

      if (ticker) {
        mapped = mapped.filter(r => r.ticker?.toLowerCase() === ticker.toLowerCase())
      }

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
                  <NewsResult key={result.id} result={result} />
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
                <p className="text-sm mt-1">Supports semantic search with relevance scoring</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ScrollArea>
  )
}
