'use client'

import { ChangeEvent, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  Database,
  FileSearch,
  Save,
  ShieldCheck,
  Upload,
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
  runThesisAudit,
  type ClaimVerification,
  type EvidenceSpan,
  type ThesisAuditReport,
  type ThesisClaim,
  type ThesisClaimStatus,
  type ThesisMemoryProposalCandidate,
} from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import { cn } from '@/lib/utils'

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
      {spans.slice(0, 3).map((span) => (
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
        </div>
      ))}
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
        <Button
          type="button"
          size="sm"
          variant={staged ? 'secondary' : 'outline'}
          className="ml-auto h-8 gap-2"
          disabled={disabled || staged}
          onClick={onStage}
        >
          <Save className="h-4 w-4" />
          {staged ? 'Staged' : 'Stage'}
        </Button>
      </div>
      <p className="text-sm leading-relaxed">{proposal.statement}</p>
    </div>
  )
}

export function ThesisAuditScreen({ apiKey }: ThesisAuditScreenProps) {
  const activeTicker = useCockpitStore((state) => state.activeTicker)
  const [ticker, setTicker] = useState(activeTicker || '')
  const [focus, setFocus] = useState('')
  const [reportText, setReportText] = useState('')
  const [uploadedReport, setUploadedReport] = useState<UploadedReport | null>(null)
  const [audit, setAudit] = useState<ThesisAuditReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [stagedProposalIndexes, setStagedProposalIndexes] = useState<Set<number>>(new Set())

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
      if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
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
      toast.success('Proposal staged')
    } catch (error) {
      toast.error(summarizeError(error))
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
              accept=".pdf,.txt,.md,text/plain,application/pdf"
              className="sr-only"
              onChange={handleFileChange}
            />
          </label>
          <Button className="h-10 gap-2" disabled={loading} onClick={handleAudit}>
            <FileSearch className="h-4 w-4" />
            {loading ? 'Auditing' : 'Audit'}
          </Button>
        </div>
        {status ? <div className="mt-3 text-xs text-muted-foreground">{status}</div> : null}
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
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <p>Spans: {asString(audit.evidence_summary.evidence_span_count, '0')}</p>
                      <p>Read only: {audit.evidence_summary.memory_read_only ? 'yes' : 'no'}</p>
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
                  {audit.contrarian_findings.map((finding) => (
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
                </div>
              </TabsContent>
              <TabsContent value="proposals" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="space-y-3">
                  {audit.user_thesis_memory_proposals.map((proposal, index) => (
                    <ProposalRow
                      key={`${proposal.proposal_type}-${index}`}
                      proposal={proposal}
                      index={index}
                      disabled={loading}
                      staged={stagedProposalIndexes.has(index)}
                      onStage={() => handleStageProposal(proposal, index)}
                    />
                  ))}
                </div>
              </TabsContent>
              <TabsContent value="diligence" className="min-h-0 flex-1 overflow-auto p-4">
                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-md border border-border bg-background/60 p-4">
                    <h2 className="mb-3 text-sm font-medium">Change My Mind</h2>
                    <ul className="space-y-2">
                      {audit.change_my_mind_triggers.map((item) => (
                        <li key={item} className="text-sm leading-relaxed text-foreground/90">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-md border border-border bg-background/60 p-4">
                    <h2 className="mb-3 text-sm font-medium">Next Questions</h2>
                    <ul className="space-y-2">
                      {audit.next_diligence_questions.map((item) => (
                        <li key={item} className="text-sm leading-relaxed text-foreground/90">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-md border border-border bg-background/60 p-4 xl:col-span-2">
                    <h2 className="mb-3 text-sm font-medium">Hidden Assumptions</h2>
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
