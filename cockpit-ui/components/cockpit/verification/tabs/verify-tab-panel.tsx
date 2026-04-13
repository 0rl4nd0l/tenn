import { AlertCircle, CheckCircle2, FileJson, FileText, Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { VerificationResult } from '@/lib/cockpit-types'

import { formatValue } from '../utils'

type VerifyTabPanelProps = {
  ticker: string
  isRunning: boolean
  error: string | null
  results: VerificationResult[] | null
  onRunVerification: (broad?: boolean) => void
  onExportJson: () => void
  onExportHtml: () => void
}

export function VerifyTabPanel({
  ticker,
  isRunning,
  error,
  results,
  onRunVerification,
  onExportJson,
  onExportHtml,
}: VerifyTabPanelProps) {
  const passedCount = results?.filter((result) => result.passed).length || 0
  const totalCount = results?.length || 0
  const passRate = totalCount > 0 ? (passedCount / totalCount) * 100 : 0

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            Data Verification
          </CardTitle>
          <CardDescription>
            Read extraction failures and low-confidence financial rows from the backend state.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex gap-2">
              <Button onClick={() => onRunVerification(true)} disabled={isRunning}>
                <Play className="mr-2 h-4 w-4" />
                Run Broad Verification
              </Button>
              <Button variant="outline" onClick={() => onRunVerification(false)} disabled={isRunning || !ticker.trim()}>
                <Play className="mr-2 h-4 w-4" />
                Verify Ticker
              </Button>
            </div>
          </div>

          {isRunning ? (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Running verification checks...
            </div>
          ) : null}

          {error ? (
            <div className="flex items-center gap-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {results ? (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle className="text-lg">Verification Results</CardTitle>
                <CardDescription>
                  {passedCount} of {totalCount} checks passed
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={onExportJson}>
                  <FileJson className="mr-2 h-4 w-4" />
                  Export JSON
                </Button>
                <Button variant="outline" size="sm" onClick={onExportHtml}>
                  <FileText className="mr-2 h-4 w-4" />
                  Export HTML
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-6 grid grid-cols-3 gap-4">
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="font-mono text-3xl font-semibold text-[oklch(0.65_0.2_145)]">{passedCount}</p>
                <p className="text-xs text-muted-foreground">Passed</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="font-mono text-3xl font-semibold text-[oklch(0.55_0.2_25)]">{totalCount - passedCount}</p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </div>
              <div className="rounded-lg bg-muted/50 p-4 text-center">
                <p className="text-3xl font-semibold text-primary">{passRate.toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground">Pass Rate</p>
              </div>
            </div>

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
                {results.map((result, index) => (
                  <TableRow key={`${result.metric}-${index}`}>
                    <TableCell>
                      {result.passed ? (
                        <CheckCircle2 className="h-4 w-4 text-[oklch(0.65_0.2_145)]" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-[oklch(0.55_0.2_25)]" />
                      )}
                    </TableCell>
                    <TableCell className="font-medium">{result.metric}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{formatValue(result.expected)}</TableCell>
                    <TableCell className="text-right font-mono text-sm">{formatValue(result.actual)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{result.details || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
