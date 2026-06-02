import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HistoryScreen } from './history-screen'

const listDocuments = vi.fn()
const getQueueStatus = vi.fn()
const rerunJob = vi.fn()

vi.mock('@/lib/api-client', () => ({
  listDocuments: () => listDocuments(),
  getQueueStatus: () => getQueueStatus(),
  rerunJob: (...args: unknown[]) => rerunJob(...args),
}))

function renderHistoryScreen() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <HistoryScreen />
    </QueryClientProvider>,
  )
}

describe('HistoryScreen accessibility', () => {
  beforeEach(() => {
    listDocuments.mockResolvedValue([
      {
        id: 'job-1',
        title: 'BHP annual report',
        filename: 'bhp-annual.pdf',
        status: 'completed',
        created_at: '2026-06-01T00:00:00Z',
      },
    ])
    getQueueStatus.mockResolvedValue({ pending: 0, active: 0, completed: 1, failed: 0 })
    rerunJob.mockResolvedValue(undefined)
  })

  it('exposes job details controls with durable accessible names', async () => {
    renderHistoryScreen()

    await waitFor(() => {
      expect(screen.getByText('job-1')).toBeInTheDocument()
    })

    expect(screen.getByRole('columnheader', { name: /job details/i })).toBeInTheDocument()

    const expandButton = screen.getByRole('button', { name: /expand job job-1/i })
    expect(expandButton).toBeInTheDocument()

    await userEvent.click(expandButton)

    expect(screen.getByRole('button', { name: /collapse job job-1/i })).toBeInTheDocument()
  })
})
