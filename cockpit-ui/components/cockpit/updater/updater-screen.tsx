'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Download, FileText, CheckCircle2, AlertCircle } from 'lucide-react'
import { FinancialData } from '@/lib/cockpit-types'
import { executeAction, fetchFinancials } from '@/lib/api-client'
import { Field, FieldLabel } from '@/components/ui/field'
import { useCockpitStore } from '@/lib/cockpit-store'
import { useEffect } from 'react'

export function UpdaterScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker } = useCockpitStore()
  const [ticker, setTicker] = useState(activeTicker || '')
  const [yearRange, setYearRange] = useState('5')
  const [processDocuments, setProcessDocuments] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<FinancialData[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Wait for hydration to finish to avoid SSR/CSR mismatch with Zustand
  useEffect(() => {
    setHasHydrated(true)
  }, [])

  // Update ticker when activeTicker changes
  useEffect(() => {
    if (activeTicker) {
      setTicker(activeTicker)
    }
  }, [activeTicker])

  if (!hasHydrated) return null

  const handleFetch = async () => {
    if (!ticker.trim()) return

    setIsLoading(true)
    setProgress(0)
    setResults(null)
    setError(null)

    // Indeterminate-style progress: advance to ~90% while waiting
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return 90
        return prev + Math.random() * 15
      })
    }, 500)

    try {
      const normalizedTicker = ticker.trim().toUpperCase()

      // 1. Trigger backfill via the cockpit action registry
      //    Uses POST /api/cockpit/action/execute with action_id
      //    "single_ticker_announcement_backfill", which runs the full
      //    headed-browser ticker sync script with correct args.
      await executeAction({
        actionId: 'single_ticker_announcement_backfill',
        args: {
          ticker: normalizedTicker,
          years: parseInt(yearRange, 10),
          process_documents: processDocuments,
        },
      })

      setProgress(70)

      // 2. Fetch financial results via GET /api/financials?ticker=...
      const financialsData = await fetchFinancials(normalizedTicker)
      setProgress(100)

      // Map API response to FinancialData shape
      // GET /api/financials returns a flat JSON array of financial rows
      const mapped: FinancialData[] = (financialsData as Record<string, unknown>[]).map((item) => ({
        ticker: (item.ticker as string) || normalizedTicker,
        date: new Date((item.date as string) || (item.period_end as string) || ''),
        revenue: item.revenue as number | undefined,
        netIncome: (item.net_income ?? item.netIncome) as number | undefined,
        eps: item.eps as number | undefined,
        marketCap: (item.market_cap ?? item.marketCap) as number | undefined,
        peRatio: (item.pe_ratio ?? item.peRatio) as number | undefined,
        auditConfidence: (item.audit_confidence ?? item.auditConfidence) as number | undefined,
      }))

      setResults(mapped.length > 0 ? mapped : null)

      if (mapped.length === 0) {
        setError('Backfill completed but no financial records found for this ticker.')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(message)
    } finally {
      clearInterval(progressInterval)
      setIsLoading(false)
    }
  }

  const formatCurrency = (value: number | undefined) => {
    if (!value) return '-'
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
    return `$${value.toLocaleString()}`
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-5xl mx-auto">
        {/* Fetch Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Download className="h-5 w-5 text-primary" />
              Fetch Financial Data
            </CardTitle>
            <CardDescription>
              Retrieve and refresh financial data for a ticker
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <Field className="w-[200px]">
                <FieldLabel>Ticker Symbol</FieldLabel>
                <Input
                  placeholder="e.g., BHP"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="font-mono"
                />
              </Field>

              <Field className="w-[150px]">
                <FieldLabel>Year Range</FieldLabel>
                <Select value={yearRange} onValueChange={setYearRange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 Year</SelectItem>
                    <SelectItem value="3">3 Years</SelectItem>
                    <SelectItem value="5">5 Years</SelectItem>
                    <SelectItem value="10">10 Years</SelectItem>
                  </SelectContent>
                </Select>
              </Field>

              <Field className="flex items-end">
                <div className="flex items-center gap-2 h-9">
                  <Checkbox
                    id="processDocuments"
                    checked={processDocuments}
                    onCheckedChange={(checked) => setProcessDocuments(checked as boolean)}
                  />
                  <label
                    htmlFor="processDocuments"
                    className="text-sm cursor-pointer flex items-center gap-2"
                  >
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    Process Documents
                  </label>
                </div>
              </Field>
            </div>

            <div className="flex gap-3">
              <Button onClick={handleFetch} disabled={!ticker.trim() || isLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                {isLoading ? 'Fetching...' : 'Fetch & Process'}
              </Button>
            </div>

            {/* Progress */}
            {isLoading && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Fetching data...</span>
                  <span className="font-mono">{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} />
              </div>
            )}

            {/* Error */}
            {error && !isLoading && (
              <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-md p-3">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {results && results.length > 0 && (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-[oklch(0.65_0.2_145)]" />
                  Latest Financial Data
                </CardTitle>
                <CardDescription>
                  Most recent financial metrics for {results[0].ticker}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Metric</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell>Date</TableCell>
                      <TableCell className="text-right font-mono">
                        {results[0].date.toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Revenue</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(results[0].revenue)}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Net Income</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(results[0].netIncome)}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>EPS</TableCell>
                      <TableCell className="text-right font-mono">
                        ${results[0].eps?.toFixed(2) || '-'}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Market Cap</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(results[0].marketCap)}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>P/E Ratio</TableCell>
                      <TableCell className="text-right font-mono">
                        {results[0].peRatio?.toFixed(1) || '-'}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Audit Section */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-primary" />
                  Audit Confidence
                </CardTitle>
                <CardDescription>
                  Data quality and extraction confidence scores
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Overall Confidence</span>
                    <div className="flex items-center gap-3">
                      <Progress
                        value={(results[0].auditConfidence || 0) * 100}
                        className="w-[200px]"
                      />
                      <Badge variant={results[0].auditConfidence && results[0].auditConfidence > 0.9 ? 'default' : 'secondary'}>
                        {((results[0].auditConfidence || 0) * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-mono font-semibold text-[oklch(0.65_0.2_145)]">23</p>
                      <p className="text-xs text-muted-foreground">Documents</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-mono font-semibold text-[oklch(0.65_0.2_145)]">156</p>
                      <p className="text-xs text-muted-foreground">Metrics</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-mono font-semibold text-primary">5</p>
                      <p className="text-xs text-muted-foreground">Years</p>
                    </div>
                    <div className="text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-mono font-semibold text-[oklch(0.75_0.15_80)]">3</p>
                      <p className="text-xs text-muted-foreground">Warnings</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </ScrollArea>
  )
}
