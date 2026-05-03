'use client'

import { AlertTriangle, CheckCircle2, CircleDot, Trash2, XCircle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

import type { VerificationProgressEntry, VerificationProgressLevel } from './types'

type VerificationProgressLogProps = {
  entries: VerificationProgressEntry[]
  onClear: () => void
  className?: string
  compact?: boolean
}

function levelIcon(level: VerificationProgressLevel) {
  if (level === 'success') return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
  if (level === 'warning') return <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
  if (level === 'error') return <XCircle className="h-3.5 w-3.5 text-destructive" />
  return <CircleDot className="h-3.5 w-3.5 text-primary" />
}

function levelVariant(level: VerificationProgressLevel): 'default' | 'secondary' | 'critical' | 'outline' {
  if (level === 'success') return 'default'
  if (level === 'warning') return 'secondary'
  if (level === 'error') return 'critical'
  return 'outline'
}

function formatLogTime(value: string): string {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function VerificationProgressLog({
  entries,
  onClear,
  className,
  compact = false,
}: VerificationProgressLogProps) {
  return (
    <Card className={cn('border-border/40 bg-muted/10', className)}>
      <CardHeader className="flex flex-row items-center justify-between gap-3 p-4 pb-2">
        <CardTitle className="text-sm font-bold uppercase text-muted-foreground">
          Progress Log
        </CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-5 px-1.5 text-[10px]">
            {entries.length}
          </Badge>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onClear}
            disabled={entries.length === 0}
            title="Clear progress log"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span className="sr-only">Clear progress log</span>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className={compact ? 'h-48' : 'h-72'}>
          <div className="space-y-2 p-4 pt-2">
            {entries.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/60 p-3 text-xs text-muted-foreground">
                No workflow events yet.
              </div>
            ) : entries.map((entry) => (
              <div key={entry.id} className="rounded-md border border-border/40 bg-background/60 p-2.5">
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 shrink-0">{levelIcon(entry.level)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant={levelVariant(entry.level)} className="h-4 rounded-sm px-1 text-[9px] uppercase">
                        {entry.scope}
                      </Badge>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {formatLogTime(entry.timestamp)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-snug text-foreground">{entry.message}</p>
                    {entry.detail ? (
                      <p className="mt-1 break-words font-mono text-[10px] leading-snug text-muted-foreground">
                        {entry.detail}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
