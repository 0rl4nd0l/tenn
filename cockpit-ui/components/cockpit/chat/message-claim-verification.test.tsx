import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { ChatMessage, ClaimVerificationResponse } from '@/lib/cockpit-types'

import { MessageClaimVerification } from './message-claim-verification'

function assistantMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'assistant',
    content: 'BHP revenue was $10m.',
    timestamp: new Date('2026-04-29T10:00:00Z'),
    sources: [
      {
        title: 'BHP results',
        sourceId: 'doc-1:0',
        score: 0.9,
        snippet: 'BHP revenue was $10m.',
        kind: 'document',
      },
    ],
    ...overrides,
  }
}

const response: ClaimVerificationResponse = {
  ok: true,
  session_id: 'session-1',
  message_id: 'msg-1',
  checked_at: '2026-04-29T10:01:00Z',
  evidence_scope: 'visible_sources',
  evidence_count: 1,
  verdicts: [
    {
      claim_id: 'claim_1',
      claim_text: 'BHP revenue was $10m.',
      verdict: 'supported',
      short_reason: 'The claim matches supplied evidence.',
      supporting_source_ids: ['doc-1:0'],
      contradicting_source_ids: [],
      uncheckable_reason: null,
      confidence: 'medium',
    },
  ],
}

describe('MessageClaimVerification', () => {
  it('runs verification for an assistant message and renders the panel', async () => {
    const runner = vi.fn().mockResolvedValue(response)

    render(
      <MessageClaimVerification
        message={assistantMessage()}
        sessionId="session-1"
        parentPrompt="What did BHP report?"
        ticker="BHP"
        apiKey="test-key"
        verifyClaimsRunner={runner}
      >
        <button type="button">good</button>
      </MessageClaimVerification>,
    )

    expect(screen.getByRole('button', { name: 'good' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /verify against evidence/i }))

    await waitFor(() => expect(screen.getByText('Evidence check')).toBeInTheDocument())
    expect(screen.getByText(/does not audit the underlying data pipeline/i)).toBeInTheDocument()
    expect(screen.getByText('supported')).toBeInTheDocument()
    expect(screen.getByText('sources: doc-1:0')).toBeInTheDocument()
    expect(runner).toHaveBeenCalledWith(
      expect.objectContaining({
        sessionId: 'session-1',
        messageId: 'msg-1',
        parentPrompt: 'What did BHP report?',
        assistantText: 'BHP revenue was $10m.',
        ticker: 'BHP',
        visibleSources: expect.arrayContaining([
          expect.objectContaining({ sourceId: 'doc-1:0' }),
        ]),
      }),
      'test-key',
    )
  })

  it('hides the verify button when assistant text is empty', () => {
    render(
      <MessageClaimVerification
        message={assistantMessage({ content: '   ' })}
        sessionId="session-1"
        verifyClaimsRunner={vi.fn()}
      />,
    )

    expect(screen.queryByRole('button', { name: /verify against evidence/i })).not.toBeInTheDocument()
  })

  it('opens and submits the inline issue reporting flow', async () => {
    const runner = vi.fn().mockResolvedValue(response)
    const feedbackRunner = vi.fn().mockResolvedValue({
      ok: true,
      feedback_id: 'feedback-1',
      created_at: '2026-04-29T10:02:00Z',
      storage_path: '/tmp/review.sqlite',
    })

    render(
      <MessageClaimVerification
        message={assistantMessage({
          metadata: { model: 'model-a', source: 'api', latencyMs: 1234 },
        })}
        sessionId="session-1"
        parentMessageId="user-msg-1"
        parentPrompt="What did BHP report?"
        ticker="BHP"
        apiKey="test-key"
        verifyClaimsRunner={runner}
        submitFeedbackRunner={feedbackRunner}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /verify against evidence/i }))
    await screen.findByText('Evidence check')

    await userEvent.click(screen.getByRole('button', { name: /report issue/i }))
    expect(screen.getByRole('button', { name: /submit issue/i })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.queryByPlaceholderText('Optional note')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /report issue/i }))
    expect(screen.getByRole('button', { name: /irrelevant/i })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /poor structure/i }))
    await userEvent.type(screen.getByPlaceholderText('Optional note'), 'Number does not match source')
    await userEvent.click(screen.getByRole('button', { name: /submit issue/i }))

    await waitFor(() => expect(feedbackRunner).toHaveBeenCalledWith(
      expect.objectContaining({
        sessionId: 'session-1',
        messageId: 'msg-1',
        parentMessageId: 'user-msg-1',
        reasonCode: 'poor_structure',
        note: 'Number does not match source',
        queryText: 'What did BHP report?',
        finalAnswerText: 'BHP revenue was $10m.',
        ticker: 'BHP',
        routeType: 'api',
        modelLabel: 'model-a',
        responseLatencyMs: 1234,
        verifierResult: response,
        visibleSources: expect.arrayContaining([
          expect.objectContaining({ sourceId: 'doc-1:0' }),
        ]),
      }),
      'test-key',
    ))
    expect(await screen.findByText('Issue reported')).toBeInTheDocument()
  })

  it('shows an error state when issue reporting fails', async () => {
    const runner = vi.fn().mockResolvedValue(response)
    const feedbackRunner = vi.fn().mockRejectedValue(new Error('write failed'))

    render(
      <MessageClaimVerification
        message={assistantMessage()}
        sessionId="session-1"
        verifyClaimsRunner={runner}
        submitFeedbackRunner={feedbackRunner}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /verify against evidence/i }))
    await screen.findByText('Evidence check')
    await userEvent.click(screen.getByRole('button', { name: /report issue/i }))
    await userEvent.click(screen.getByRole('button', { name: /weak evidence/i }))
    await userEvent.click(screen.getByRole('button', { name: /submit issue/i }))

    expect(await screen.findByText('write failed')).toBeInTheDocument()
  })
})
