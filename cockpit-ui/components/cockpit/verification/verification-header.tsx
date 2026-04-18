'use client'

import { Activity } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import type { ExtractionMethod, ExtractionReviewSession } from '@/lib/cockpit-types'

import { EXTRACTION_METHOD_OPTIONS } from './constants'

type VerificationHeaderProps = {
  ticker: string
  extractionMethod: ExtractionMethod
  strictMethod: boolean
  reviewSession: ExtractionReviewSession | null
  failedChecksCount: number
  onTickerChange: (value: string) => void
  onMethodChange: (value: ExtractionMethod) => void
  onStrictMethodChange: (value: boolean) => void
}

export function VerificationHeader({
  ticker,
  extractionMethod,
  strictMethod,
  reviewSession,
  failedChecksCount,
  onTickerChange,
  onMethodChange,
  onStrictMethodChange,
}: VerificationHeaderProps) {
  const summary = reviewSession?.summary

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5 text-primary" />
              Verification Workstation
            </CardTitle>
            <CardDescription>
              Shared extraction configuration stays visible while you move between review, runs, gold eval, and verification workflows.
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            {failedChecksCount > 0 && (
              <Badge variant="critical" className="h-6 animate-pulse px-2 shadow-sm">
                {failedChecksCount} Logical Failure{failedChecksCount === 1 ? '' : 's'}
              </Badge>
            )}
            {summary ? (
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="h-6">pending {summary.pending ?? 0}</Badge>
                <Badge variant="default" className="h-6">correct {summary.approved ?? 0}</Badge>
                <Badge variant="critical" className="h-6">wrong {summary.wrong ?? 0}</Badge>
                <Badge variant="secondary" className="h-6">unsure {summary.abstain ?? 0}</Badge>
              </div>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-end gap-6">
          <Field className="w-[200px]">
            <FieldLabel>Active Ticker</FieldLabel>
            <Input
              placeholder="e.g. BHP"
              value={ticker}
              onChange={(event) => onTickerChange(event.target.value.toUpperCase())}
              className="font-mono"
            />
          </Field>

          <Field className="w-[200px]">
            <FieldLabel>Method / Provider</FieldLabel>
            <Select value={extractionMethod} onValueChange={(value) => onMethodChange(value as ExtractionMethod)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EXTRACTION_METHOD_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field className="w-[160px]">
            <FieldLabel>Strict Mode</FieldLabel>
            <div className="flex h-10 items-center gap-3 rounded-md border border-input bg-background px-3">
              <Switch checked={strictMethod} onCheckedChange={onStrictMethodChange} />
              <span className="text-sm whitespace-nowrap text-muted-foreground">No fallback</span>
            </div>
          </Field>

          <div className="flex-1" />

          <div className="flex flex-wrap gap-2 pt-2 md:pt-0">
            <Badge variant="outline" className="h-7 border-primary/30 font-mono">
              {ticker ? `Target: ${ticker}` : 'Broad Mode'}
            </Badge>
            <Badge variant="outline" className="h-7 border-primary/30">
              {extractionMethod}
            </Badge>
            <Badge
              variant="outline"
              className={cn('h-7', strictMethod ? 'border-orange-500/50 text-orange-500' : 'border-primary/30')}
            >
              {strictMethod ? 'Strict' : 'Auto-fallback'}
            </Badge>
            {reviewSession ? (
              <Badge variant="outline" className="h-7 border-primary/30 font-mono">
                Session {reviewSession.session_id.slice(0, 12)}
              </Badge>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
