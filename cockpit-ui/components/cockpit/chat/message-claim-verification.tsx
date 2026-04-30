'use client'

import { useState, type ReactNode } from 'react'

import {
  submitResponseFeedback,
  verifyClaims,
  type SubmitResponseFeedbackRequest,
  type VerifyClaimsRequest,
} from '@/lib/api-client'
import type {
  ChatMessage,
  ClaimVerificationResponse,
  ClaimVerificationVerdictStatus,
  ResponseFeedbackReasonCode,
  ResponseFeedbackResponse,
} from '@/lib/cockpit-types'

type VerifyClaimsRunner = (
  params: VerifyClaimsRequest,
  apiKey?: string,
) => Promise<ClaimVerificationResponse>

type SubmitFeedbackRunner = (
  params: SubmitResponseFeedbackRequest,
  apiKey?: string,
) => Promise<ResponseFeedbackResponse>

type MessageClaimVerificationProps = {
  message: ChatMessage
  sessionId: string
  parentMessageId?: string | null
  parentPrompt?: string | null
  ticker?: string | null
  apiKey?: string
  children?: ReactNode
  verifyClaimsRunner?: VerifyClaimsRunner
  submitFeedbackRunner?: SubmitFeedbackRunner
}

const VERDICT_LABELS: Record<ClaimVerificationVerdictStatus, string> = {
  supported: 'supported',
  contradicted: 'contradicted',
  insufficient_evidence: 'insufficient evidence',
  not_checkable: 'not checkable',
}

const ISSUE_REASONS: Array<{ code: ResponseFeedbackReasonCode; label: string }> = [
  { code: 'wrong_fact', label: 'Wrong fact' },
  { code: 'wrong_number', label: 'Wrong number' },
  { code: 'unsupported_claim', label: 'Unsupported claim' },
  { code: 'weak_evidence', label: 'Weak evidence' },
  { code: 'bad_reasoning', label: 'Bad reasoning' },
  { code: 'incomplete', label: 'Incomplete' },
  { code: 'irrelevant', label: 'Irrelevant' },
  { code: 'unclear', label: 'Unclear' },
  { code: 'poor_structure', label: 'Poor structure' },
  { code: 'other', label: 'Other' },
]

function verdictClass(verdict: ClaimVerificationVerdictStatus): string {
  if (verdict === 'supported') {
    return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
  }
  if (verdict === 'contradicted') {
    return 'border-red-500/40 bg-red-500/10 text-red-200'
  }
  if (verdict === 'not_checkable') {
    return 'border-zinc-500/40 bg-zinc-500/10 text-zinc-200'
  }
  return 'border-amber-500/40 bg-amber-500/10 text-amber-200'
}

