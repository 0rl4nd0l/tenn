'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { CheckCircle2, XCircle, Play, FileJson, FileText, BarChart3, AlertCircle } from 'lucide-react'
import type { VerificationResult } from '@/lib/cockpit-types'
import { Field, FieldLabel } from '@/components/ui/field'
import { useCockpitStore } from '@/lib/cockpit-store'
import { useEffect } from 'react'

export function VerificationScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const { activeTicker } = useCockpitStore()
  const [ticker, setTicker] = useState(activeTicker || '')
  const [isRunning, setIsRunning] = useState(false)
  const [results, setResults] = useState<VerificationResult[] | null>(null)
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

  const handleRunVerification = async (broad: boolean = false) => {
    setIsRunning(true)
    setResults(null)
    setError(null)

    const queryTicker = broad ? '' : ticker.trim()
    const url = queryTicker
      ? `/api/context/verification?ticker=${encodeURIComponent(queryTicker)}`
      : '/api/context/verification'

    try {
      const res = await fetch(url)
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `Verification failed (HTTP ${res.status})`)
      }

      const data: unknown = await res.json()

      // Map response defensively to VerificationResult[]
      const mapped = mapResponseToResults(data)
      setResults(mapped)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unexpected error during verification'
      setError(message)
    } finally {
      setIsRunning(false)
    }
  }

  function mapResponseToResults(data: unknown): VerificationResult[] {
    if (!data || typeof data !== 'object') {
      return [{ metric: 'Raw Response', expected: '-', actual: String(data), passed: false, details: 'Unexpected response format' }]
    }

    // If the response is an array, treat each item as a potential result
    const items = Array.isArray(data)
      ? data
      : 'metrics' in data && Array.isArray((data as Record<string, unknown>).metrics)
        ? (data as Record<string, unknown>).metrics as unknown[]
        : null

    if (items) {
      return items.map((item: unknown, i: number) => {
        if (item && typeof item === 'object') {
          const r = item as Record<string, unknown>
          return {
            metric: String(r.metric ?? r.name ?? r.label ?? `Check ${i + 1}`),
            expected: formatRawValue(r.expected),
            actual: formatRawValue(r.actual ?? r.value),
            passed: typeof r.passed === 'boolean' ? r.passed : (r.status === 'pass' || r.status === 'ok'),
            details: r.details ? String(r.details) : undefined,
          }
        }
        return { metric: `Check ${i + 1}`, expected: '-', actual: String(item), passed: false }
      })
    }

    // Fallback: display raw JSON as a single row
    return [{ metric: 'Raw Response', expected: '-', actual: JSON.stringify(data, null, 2), passed: false, details: 'Unrecognized response shape' }]
  }

  function formatRawValue(v: unknown): string | number {
    if (typeof v === 'number') return v
    if (typeof v === 'string') return v
    if (v == null) return '-'
    return String(v)
  }

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleExportJson = () => {
    if (!results) return
    const payload = {
      ticker: ticker || 'broad',
      exportedAt: new Date().toISOString(),
      summary: {
        passed: results.filter(r => r.passed).length,
        failed: results.filter(r => !r.passed).length,
        total: results.length,
      },
      results,
    }
    const filename = `verification-${ticker || 'broad'}-${new Date().toISOString().slice(0, 10)}.json`
    downloadFile(JSON.stringify(payload, null, 2), filename, 'application/json')
  }

  const handleExportHtml = () => {
    if (!results) return
    const passed = results.filter(r => r.passed).length
    const failed = results.filter(r => !r.passed).length
    const rate = results.length > 0 ? ((passed / results.length) * 100).toFixed(0) : '0'

    const rows = results.map(r => {
      const statusIcon = r.passed ? '&#10003;' : '&#10007;'
      const statusColor = r.passed ? '#22c55e' : '#ef4444'
      return `<tr>
        <td style="color:${statusColor};text-align:center;font-size:18px">${statusIcon}</td>
        <td>${escapeHtml(r.metric)}</td>
        <td style="text-align:right;font-family:monospace">${escapeHtml(String(r.expected))}</td>
        <td style="text-align:right;font-family:monospace">${escapeHtml(String(r.actual))}</td>
        <td style="color:#888">${escapeHtml(r.details || '-')}</td>
      </tr>`
    }).join('\n')

    const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Verification Report – ${escapeHtml(ticker || 'Broad')}</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;color:#e0e0e0;background:#0a0a0a}
  h1{font-size:1.4rem}
  .summary{display:flex;gap:2rem;margin:1rem 0}
  .summary div{text-align:center;padding:1rem;border-radius:8px;background:#1a1a1a;min-width:100px}
  .summary .val{font-size:2rem;font-weight:700;font-family:monospace}
  table{width:100%;border-collapse:collapse;margin-top:1rem}
  th,td{padding:8px 12px;border-bottom:1px solid #222;text-align:left;font-size:0.9rem}
  th{background:#111;color:#aaa;font-weight:600}
</style></head><body>
<h1>Verification Report${ticker ? ' — ' + escapeHtml(ticker) : ''}</h1>
<p style="color:#888">Generated ${new Date().toLocaleString()}</p>
<div class="summary">
  <div><div class="val" style="color:#22c55e">${passed}</div><div>Passed</div></div>
  <div><div class="val" style="color:#ef4444">${failed}</div><div>Failed</div></div>
  <div><div class="val" style="color:#3b82f6">${rate}%</div><div>Pass Rate</div></div>
</div>
<table><thead><tr><th>Status</th><th>Metric</th><th style="text-align:right">Expected</th><th style="text-align:right">Actual</th><th>Details</th></tr></thead>
<tbody>${rows}</tbody></table>
</body></html>`

    const filename = `verification-${ticker || 'broad'}-${new Date().toISOString().slice(0, 10)}.html`
    downloadFile(html, filename, 'text/html')
  }

  function escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  const passedCount = results?.filter(r => r.passed).length || 0
  const totalCount = results?.length || 0
  const passRate = totalCount > 0 ? (passedCount / totalCount) * 100 : 0

  const formatValue = (value: string | number) => {
    if (typeof value === 'number') {
      if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
      if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
      return value.toLocaleString()
    }
    return value
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-5xl mx-auto">
        {/* Verification Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-primary" />
              Data Verification
            </CardTitle>
            <CardDescription>
              Run integrity checks on financial data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-4 items-end">
              <Field className="w-[200px]">
                <FieldLabel>Ticker (optional)</FieldLabel>
                <Input
                  placeholder="Leave empty for broad check"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="font-mono"
                />
              </Field>

              <div className="flex gap-2">
                <Button onClick={() => handleRunVerification(true)} disabled={isRunning}>
                  <Play className="h-4 w-4 mr-2" />
                  Run Broad Verification
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => handleRunVerification(false)} 
                  disabled={isRunning || !ticker.trim()}
                >
                  <Play className="h-4 w-4 mr-2" />
                  Verify Ticker
                </Button>
              </div>
            </div>

            {isRunning && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                Running verification checks...
              </div>
            )}

            {error && (
              <div className="flex items-center gap-3 text-sm text-destructive bg-destructive/10 rounded-lg p-3">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {results && (
          <>
            {/* Summary */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">Verification Results</CardTitle>
                    <CardDescription>
                      {passedCount} of {totalCount} checks passed
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleExportJson}>
                      <FileJson className="h-4 w-4 mr-2" />
                      Export JSON
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleExportHtml}>
                      <FileText className="h-4 w-4 mr-2" />
                      Export HTML
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* Summary Stats */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <p className="text-3xl font-mono font-semibold text-[oklch(0.65_0.2_145)]">
                      {passedCount}
                    </p>
                    <p className="text-xs text-muted-foreground">Passed</p>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <p className="text-3xl font-mono font-semibold text-[oklch(0.55_0.2_25)]">
                      {totalCount - passedCount}
                    </p>
                    <p className="text-xs text-muted-foreground">Failed</p>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <p className="text-3xl font-mono font-semibold text-primary">
                      {passRate.toFixed(0)}%
                    </p>
                    <p className="text-xs text-muted-foreground">Pass Rate</p>
                  </div>
                </div>

                {/* Results Table */}
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[40px]">Status</TableHead>
                      <TableHead>Metric</TableHead>
                      <TableHead className="text-right">Expected</TableHead>
                      <TableHead className="text-right">Actual</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((result, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          {result.passed ? (
                            <CheckCircle2 className="h-4 w-4 text-[oklch(0.65_0.2_145)]" />
                          ) : (
                            <XCircle className="h-4 w-4 text-[oklch(0.55_0.2_25)]" />
                          )}
                        </TableCell>
                        <TableCell className="font-medium">{result.metric}</TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {formatValue(result.expected)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {formatValue(result.actual)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {result.details || '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Chart Placeholder */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  Visualization
                </CardTitle>
                <CardDescription>
                  Interactive charts for verified data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64 flex items-center justify-center rounded-lg border border-dashed border-border bg-muted/20">
                  <div className="text-center text-muted-foreground">
                    <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">Plotly chart would render here</p>
                    <p className="text-xs mt-1">Candlestick, snapshot, or comparison charts</p>
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
