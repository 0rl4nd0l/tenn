'use client'

import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Clock,
  Database,
  ExternalLink,
  FileSearch,
  Save,
  ShieldCheck,
  Upload,
  X,
  XCircle,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  createUserThesisProposal,
  getThesisAuditCoverage,
  listThesisWatchdogAlerts,
  runThesisAudit,
  updateThesisWatchdogAlertStatus,
  type ClaimVerification,
  type EvidenceSpan,
  type ThesisAuditCoverageReport,
  type ThesisAuditReport,
  type ThesisClaim,
  type ThesisClaimStatus,
  type ThesisMemoryProposalCandidate,
  type ThesisWatchdogAlert,
} from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import { cn } from '@/lib/utils'

const HISTORY_KEY = 'thesis_audit_history'
const MAX_HISTORY = 5

type AuditHistoryEntry = {
  audit_id: string
  ticker: string
  filename: string | null
  focus: string | null
  generated_at: string
  thesis_summary: string
  report: ThesisAuditReport
}

interface ThesisAuditScreenProps {
  apiKey: string
}

type UploadedReport = {
  filename: string
  mimeType: string
  base64: string
}

const STATUS_STYLES: Record<ThesisClaimStatus, string> = {
  supported: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  partially_supported: 'border-sky-500/40 bg-sky-500/10 text-sky-200',
  contradicted: 'border-red-500/40 bg-red-500/10 text-red-200',
  stale: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
  assumption: 'border-violet-500/40 bg-violet-500/10 text-violet-200',
  DATA_MISSING: 'border-zinc-500/40 bg-zinc-500/10 text-zinc-200',
}

function asString(value: unknown, fallback: string = ''): string {
  if (typeof value === 'string') return value
  if (value == null) return fallback
  return String(value)
}

function summarizeError(raw: unknown): string {
  if (raw instanceof Error) return raw.message
  if (raw && typeof raw === 'object' && 'body' in raw) {
    const body = (raw as { body?: unknown }).body
    if (typeof body === 'string') return body
    if (body && typeof body === 'object' && 'detail' in body) {
      return asString((body as { detail?: unknown }).detail, 'Request failed')
    }
  }
  return 'Request failed'
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result || '')
      resolve(result.includes(',') ? result.split(',').pop() || '' : result)
    }
    reader.onerror = () => reject(reader.error || new Error('File read failed'))
    reader.readAsDataURL(file)
  })
}

function statusLabel(status: ThesisClaimStatus): string {
  if (status === 'DATA_MISSING') return 'DATA MISSING'
  return status.replace(/_/g, ' ')
}

function coverageStatusLabel(value: string | null | undefined): string {
  const normalized = asString(value || 'unknown', 'unknown')
  return normalized.replace(/_/g, ' ')
}

function StatusIcon({ status }: { status: ThesisClaimStatus }) {
  if (status === 'supported') return <CheckCircle2 className="h-4 w-4" />
  if (status === 'contradicted') return <XCircle className="h-4 w-4" />
  if (status === 'DATA_MISSING') return <CircleHelp className="h-4 w-4" />
  return <AlertTriangle className="h-4 w-4" />
}

