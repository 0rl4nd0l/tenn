import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DiagnosticMatrix } from './diagnostic-matrix'
import { FailureRegistry } from './failure-registry'
import { PipelineRibbon } from './pipeline-ribbon'
import { ScopeTerminal } from './scope-terminal'
import { getDiagnosticMatrix } from '@/lib/api-client'

vi.mock('@/lib/api-client', () => ({
  getDiagnosticMatrix: vi.fn(),
}))

const getDiagnosticMatrixMock = vi.mocked(getDiagnosticMatrix)

function renderWithQueryClient(node: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(<QueryClientProvider client={queryClient}>{node}</QueryClientProvider>)
}

describe('Intel Ops accessible controls', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('labels the company scope search and clear controls', async () => {
    const onCompanySelect = vi.fn()

    const { rerender } = render(
      <ScopeTerminal
        scope="global"
        selectedCompany={null}
        onCompanySelect={onCompanySelect}
      />,
    )

    await userEvent.type(screen.getByRole('textbox', { name: /search company entity scope/i }), 'bhp')

    expect(onCompanySelect).toHaveBeenCalled()

    rerender(
      <ScopeTerminal
        scope="company"
        selectedCompany="BHP"
        onCompanySelect={onCompanySelect}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /clear company entity scope/i }))

    expect(onCompanySelect).toHaveBeenLastCalledWith(null)
  })

  it('labels pipeline stage controls by action and stage', async () => {
    const onStageSelect = vi.fn()
    const onStageInspect = vi.fn()

    render(
      <PipelineRibbon
        activeStage="overview"
        onStageSelect={onStageSelect}
        onStageInspect={onStageInspect}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /inspect extraction pipeline stage/i }))

    expect(onStageSelect).toHaveBeenCalledWith('extraction')
    expect(onStageInspect).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'extraction',
        label: 'EXTRACTION',
      }),
    )
  })

  it('labels diagnostic matrix cells with stage, entity, metric, and state', async () => {
    const onCellSelect = vi.fn()
    getDiagnosticMatrixMock.mockResolvedValue({
      stage: 'extraction',
      entities: [
        {
          entity: 'BHP',
          metrics: {
            revenue: 'populated',
            ebit: 'failed',
          },
        },
      ],
    })

    renderWithQueryClient(
      <DiagnosticMatrix
        stage="extraction"
        _scope="global"
        company={null}
        onCellSelect={onCellSelect}
      />,
    )

    await userEvent.click(
      await screen.findByRole('button', {
        name: /inspect extraction matrix cell for BHP revenue: populated/i,
      }),
    )

    expect(onCellSelect).toHaveBeenCalledWith({
      stage: 'extraction',
      entity: 'BHP',
      metric: 'revenue',
      state: 'populated',
    })
  })

  it('labels failure registry controls without relying on row text alone', async () => {
    const onFailureSelect = vi.fn()
    const failure = {
      id: 'fail-1',
      entity: 'BHP',
      type: 'EXTRACTION_FAIL',
      message: 'source evidence missing',
      confidence: 0.42,
      timestamp: '2026-06-02T07:00:00Z',
    }

    render(<FailureRegistry failures={[failure]} onFailureSelect={onFailureSelect} />)

    expect(
      screen.getByRole('button', { name: /failure registry retry controls are read-only/i }),
    ).toBeDisabled()

    await userEvent.click(screen.getByRole('button', { name: /inspect failure fail-1 for BHP/i }))

    expect(onFailureSelect).toHaveBeenCalledWith(failure)
  })
})