export function ClaimVerificationPanel({
  result,
  error,
}: {
  result: ClaimVerificationResponse | null
  error: string | null
}) {
  if (!result && !error) {
    return null
  }

  if (error) {
    return (
      <div className="rounded border border-red-500/30 bg-red-500/8 px-3 py-2 text-xs text-red-200">
        {error}
      </div>
    )
  }

  if (!result) {
    return null
  }

  return (
    <div className="space-y-2 rounded border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-xs text-blue-100/90">
      <div className="space-y-1 border-b border-blue-500/10 pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-blue-200/80">
          <span>Evidence check</span>
          <span>
            {result.verdicts.length} claim{result.verdicts.length === 1 ? '' : 's'} · {result.evidence_count} evidence
          </span>
        </div>
        <div className="text-blue-100/60">
          Checks whether this answer is supported by the evidence attached to it. It does not audit the underlying data pipeline.
        </div>
      </div>
      {result.verdicts.length === 0 ? (
        <div className="text-blue-100/70">No checkable claims found.</div>
      ) : (
        <div className="space-y-2">
          {result.verdicts.map((item) => {
            const refs = [
              ...item.supporting_source_ids,
              ...item.contradicting_source_ids,
            ]
            return (
              <div key={item.claim_id} className="space-y-1 border-t border-blue-500/10 pt-2">
                <div className="flex flex-wrap items-start gap-2">
                  <span className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] ${verdictClass(item.verdict)}`}>
                    {VERDICT_LABELS[item.verdict]}
                  </span>
                  <span className="min-w-0 flex-1 break-words text-blue-50">
                    {item.claim_text}
                  </span>
                </div>
                <div className="text-blue-100/65">{item.short_reason}</div>
                {refs.length > 0 ? (
                  <div className="break-words font-mono text-[10px] text-blue-200/55">
                    sources: {refs.join(', ')}
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function MessageClaimVerification({
  message,
  sessionId,
  parentMessageId = null,
  parentPrompt = null,
  ticker = null,
  apiKey,
  children,
  verifyClaimsRunner = verifyClaims,
  submitFeedbackRunner = submitResponseFeedback,
}: MessageClaimVerificationProps) {
  const [result, setResult] = useState<ClaimVerificationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [issueOpen, setIssueOpen] = useState(false)
  const [issueReason, setIssueReason] = useState<ResponseFeedbackReasonCode | null>(null)
  const [issueNote, setIssueNote] = useState('')
  const [issueState, setIssueState] = useState<'idle' | 'submitting' | 'submitted'>('idle')
  const [issueError, setIssueError] = useState<string | null>(null)
  const assistantText = message.content.trim()
  const canVerify = message.role === 'assistant' && assistantText.length > 0

  const handleVerify = async () => {
    if (!canVerify || isLoading) {
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const response = await verifyClaimsRunner(
        {
          sessionId,
          messageId: message.id,
          parentPrompt,
          assistantText,
          ticker,
          routeType: message.metadata?.source ?? null,
          visibleSources: message.sources ?? [],
        },
        apiKey,
      )
      setResult(response)
      setIssueOpen(false)
      setIssueReason(null)
      setIssueNote('')
      setIssueState('idle')
      setIssueError(null)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Evidence check failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmitIssue = async () => {
    if (!result || !issueReason || issueState === 'submitting') {
      return
    }

    setIssueState('submitting')
    setIssueError(null)
    try {
      await submitFeedbackRunner(
        {
          sessionId,
          messageId: message.id,
          parentMessageId,
          userLabel: 'evidence_check_issue',
          reasonCode: issueReason,
          note: issueNote.trim() || null,
          queryText: parentPrompt,
          finalAnswerText: assistantText,
          ticker,
          routeType: message.metadata?.source ?? null,
          modelLabel: message.metadata?.model ?? null,
          visibleSources: message.sources ?? [],
          responseLatencyMs: message.metadata?.latencyMs ?? null,
          verifierResult: result,
        },
        apiKey,
      )
      setIssueState('submitted')
      setIssueOpen(false)
    } catch (err) {
      setIssueState('idle')
      setIssueError(err instanceof Error ? err.message : 'Issue report failed')
    }
  }

  return (
    <div className="ml-6 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {children}
        {canVerify ? (
          <button
            type="button"
            onClick={() => { void handleVerify() }}
            disabled={isLoading}
            className="rounded border border-blue-500/30 bg-blue-500/8 px-2 py-0.5 font-mono text-[11px] text-blue-300 transition-colors hover:bg-blue-500/15 disabled:cursor-default disabled:opacity-70"
          >
            {isLoading ? 'Checking evidence...' : 'Verify against evidence'}
          </button>
        ) : null}
      </div>
      <ClaimVerificationPanel result={result} error={error} />
      {result ? (
        <div className="space-y-2 rounded border border-zinc-700/60 bg-zinc-950/40 px-3 py-2 text-xs text-zinc-200">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setIssueOpen((value) => !value)
                setIssueError(null)
              }}
              disabled={issueState === 'submitting'}
              className="rounded border border-zinc-600 bg-zinc-900 px-2 py-0.5 font-mono text-[11px] text-zinc-200 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60"
            >
              Report issue
            </button>
            {issueState === 'submitted' ? (
              <span className="font-mono text-[11px] text-emerald-300">Issue reported</span>
            ) : null}
            {issueError ? (
              <span className="font-mono text-[11px] text-red-300">{issueError}</span>
            ) : null}
          </div>
          {issueOpen ? (
            <div className="space-y-2 border-t border-zinc-800 pt-2">
              <div className="flex flex-wrap gap-2">
                {ISSUE_REASONS.map((reason) => {
                  const selected = issueReason === reason.code
                  return (
                    <button
                      key={reason.code}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setIssueReason(reason.code)}
                      disabled={issueState === 'submitting'}
                      className={selected
                        ? 'rounded border border-blue-400/60 bg-blue-500/20 px-2 py-1 font-mono text-[11px] text-blue-100 transition-colors disabled:cursor-default disabled:opacity-60'
                        : 'rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px] text-zinc-300 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60'}
                    >
                      {reason.label}
                    </button>
                  )
                })}
              </div>
              <textarea
                value={issueNote}
                onChange={(event) => setIssueNote(event.target.value.slice(0, 1000))}
                placeholder="Optional note"
                disabled={issueState === 'submitting'}
                maxLength={1000}
                rows={3}
                className="min-h-20 w-full rounded border border-zinc-700 bg-black/30 px-2 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-500 focus:border-blue-500/50 focus:outline-none disabled:cursor-default disabled:opacity-60"
              />
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIssueOpen(false)
                    setIssueError(null)
                  }}
                  disabled={issueState === 'submitting'}
                  className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px] text-zinc-200 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => { void handleSubmitIssue() }}
                  disabled={!issueReason || issueState === 'submitting'}
                  className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 font-mono text-[11px] text-blue-200 transition-colors hover:bg-blue-500/20 disabled:cursor-default disabled:opacity-60"
                >
                  {issueState === 'submitting' ? 'Submitting...' : 'Submit issue'}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
