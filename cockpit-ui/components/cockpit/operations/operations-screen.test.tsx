import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OperationsScreen } from './operations-screen'
import { useCockpitStore } from '@/lib/cockpit-store'

const apiMocks = vi.hoisted(() => ({
  checkHealth: vi.fn(),
  executeAction: vi.fn(),
  getActionJob: vi.fn(),
  getSystemStatus: vi.fn(),
  loadCockpitModel: vi.fn(),
  previewAction: vi.fn(),
  restartBackend: vi.fn(),
  startActionJob: vi.fn(),
}))

vi.mock('@/lib/api-client', () => ({
  checkHealth: (...args: unknown[]) => apiMocks.checkHealth(...args),
  executeAction: (...args: unknown[]) => apiMocks.executeAction(...args),
  getActionJob: (...args: unknown[]) => apiMocks.getActionJob(...args),
  getSystemStatus: (...args: unknown[]) => apiMocks.getSystemStatus(...args),
  loadCockpitModel: (...args: unknown[]) => apiMocks.loadCockpitModel(...args),
  previewAction: (...args: unknown[]) => apiMocks.previewAction(...args),
  restartBackend: (...args: unknown[]) => apiMocks.restartBackend(...args),
  startActionJob: (...args: unknown[]) => apiMocks.startActionJob(...args),
}))

vi.mock('@/components/cockpit/operations/job-list', () => ({
  JobList: () => <div data-testid="job-list" />,
}))

vi.mock('@/components/cockpit/operations/job-detail-panel', () => ({
  JobDetailPanel: () => <div data-testid="job-detail-panel" />,
}))

vi.mock('@/components/cockpit/operations/gpu-workload-card', () => ({
  GpuWorkloadCard: () => null,
}))

vi.mock('@/components/cockpit/gpu-activity-dialog', () => ({
  getGpuProcesses: () => [],
}))

const DEFAULT_PREFERENCES = {
  webSearchEnabled: true,
  ragEnabled: true,
  dbDiagnosticsEnabled: false,
  showSources: true,
  theme: 'dark' as const,
  marketplaceHomeLocation: '',
  marketplacePreferCloudRouting: false,
  chatRoutingPolicyOverride: 'config_default' as const,
  chatRuntimeTarget: 'local' as const,
  iphoneScale: false,
}

describe('OperationsScreen universe backfill review gate', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    window.HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
    window.HTMLElement.prototype.setPointerCapture = vi.fn()
    window.HTMLElement.prototype.releasePointerCapture = vi.fn()
    useCockpitStore.setState({
      activeTicker: '',
      apiDefaultEnabled: false,
      preferences: DEFAULT_PREFERENCES,
    })
    apiMocks.checkHealth.mockResolvedValue({ services: [] })
    apiMocks.previewAction.mockResolvedValue({
      command: ['python', 'scripts/backfill_asx_universe.py'],
      estimated_impact: 'all ASX ticker announcements',
      timeout_seconds: 3600,
      guard_message: 'backend ops queue',
    })
    apiMocks.getSystemStatus.mockResolvedValue({
      features: { extraction: true },
      anthropic_key_configured: false,
      llm_model: 'model:qwen3.5-35b-a3b-apex',
      extract_model: 'model:qwen3.5-35b-a3b-apex',
    })
    apiMocks.startActionJob.mockResolvedValue({
      action_id: 'universe_announcement_enrichment_backfill',
      job_id: 'ops-job-1',
      queued: true,
      status: 'queued',
    })
    apiMocks.getActionJob.mockResolvedValue({
      action_id: 'universe_announcement_enrichment_backfill',
      job_id: 'ops-job-1',
      status: 'success',
      result: 'complete',
    })
  })

  it('keeps Run Backfill disabled until the current settings are previewed', async () => {
    const user = userEvent.setup()
    render(<OperationsScreen />)

    const runBackfill = await screen.findByRole('button', { name: /run backfill/i })

    expect(runBackfill).toBeDisabled()
    expect(screen.getByText(/preview required before run backfill/i)).toBeInTheDocument()

    await user.click(runBackfill)

    expect(apiMocks.startActionJob).not.toHaveBeenCalled()
  })

  it('allows Run Backfill after a successful preview for the current settings', async () => {
    const user = userEvent.setup()
    render(<OperationsScreen />)

    await user.click(await screen.findByRole('button', { name: /preview run/i }))

    await waitFor(() => {
      expect(apiMocks.previewAction).toHaveBeenCalledWith({
        actionId: 'universe_announcement_enrichment_backfill',
        args: {
          total_days_back: 1825,
          process_documents: true,
        },
      })
    })
    expect(screen.getByText(/preview reviewed for current settings/i)).toBeInTheDocument()

    const runBackfill = screen.getByRole('button', { name: /run backfill/i })
    expect(runBackfill).toBeEnabled()

    await user.click(runBackfill)

    await waitFor(() => {
      expect(apiMocks.startActionJob).toHaveBeenCalledWith({
        actionId: 'universe_announcement_enrichment_backfill',
        args: {
          total_days_back: 1825,
          process_documents: true,
        },
      })
    })
  })

  it('resets review when the document-processing setting changes', async () => {
    const user = userEvent.setup()
    render(<OperationsScreen />)

    await user.click(await screen.findByRole('button', { name: /preview run/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run backfill/i })).toBeEnabled()
    })

    await user.click(screen.getByRole('switch'))

    const runBackfill = screen.getByRole('button', { name: /run backfill/i })
    expect(runBackfill).toBeDisabled()
    expect(screen.getByText(/preview required before run backfill/i)).toBeInTheDocument()

    apiMocks.startActionJob.mockClear()
    await user.click(runBackfill)

    expect(apiMocks.startActionJob).not.toHaveBeenCalled()
  })

  it('resets review when the history window changes', async () => {
    const user = userEvent.setup()
    render(<OperationsScreen />)

    await user.click(await screen.findByRole('button', { name: /preview run/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /run backfill/i })).toBeEnabled()
    })

    await user.click(screen.getAllByRole('combobox')[0])
    await user.click(await screen.findByRole('option', { name: '3 years' }))

    const runBackfill = screen.getByRole('button', { name: /run backfill/i })
    expect(runBackfill).toBeDisabled()
    expect(screen.getByText(/preview required before run backfill/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /preview run/i }))

    await waitFor(() => {
      expect(apiMocks.previewAction).toHaveBeenLastCalledWith({
        actionId: 'universe_announcement_enrichment_backfill',
        args: {
          total_days_back: 1095,
          process_documents: true,
        },
      })
    })
  })
})