function EvidenceList({ spans }: { spans: EvidenceSpan[] }) {
  if (!spans.length) return <p className="text-xs text-muted-foreground">No independent evidence span.</p>
  return (
    <div className="space-y-2">
      {spans.map((span) => (
        <div key={span.evidence_id} className="rounded-md border border-border/70 bg-muted/20 p-3">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-[10px] uppercase tracking-normal">
              {span.source_layer}
            </Badge>
            <span className="truncate text-xs text-muted-foreground">
              {span.title || span.source_type || span.document_id || span.evidence_id}
            </span>
          </div>
          <p className="line-clamp-4 text-xs leading-relaxed text-foreground/90">{span.text}</p>
          {span.url ? (
            <a
              href={span.url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              Open source
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </div>
      ))}
    </div>
  )
}

function EmptyState({ children }: { children: string }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-muted/10 p-4 text-sm text-muted-foreground">
      {children}
    </div>
  )
}

function ClaimRow({
  claim,
  verification,
}: {
  claim: ThesisClaim
  verification: ClaimVerification | undefined
}) {
  const status = verification?.status ?? 'DATA_MISSING'
  return (
    <div className="rounded-md border border-border bg-background/60 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono text-[10px]">
          #{claim.load_bearing_rank}
        </Badge>
        <Badge variant="secondary" className="text-[10px]">
          {claim.claim_type.replace(/_/g, ' ')}
        </Badge>
        <Badge className={cn('gap-1 border text-[10px] capitalize', STATUS_STYLES[status])}>
          <StatusIcon status={status} />
          {statusLabel(status)}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {claim.confidence_label} | {(claim.load_bearing_score * 100).toFixed(0)}%
        </span>
      </div>
      <p className="text-sm leading-relaxed" data-testid="thesis-audit-claim-text">
        {claim.text}
      </p>
      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-border/70 bg-muted/10 p-3">
          <div className="mb-1 text-xs font-medium text-muted-foreground">Report Span</div>
          <p className="line-clamp-4 text-xs leading-relaxed">{claim.report_span.text}</p>
        </div>
        <div className="rounded-md border border-border/70 bg-muted/10 p-3">
          <div className="mb-1 text-xs font-medium text-muted-foreground">Verification</div>
          <p className="mb-2 text-xs leading-relaxed">{verification?.rationale || 'Not verified.'}</p>
          <EvidenceList
            spans={[
              ...(verification?.independent_evidence_spans || []),
              ...(verification?.contradicting_evidence_spans || []),
            ]}
          />
        </div>
      </div>
    </div>
  )
}

function ProposalRow({
  proposal,
  index,
  disabled,
  staged,
  onStage,
}: {
  proposal: ThesisMemoryProposalCandidate
  index: number
  disabled: boolean
  staged: boolean
  onStage: () => void
}) {
  return (
    <div className="rounded-md border border-border bg-background/60 p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono text-[10px]">
          proposal {index + 1}
        </Badge>
        <Badge variant="secondary" className="text-[10px]">
          {proposal.proposal_type.replace(/_/g, ' ')}
        </Badge>
        <span className="text-xs text-muted-foreground">
          confidence {(proposal.confidence * 100).toFixed(0)}%
        </span>
        {staged ? (
          <a
            href="/memory?tab=thesis"
            className="ml-auto inline-flex h-8 items-center gap-1 rounded-md border border-border px-3 text-xs text-primary hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            View in Memory
          </a>
        ) : (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="ml-auto h-8 gap-2"
            disabled={disabled}
            onClick={onStage}
          >
            <Save className="h-4 w-4" />
            Stage
          </Button>
        )}
      </div>
      <p className="text-sm leading-relaxed">{proposal.statement}</p>
    </div>
  )
}

function HistoryList({
  entries,
  onRestore,
  onDelete,
}: {
  entries: AuditHistoryEntry[]
  onRestore: (entry: AuditHistoryEntry) => void
  onDelete: (auditId: string) => void
}) {
  if (!entries.length) return null
  return (
    <div className="shrink-0 border-t border-border p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Clock className="h-3 w-3" />
        Past Audits
      </div>
      <div className="space-y-1">
        {entries.map((entry) => (
          <div
            key={entry.audit_id}
            className="group flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/30"
            onClick={() => onRestore(entry)}
          >
            <Badge variant="outline" className="shrink-0 font-mono text-[10px]">
              {entry.ticker}
            </Badge>
            <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
              {entry.filename || entry.focus || entry.audit_id.slice(0, 8)}
            </span>
            <span className="shrink-0 text-[10px] text-muted-foreground/60">
              {new Date(entry.generated_at).toLocaleDateString()}
            </span>
            <button
              type="button"
              className="invisible shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground group-hover:visible"
              onClick={(e) => { e.stopPropagation(); onDelete(entry.audit_id) }}
              aria-label="Remove"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

interface AlertListProps {
  alerts: ThesisWatchdogAlert[]
  onDismiss: (alertId: string) => void
  loading?: boolean
}

function AlertList({ alerts, onDismiss, loading }: AlertListProps) {
  if (loading && alerts.length === 0) {
    return (
      <div className="mt-6 border-t border-border pt-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Watchdog Alerts</h3>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3 animate-spin" />
          Checking for alerts...
        </div>
      </div>
    )
  }

  if (alerts.length === 0) return null

  return (
    <div className="mt-6 border-t border-border pt-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Watchdog Alerts</h3>
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div
            key={alert.alert_id}
            className="group relative rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs transition-colors hover:bg-amber-500/10"
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={cn(
                    'px-1 py-0 text-[10px] uppercase',
                    alert.severity === 'contradict'
                      ? 'border-red-500/50 text-red-500'
                      : alert.severity === 'support'
                      ? 'border-green-500/50 text-green-500'
                      : 'border-amber-500/50 text-amber-500',
                  )}
                >
                  {alert.severity}
                </Badge>
                <span className="text-[10px] text-muted-foreground">{new Date(alert.created_at).toLocaleDateString()}</span>
              </div>
              <button
                onClick={() => onDismiss(alert.alert_id)}
                className="opacity-0 transition-opacity group-hover:opacity-100"
                title="Dismiss alert"
              >
                <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
              </button>
            </div>
            <p className="font-medium leading-tight text-foreground">{alert.finding}</p>
            {alert.metadata.excerpt ? (
              <p className="mt-2 line-clamp-2 italic text-muted-foreground">"{alert.metadata.excerpt}"</p>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ThesisAuditScreen({ apiKey }: ThesisAuditScreenProps) {
  const activeTicker = useCockpitStore((state) => state.activeTicker)
  const [ticker, setTicker] = useState(activeTicker || '')
  const prevActiveTickerRef = useRef(activeTicker || '')
  const tickerRef = useRef(ticker)
  tickerRef.current = ticker
  useEffect(() => {
    if (activeTicker && tickerRef.current === prevActiveTickerRef.current) {
      setTicker(activeTicker)
    }
    prevActiveTickerRef.current = activeTicker || ''
  }, [activeTicker])
  const [focus, setFocus] = useState('')
  const [reportText, setReportText] = useState('')
  const [uploadedReport, setUploadedReport] = useState<UploadedReport | null>(null)
  const [audit, setAudit] = useState<ThesisAuditReport | null>(null)
  const [coverage, setCoverage] = useState<ThesisAuditCoverageReport | null>(null)
  const [coverageLoading, setCoverageLoading] = useState(false)
  const [coverageError, setCoverageError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [stagedProposalIndexes, setStagedProposalIndexes] = useState<Set<number>>(new Set())
  const [history, setHistory] = useState<AuditHistoryEntry[]>([])
  const [alerts, setAlerts] = useState<ThesisWatchdogAlert[]>([])
  const [alertsLoading, setAlertsLoading] = useState(false)

  const refreshAlerts = useCallback(
    async (t: string) => {
      if (!t) {
        setAlerts([])
        return
      }
      setAlertsLoading(true)
      try {
        const res = await listThesisWatchdogAlerts({ ticker: t, status: 'unread' }, apiKey)
        if (res.ok) {
          setAlerts(res.alerts)
        }
      } catch (e) {
        console.error('Failed to fetch thesis alerts', e)
      } finally {
        setAlertsLoading(false)
      }
    },
    [apiKey],
  )

  useEffect(() => {
    const saved = localStorage.getItem(HISTORY_KEY)
    if (saved) {
      try {
        setHistory(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to parse thesis audit history', e)
      }
    }
  }, [])

  const saveHistory = (newHistory: AuditHistoryEntry[]) => {
    setHistory(newHistory)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory))
  }

  const verificationByClaim = useMemo(() => {
    const map = new Map<string, ClaimVerification>()
    for (const row of audit?.verification_matrix || []) {
      map.set(row.claim_id, row)
    }
    return map
  }, [audit])

  const counts = useMemo(() => {
    const matrix = audit?.verification_matrix || []
    return {
      supported: matrix.filter((row) => row.status === 'supported').length,
      contradicted: matrix.filter((row) => row.status === 'contradicted').length,
      missing: matrix.filter((row) => row.status === 'DATA_MISSING').length,
      assumption: matrix.filter((row) => row.status === 'assumption').length,
    }
  }, [audit])

  const evidenceSummary = audit?.evidence_summary
  const evidenceSpanCount = Number(evidenceSummary?.evidence_span_count ?? 0)
  const missingCategories = evidenceSummary?.missing_categories_after_recovery || []
  const proposalGate = evidenceSummary?.proposal_gate
  const isEvidenceLimited = Boolean(
    audit
    && (
      evidenceSummary?.sufficient_for_analysis === false
      || evidenceSpanCount === 0
      || missingCategories.length > 0
    ),
  )
  const proposalStageDisabled = Boolean(loading || isEvidenceLimited || proposalGate?.allowed === false)
  const normalizedTicker = ticker.trim().toUpperCase()

  useEffect(() => {
    if (normalizedTicker && /^[A-Z0-9]{3,10}$/.test(normalizedTicker)) {
      refreshAlerts(normalizedTicker)
    }
  }, [normalizedTicker, refreshAlerts])

  const coverageSummary = coverage?.evidence_summary
  const coverageStatus = coverageSummary?.coverage_status
  const coverageIsLimited = Boolean(
    coverage
    && (
      coverageSummary?.sufficient_for_analysis === false
      || Number(coverageSummary?.evidence_span_count ?? 0) === 0
      || (coverageSummary?.missing_categories_after_recovery || []).length > 0
    ),
  )

  useEffect(() => {
    if (!/^[A-Z0-9]{3,10}$/.test(normalizedTicker)) {
      setCoverage(null)
      setCoverageError(null)
      setCoverageLoading(false)
      return
    }

    let cancelled = false
    setCoverageLoading(true)
    setCoverageError(null)
    const timeoutId = window.setTimeout(() => {
      void getThesisAuditCoverage(normalizedTicker, apiKey)
        .then((result) => {
          if (!cancelled) setCoverage(result)
        })
        .catch((error) => {
          if (!cancelled) {
            setCoverage(null)
            setCoverageError(summarizeError(error))
          }
        })
        .finally(() => {
          if (!cancelled) setCoverageLoading(false)
        })
    }, 450)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [apiKey, normalizedTicker])

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const base64 = await readFileAsBase64(file)
      setUploadedReport({
        filename: file.name,
        mimeType: file.type || 'application/octet-stream',
        base64,
      })
      const ext = file.name.toLowerCase().split('.').pop() ?? ''
      const isPlainText = file.type.startsWith('text/') || ext === 'txt' || ext === 'md'
      if (isPlainText) {
        const text = await file.text()
        if (text.trim()) setReportText(text)
      }
      setStatus(`Loaded ${file.name}.`)
    } catch (error) {
      setUploadedReport(null)
      setStatus(summarizeError(error))
    }
  }

  const handleAudit = async () => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) {
      setStatus('Ticker is required.')
      return
    }
    if (!reportText.trim() && !uploadedReport?.base64) {
      setStatus('Report text or file is required.')
      return
    }
    setLoading(true)
    setStatus(null)
    setAudit(null)
    setStagedProposalIndexes(new Set())
    try {
      const result = await runThesisAudit(
        {
          ticker: normalizedTicker,
          reportText: reportText.trim() || undefined,
          filename: uploadedReport?.filename,
          mimeType: uploadedReport?.mimeType,
          contentBase64: reportText.trim() ? undefined : uploadedReport?.base64,
          focus: focus.trim() || undefined,
        },
        apiKey,
      )
      setAudit(result)
      setStatus(`Audit ${result.audit_id} completed.`)

      const entry: AuditHistoryEntry = {
        audit_id: result.audit_id,
        ticker: normalizedTicker,
        filename: uploadedReport?.filename || null,
        focus: focus.trim() || null,
        generated_at: result.generated_at,
        thesis_summary: result.thesis_summary,
        report: result,
      }
      const newHistory = [entry, ...history.filter((h) => h.audit_id !== entry.audit_id)].slice(0, MAX_HISTORY)
      saveHistory(newHistory)
      
      // Refresh alerts after audit as it might have triggered new ones (async)
      setTimeout(() => refreshAlerts(normalizedTicker), 3000)
    } catch (error) {
      setStatus(summarizeError(error))
    } finally {
      setLoading(false)
    }
  }

  const handleStageProposal = async (proposal: ThesisMemoryProposalCandidate, index: number) => {
    if (!audit) return
    try {
      await createUserThesisProposal(
        {
          ticker: audit.ticker,
          proposal_type: proposal.proposal_type,
          statement: proposal.statement,
          signal: proposal.signal || null,
          confidence: proposal.confidence,
          metadata: {
            ...proposal.metadata,
            staged_from: 'thesis_audit_ui',
          },
          note: `Staged from thesis audit ${audit.audit_id}`,
        },
        apiKey,
      )
      setStagedProposalIndexes((prev) => new Set(prev).add(index))
      toast.success('Proposal staged — confirm it in Memory → Thesis')
    } catch (error) {
      toast.error(summarizeError(error))
    }
  }

  const handleRestoreHistory = (entry: AuditHistoryEntry) => {
    setTicker(entry.ticker)
    setFocus(entry.focus || '')
    setReportText('')
    setUploadedReport(null)
    setAudit(entry.report)
    setStatus(`Restored audit from ${new Date(entry.generated_at).toLocaleString()}`)
    setStagedProposalIndexes(new Set())
  }

  const handleDeleteHistory = (auditId: string) => {
    const newHistory = history.filter((h) => h.audit_id !== auditId)
    saveHistory(newHistory)
  }

  const handleDismissAlert = async (alertId: string) => {
    try {
      const res = await updateThesisWatchdogAlertStatus(alertId, 'dismissed', apiKey)
      if (res.ok) {
        setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId))
        toast.success('Alert dismissed')
      }
    } catch (e) {
      toast.error('Failed to dismiss alert')
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="shrink-0 border-b border-border bg-muted/20 p-4">
        <div className="grid gap-3 lg:grid-cols-[120px_1fr_1fr_auto]">
          <Input
            value={ticker}
            onChange={(event) => setTicker(event.target.value.toUpperCase())}
            placeholder="Ticker"
            className="h-10 font-mono uppercase"
            maxLength={10}
          />
          <Input
            value={focus}
            onChange={(event) => setFocus(event.target.value)}
            placeholder="Focus"
            className="h-10"
          />
          <label className="flex h-10 cursor-pointer items-center gap-2 rounded-md border border-border bg-background px-3 text-sm text-muted-foreground hover:bg-muted/40">
            <Upload className="h-4 w-4" />
            <span className="truncate">{uploadedReport?.filename || 'Select report'}</span>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              onChange={handleFileChange}
            />
          </label>
          <Button className="h-10 gap-2" disabled={loading} onClick={handleAudit}>
            <FileSearch className="h-4 w-4" />
            {loading ? 'Auditing' : 'Audit'}
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-10 w-10"
            disabled={coverageLoading}
            onClick={() => {
              if (normalizedTicker) {
                setCoverageLoading(true)
                getThesisAuditCoverage(normalizedTicker, apiKey)
                  .then(setCoverage)
                  .catch((e) => setCoverageError(summarizeError(e)))
                  .finally(() => setCoverageLoading(false))
              }
            }}
            title="Refresh Coverage"
          >
            <Clock className={cn('h-4 w-4', coverageLoading && 'animate-spin')} />
          </Button>
        </div>
        {status || coverageLoading || coverage || coverageError || (reportText.trim() && uploadedReport) ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {status ? <span>{status}</span> : null}
            {coverageLoading ? <span>Checking backend evidence coverage.</span> : null}
            {coverage ? (
              <span
                className={cn(
                  'rounded border px-2 py-1',
                  coverageIsLimited
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-100'
                    : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100',
                )}
                data-testid="thesis-audit-coverage-preflight"
              >
                Coverage: {coverageStatusLabel(coverageStatus)}
              </span>
            ) : null}
            {coverageError ? <span>Coverage unavailable: {coverageError}</span> : null}
            {reportText.trim() && uploadedReport ? (
              <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-amber-100">
                Text input takes priority over uploaded file.
              </span>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="grid flex-1 min-h-0 grid-cols-1 lg:grid-cols-[380px_1fr]">
        <aside className="min-h-0 border-r border-border bg-muted/10">
          <div className="flex h-full min-h-0 flex-col">
            <div className="border-b border-border p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                <ShieldCheck className="h-4 w-4 text-primary" />
                Thesis Source
              </div>
              <Textarea
                value={reportText}
                onChange={(event) => setReportText(event.target.value)}
                placeholder="Paste report text"
                className="min-h-52 resize-none font-mono text-xs"
              />
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-4">
              {audit ? (
                <div className="space-y-4">
                  <div>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="font-mono">
                        {audit.ticker}
                      </Badge>
                      <Badge variant="secondary">{asString(audit.report_source.source_role)}</Badge>
                    </div>
                    <p className="text-sm leading-relaxed">{audit.thesis_summary}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-md border border-border p-3">
                      <div className="text-lg font-semibold">{audit.claims.length}</div>
                      <div className="text-xs text-muted-foreground">Claims</div>
                    </div>
                    <div className="rounded-md border border-border p-3">
                      <div className="text-lg font-semibold">{audit.hidden_assumptions.length}</div>
                      <div className="text-xs text-muted-foreground">Assumptions</div>
                    </div>
                    <div className="rounded-md border border-border p-3">
                      <div className="text-lg font-semibold">{counts.contradicted}</div>
                      <div className="text-xs text-muted-foreground">Contradicted</div>
                    </div>
                    <div className="rounded-md border border-border p-3">
                      <div className="text-lg font-semibold">{counts.missing}</div>
                      <div className="text-xs text-muted-foreground">Missing</div>
                    </div>
                  </div>
                  <div className="rounded-md border border-border p-3">
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                      <Database className="h-4 w-4" />
                      Evidence
                    </div>
                    {isEvidenceLimited ? (
                      <div
                        className="mb-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-100"
                        data-testid="thesis-audit-evidence-limited"
                      >
                        <div className="mb-1 flex items-center gap-2 font-medium">
                          <AlertTriangle className="h-4 w-4" />
                          Evidence-limited result
                        </div>
                        <p className="leading-relaxed">
                          Treat this as an incomplete audit until more backend evidence is available.
                        </p>
                        {missingCategories.length ? (
                          <p className="mt-2 leading-relaxed">
                            Missing after recovery: {missingCategories.join(', ')}
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <p>Spans: {asString(evidenceSummary?.evidence_span_count, '0')}</p>
                      {typeof evidenceSummary?.sufficient_for_analysis === 'boolean' ? (
                        <p>Analysis sufficient: {evidenceSummary.sufficient_for_analysis ? 'yes' : 'no'}</p>
                      ) : null}
                      <p>Read only: {evidenceSummary?.memory_read_only ? 'yes' : 'no'}</p>
                      <p>Auto saved: {audit.guardrails.user_thesis_memory_auto_saved ? 'yes' : 'no'}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  {loading ? 'Audit running.' : 'No audit loaded.'}
                </div>
              )}
            </div>
            <AlertList
              alerts={alerts}
              onDismiss={handleDismissAlert}
              loading={alertsLoading}
            />
            <HistoryList
              entries={history}
              onRestore={handleRestoreHistory}
              onDelete={handleDeleteHistory}
            />
          </div>
        </aside>

        <section className="min-h-0 overflow-hidden">
          {audit ? (
            <Tabs defaultValue="claims" className="flex h-full min-h-0 flex-col">
              <div className="shrink-0 border-b border-border px-4 pt-4">
                <TabsList>
                  <TabsTrigger value="claims">Claims</TabsTrigger>
                  <TabsTrigger value="contrarian">Contrarian</TabsTrigger>
                  <TabsTrigger value="proposals">Proposals</TabsTrigger>
                  <TabsTrigger value="diligence">Diligence</TabsTrigger>
                </TabsList>
              </div>
              <TabsContent value="claims" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="space-y-3">
                  {[...audit.claims]
                    .sort((a, b) => a.load_bearing_rank - b.load_bearing_rank)
                    .map((claim) => (
                      <ClaimRow
                        key={claim.claim_id}
                        claim={claim}
                        verification={verificationByClaim.get(claim.claim_id)}
                      />
                    ))}
                </div>
              </TabsContent>
              <TabsContent value="contrarian" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="space-y-3">
                  {audit.strongest_disconfirming_evidence.length > 0 ? (
                    <>
                      <h2 className="text-sm font-medium">Strongest Disconfirming Evidence</h2>
                      {audit.strongest_disconfirming_evidence.map((finding) => (
                        <div key={finding.break_pack} className="rounded-md border border-border bg-background/60 p-4">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <Badge variant="outline">{finding.break_pack.replace(/_/g, ' ')}</Badge>
                            <Badge className={cn('border text-[10px]', STATUS_STYLES[finding.status])}>
                              {statusLabel(finding.status)}
                            </Badge>
                            <span className="text-xs text-muted-foreground">{finding.confidence_label}</span>
                          </div>
                          <p className="mb-3 text-sm leading-relaxed">{finding.finding}</p>
                          <EvidenceList spans={finding.evidence_spans} />
                        </div>
                      ))}
                      <div className="border-t border-border my-4" />
                    </>
                  ) : null}
                  {audit.contrarian_findings.filter(
                    (f) => !audit.strongest_disconfirming_evidence.some((s) => s.break_pack === f.break_pack),
                  ).length ? (
                    audit.contrarian_findings
                      .filter((f) => !audit.strongest_disconfirming_evidence.some((s) => s.break_pack === f.break_pack))
                      .map((finding) => (
                        <div key={finding.break_pack} className="rounded-md border border-border bg-background/60 p-4">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <Badge variant="outline">{finding.break_pack.replace(/_/g, ' ')}</Badge>
                            <Badge className={cn('border text-[10px]', STATUS_STYLES[finding.status])}>
                              {statusLabel(finding.status)}
                            </Badge>
                            <span className="text-xs text-muted-foreground">{finding.confidence_label}</span>
                          </div>
                          <p className="mb-3 text-sm leading-relaxed">{finding.finding}</p>
                          <EvidenceList spans={finding.evidence_spans} />
                        </div>
                      ))
                  ) : audit.strongest_disconfirming_evidence.length === 0 ? (
                    <EmptyState>No contrarian findings were returned for this audit.</EmptyState>
                  ) : null}
                </div>
              </TabsContent>
              <TabsContent value="proposals" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="space-y-3">
                  {audit.user_thesis_memory_proposals.length ? (
                    audit.user_thesis_memory_proposals.map((proposal, index) => (
                      <ProposalRow
                        key={`${proposal.proposal_type}-${index}`}
                        proposal={proposal}
                        index={index}
                        disabled={proposalStageDisabled}
                        staged={stagedProposalIndexes.has(index)}
                        onStage={() => handleStageProposal(proposal, index)}
                      />
                    ))
                  ) : (
                    <EmptyState>No thesis memory proposals were generated.</EmptyState>
                  )}
                  {proposalGate?.allowed === false && proposalGate.message ? (
                    <EmptyState>{proposalGate.message}</EmptyState>
                  ) : null}
                </div>
              </TabsContent>
              <TabsContent value="diligence" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="grid gap-4 xl:grid-cols-2">
                  {audit.report_to_reality_delta ? (
                    <div className="rounded-md border border-border bg-background/60 p-4 xl:col-span-2">
                      <h2 className="mb-3 text-sm font-medium">Report-to-Reality Delta</h2>
                      <p className="text-sm leading-relaxed text-foreground/90">{audit.report_to_reality_delta}</p>
                    </div>
                  ) : null}
                  <div className="rounded-md border border-border bg-background/60 p-4">
                    <h2 className="mb-3 text-sm font-medium">Change My Mind</h2>
                    {audit.change_my_mind_triggers.length ? (
                      <ul className="space-y-2">
                        {audit.change_my_mind_triggers.map((item) => (
                          <li key={item} className="text-sm leading-relaxed text-foreground/90">
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <EmptyState>No change-my-mind triggers were returned.</EmptyState>
                    )}
                  </div>
                  <div className="rounded-md border border-border bg-background/60 p-4">
                    <h2 className="mb-3 text-sm font-medium">Next Questions</h2>
                    {audit.next_diligence_questions.length ? (
                      <ul className="space-y-2">
                        {audit.next_diligence_questions.map((item) => (
                          <li key={item} className="text-sm leading-relaxed text-foreground/90">
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <EmptyState>No next diligence questions were returned.</EmptyState>
                    )}
                  </div>
                  <div className="rounded-md border border-border bg-background/60 p-4 xl:col-span-2">
                    <h2 className="mb-3 text-sm font-medium">Hidden Assumptions</h2>
                    {audit.hidden_assumptions.length ? (
                      <div className="grid gap-3 lg:grid-cols-2">
                        {audit.hidden_assumptions.map((assumption) => (
                          <div key={assumption.assumption_id} className="rounded-md border border-border/70 p-3">
                            <div className="mb-1 text-xs text-muted-foreground">
                              {assumption.confidence_label} | {assumption.related_claim_ids.join(', ') || '-'}
                            </div>
                            <p className="text-sm leading-relaxed">{assumption.text}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <EmptyState>No hidden assumptions were extracted.</EmptyState>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              <div className="rounded-md border border-border bg-muted/10 p-6">
                <FileSearch className="mb-3 h-6 w-6 text-primary" />
                <div>{loading ? 'Running thesis audit.' : 'Run an audit to review claims.'}</div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
