import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  GpuActivityDialog,
  getGpuProcessSummary,
} from './gpu-activity-dialog'
import type { ServiceHealth } from '@/lib/cockpit-types'

const degradedGpuHealth: ServiceHealth = {
  name: 'gpu',
  status: 'degraded',
  error: 'nvidia-smi query failed',
  details: {
    gpus: [],
    processes: [],
  },
}

describe('GPU activity telemetry states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not present failed process telemetry as an idle GPU', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          error: 'nvidia-smi query failed',
          details: {
            gpus: [],
            processes: [],
          },
        }),
      })),
    )

    render(
      <GpuActivityDialog gpuHealth={degradedGpuHealth}>
        <button type="button">Open GPU activity</button>
      </GpuActivityDialog>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Open GPU activity' }))

    expect(await screen.findByText('GPU telemetry unavailable. Empty GPU rows do not prove the GPU is idle.')).toBeInTheDocument()
    expect(screen.getByText('GPU process telemetry unavailable. Empty process rows do not prove the GPU is idle.')).toBeInTheDocument()
    expect(screen.queryByText('No active GPU compute processes reported.')).not.toBeInTheDocument()
  })

  it('keeps the confirmed process count copy when backend telemetry reports processes', () => {
    const health: ServiceHealth = {
      name: 'gpu',
      status: 'healthy',
      details: {
        processes: [
          { pid: 101, process_name: 'llama-server' },
          { pid: 102, process_name: 'python' },
        ],
      },
    }

    expect(getGpuProcessSummary(health)).toBe('2 active GPU processes')
  })

  it('marks sidebar process telemetry unavailable when backend returns a GPU probe error', () => {
    expect(getGpuProcessSummary(degradedGpuHealth)).toBe('GPU process telemetry unavailable')
  })
})
