import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { JobDetailPanel } from './job-detail-panel'

const getOpsJob = vi.fn()
const getOpsJobEvents = vi.fn()
const getOpsJobArtifacts = vi.fn()
const stopActionJob = vi.fn()

vi.mock('@/lib/ops-api-client', () => ({
  getOpsJob: (...args: unknown[]) => getOpsJob(...args),
  getOpsJobEvents: (...args: unknown[]) => getOpsJobEvents(...args),
  getOpsJobArtifacts: (...args: unknown[]) => getOpsJobArtifacts(...args),
}))

vi.mock('@/lib/api-client', () => ({
  stopActionJob: (...args: unknown[]) => stopActionJob(...args),
}))

vi.mock('@/hooks/use-job-stream', () => ({
  useJobStream: () => ({
    recentEvents: [],
    activeJobs: new Map(),
    connected: true,
    error: null,
  }),
}))

describe('JobDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
    getOpsJob.mockResolvedValue({
      job_id: 'job-1',
      job_type: 'extraction',
      job_family: 'pipeline',
      status: 'running',
      phase: 'processing',
      title: 'Extract ABC report',
      summary: null,
      trigger_source: 'api',
      entity_scope: 'document',
      ticker: 'ABC',
      total_items: 2,
      succeeded_items: 1,
      failed_items: 0,
      skipped_items: 0,
      warning_count: 0,
      error_count: 0,
      current_item_label: 'doc-1',
      queued_at: '2026-04-21T00:00:00Z',
      started_at: '2026-04-21T00:00:05Z',
      updated_at: '2026-04-21T00:00:10Z',
      completed_at: null,
      elapsed_ms: 5000,
      metadata: { supports_cancellation: true },
    })
    getOpsJobEvents.mockResolvedValue({ items: [] })
    getOpsJobArtifacts.mockResolvedValue({ items: [] })
    stopActionJob.mockResolvedValue({
      ok: true,
      job_id: 'job-1',
      status: 'cancelling',
    })
  })

  it('shows a cancel button for cancellable running jobs and sends the stop request', async () => {
    render(<JobDetailPanel jobId="job-1" onClose={() => undefined} />)

    await waitFor(() => {
      expect(screen.getByText('Extract ABC report')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /cancel operation/i }))

    await waitFor(() => {
      expect(stopActionJob).toHaveBeenCalledWith('job-1')
    })
    expect(
      screen.getByText(/cancellation requested\. the operation will stop at the next safe checkpoint\./i),
    ).toBeInTheDocument()
  })

  it('hides the cancel button for completed jobs', async () => {
    getOpsJob.mockResolvedValue({
      job_id: 'job-2',
      job_type: 'extraction',
      job_family: 'pipeline',
      status: 'succeeded',
      phase: null,
      title: 'Extract DEF report',
      summary: 'done',
      trigger_source: 'api',
      entity_scope: 'document',
      ticker: 'DEF',
      total_items: 1,
      succeeded_items: 1,
      failed_items: 0,
      skipped_items: 0,
      warning_count: 0,
      error_count: 0,
      current_item_label: null,
      queued_at: '2026-04-21T00:00:00Z',
      started_at: '2026-04-21T00:00:05Z',
      updated_at: '2026-04-21T00:00:10Z',
      completed_at: '2026-04-21T00:00:11Z',
      elapsed_ms: 6000,
      metadata: { supports_cancellation: true },
    })

    render(<JobDetailPanel jobId="job-2" onClose={() => undefined} />)

    await waitFor(() => {
      expect(screen.getByText('Extract DEF report')).toBeInTheDocument()
    })

    expect(
      screen.queryByRole('button', { name: /cancel operation/i }),
    ).not.toBeInTheDocument()
  })
})
