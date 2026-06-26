import { render } from '@testing-library/react'
import type { ComponentProps } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ReviewTabPanel } from './review-tab-panel'

type ReviewTabPanelProps = ComponentProps<typeof ReviewTabPanel>

const noop = vi.fn()

const baseProps: ReviewTabPanelProps = {
  documents: [],
  documentsLoading: false,
  docsLimit: '5',
  extraDocumentIds: '',
  reviewError: null,
  reviewActionLoading: false,
  reviewSession: null,
  reviewSessionLoadingMessage: null,
  wrongQueue: null,
  recentRuns: [
    {
      run_id: 'run-1',
      document_id: 'doc-1',
      status: 'completed',
      created_at: '2026-05-31T00:00:00Z',
      metrics_count: 3,
      review_ready: true,
    },
  ],
  recentRunsLoading: false,
  recentRunsError: null,
  recentReviewSessions: [
    {
      session_id: 'session-1',
      created_at: '2026-05-31T00:00:00Z',
      updated_at: '2026-05-31T00:10:00Z',
      tickers: ['BHP'],
      titles: ['BHP review'],
      document_ids: ['doc-1'],
      run_ids: ['run-1'],
      item_count: 2,
    },
  ],
  recentReviewSessionsLoading: false,
  recentReviewSessionsError: null,
  selectedRunId: '',
  selectedReviewSessionId: '',
  selectedDocumentId: '',
  selectedReviewDocumentIds: [],
  currentReviewItem: null,
  currentReviewIndex: 0,
  currentEvidenceQuality: 'missing',
  matchedEvidenceText: null,
  currentSnippetPath: null,
  currentSnippetUrl: null,
  currentSnippetRenderKey: 'empty',
  currentRowRef: null,
  reviewItems: [],
  evidenceSuspendMessage: null,
  snippetImageState: {
    key: null,
    status: 'idle',
    retryAttempted: false,
    message: null,
  },
  hasPrevReviewItem: false,
  hasNextReviewItem: false,
  onDocsLimitChange: noop,
  onExtraDocumentIdsChange: noop,
  onLoadDocuments: noop,
  onRunExtraction: noop,
  onLoadReview: noop,
  onRefreshWrongQueue: noop,
  onExportReviewArtifacts: noop,
  onSelectedRunIdChange: noop,
  onLoadRecentRuns: noop,
  onInspectSelectedRun: noop,
  onSelectedReviewSessionIdChange: noop,
  onLoadReviewSessions: noop,
  onInspectSelectedReviewSession: noop,
  onSelectedDocumentIdChange: noop,
  onMoveReviewSelection: noop,
  onSelectedReviewItemIdChange: noop,
  onSnippetImageLoad: noop,
  onSnippetImageError: noop,
  onSubmitReview: noop,
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ReviewTabPanel', () => {
  it('keeps optional review selectors controlled across selection changes', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)

    const { rerender } = render(<ReviewTabPanel {...baseProps} />)

    rerender(
      <ReviewTabPanel
        {...baseProps}
        selectedRunId="run-1"
        selectedReviewSessionId="session-1"
      />,
    )
    rerender(<ReviewTabPanel {...baseProps} />)

    const errors = consoleError.mock.calls.map((call) => call.join(' ')).join('\n')
    expect(errors).not.toMatch(/uncontrolled/i)
  })
})
