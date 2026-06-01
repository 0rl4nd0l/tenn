import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getQueueStatus, listDocuments, rerunJob } from '@/lib/api-client'
import { HistoryScreen } from './history-screen'

vi.mock('@/lib/api-client', () => ({
  getQueueStatus: vi.fn(),
  listDocuments: vi.fn(),
  rerunJob: vi.fn(),
}))

vi.mock('@/lib/cockpit-store', () => ({
  useCockpitStore: () => ({
    preferences: {
      iphoneScale: false,
    },
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}))

const listDocumentsMock = vi.mocked(listDocuments)
const getQueueStatusMock = vi.mocked(getQueueStatus)
const rerunJobMock = vi.mocked(rerunJob)

function renderHistoryScreen() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  })

  render(
    <QueryClientProvider client={queryClient}>
      <HistoryScreen />
    </QueryClientProvider>,
  )
}

describe('HistoryScreen timestamp truth', () => {
  beforeEach(() => {
    listDocumentsMock.mockReset()
    getQueueStatusMock.mockReset()
    rerunJobMock.mockReset()
  })

  it('does not turn document inventory without execution timestamps into Just now completed jobs', async () => {
    listDocumentsMock.mockResolvedValue([
      {
        id: 'doc-0',
        title: 'BHP annual report',
        filename: 'bhp-annual-report.pdf',
        published_at: '2026-05-01T00:00:00Z',
      },
    ])
    getQueueStatusMock.mockResolvedValue({
      pending: 0,
      active: 0,
      completed: 0,
      failed: 0,
    })

    renderHistoryScreen()

    expect(await screen.findByText('Document Inventory')).toBeInTheDocument()
    expect(screen.getByText('History Rows')).toBeInTheDocument()
    expect(screen.queryByText('Total Jobs')).not.toBeInTheDocument()
    expect(screen.getByText('inventory')).toBeInTheDocument()
    expect(screen.getByText('DATA_MISSING')).toBeInTheDocument()
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.getByText('Read-only')).toBeInTheDocument()
    expect(screen.queryByText('document_ingestion')).not.toBeInTheDocument()
    expect(screen.queryByText('Just now')).not.toBeInTheDocument()
    expect(screen.queryByText('0ms')).not.toBeInTheDocument()
  })

  it('keeps queue summary rows honest when no execution timestamp is available', async () => {
    listDocumentsMock.mockResolvedValue([])
    getQueueStatusMock.mockResolvedValue({
      pending: 2,
      active: 0,
      completed: 3,
      failed: 0,
    })

    renderHistoryScreen()

    expect(await screen.findByText('Queue Snapshot')).toBeInTheDocument()
    expect(screen.getByText('queue snapshot')).toBeInTheDocument()
    expect(screen.getByText('DATA_MISSING')).toBeInTheDocument()
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.getByText('Read-only')).toBeInTheDocument()
    expect(screen.queryByText('Just now')).not.toBeInTheDocument()
    expect(screen.queryByText('0ms')).not.toBeInTheDocument()
  })
})
