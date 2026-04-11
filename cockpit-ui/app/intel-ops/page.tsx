'use client'

import React, { useState } from 'react'
import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { ScopeTerminal } from '@/components/intel-ops/scope-terminal'
import { PipelineRibbon } from '@/components/intel-ops/pipeline-ribbon'
import { DiagnosticMatrix } from '@/components/intel-ops/diagnostic-matrix'
import { FailureRegistry } from '@/components/intel-ops/failure-registry'
import { IntelInspector, type IntelInspectorSelection } from '@/components/intel-ops/intel-inspector'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import { useQuery } from '@tanstack/react-query'
import { getIntelPulse } from '@/lib/api-client'

export default function IntelOpsPage() {
  const [scope, setScope] = useState<'global' | 'company'>('global')
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)
  const [activeStage, setActiveStage] = useState<string>('overview')
  const [inspectorSelection, setInspectorSelection] = useState<IntelInspectorSelection | null>(null)

  const { data: pulseData, isLoading, error: pulseError, dataUpdatedAt } = useQuery({
    queryKey: ['intel-pulse', selectedCompany],
    queryFn: () => getIntelPulse(selectedCompany || undefined),
    staleTime: 10_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  })

  const handleCompanySelect = (company: string | null) => {
    const normalizedCompany = company?.trim().toUpperCase() || null

    if (normalizedCompany) {
      setScope('company')
      setSelectedCompany(normalizedCompany)
    } else {
      setScope('global')
      setSelectedCompany(null)
    }

    setInspectorSelection(null)
  }

  const pulseErrorMessage = pulseError instanceof Error ? pulseError.message : null
  const streamStatus = pulseErrorMessage ? 'error' : isLoading ? 'loading' : 'live'

  const inspectStage = (stage: { id: string; label: string; health?: number | null; status: string }) => {
    setInspectorSelection({
      kind: 'stage',
      title: stage.label,
      subtitle: selectedCompany ? `Ticker ${selectedCompany}` : 'Global system scope',
      status: stage.status.toUpperCase(),
      rawMetadata: {
        stage_id: stage.id,
        label: stage.label,
        health: stage.health,
        status: stage.status,
        scope,
        ticker: selectedCompany,
        stats: pulseData?.stats ?? null,
      },
      trace: [
        { label: 'SCOPE', status: selectedCompany ? 'COMPANY' : 'GLOBAL', time: selectedCompany ?? '--' },
        { label: 'PIPELINE_STAGE', status: stage.status.toUpperCase(), time: stage.health == null ? '--' : `${stage.health}%` },
      ],
      linkedEntities: [selectedCompany ?? 'SYSTEM'],
      notes: [
        'Stage health is sourced from the Intel Pulse summary endpoint.',
        'No deeper provenance endpoint is currently wired for pipeline-stage inspection.',
      ],
    })
  }

  const inspectFailure = (failure: {
    id: string
    entity: string
    type: string
    message: string
    confidence: number
    timestamp: string
  }) => {
    setInspectorSelection({
      kind: 'failure',
      title: `${failure.type} :: ${failure.id}`,
      subtitle: failure.entity,
      status: 'FAILED',
      rawMetadata: { ...failure, scope, ticker: selectedCompany },
      trace: [
        { label: 'FAILURE_REGISTRY', status: 'FAILED', time: failure.timestamp },
        { label: 'ENTITY_SCOPE', status: failure.entity, time: selectedCompany ?? '--' },
      ],
      linkedEntities: [failure.entity],
      notes: [
        'Failure rows are live backend records from recent extraction failures.',
        'Retry execution is not wired on this surface yet, so this registry is read-only.',
      ],
    })
  }

  const inspectMatrixCell = ({
    stage,
    entity,
    metric,
    state,
  }: {
    stage: string
    entity: string
    metric: string
    state: 'populated' | 'abstain' | 'failed' | 'sparse'
  }) => {
    setInspectorSelection({
      kind: 'matrix-cell',
      title: `${entity} :: ${metric}`,
      subtitle: `${stage.toUpperCase()} density matrix`,
      status: state.toUpperCase(),
      rawMetadata: {
        entity,
        metric,
        stage,
        state,
        scope,
        ticker: selectedCompany,
      },
      trace: [
        { label: 'MATRIX_STAGE', status: stage.toUpperCase(), time: '--' },
        { label: 'METRIC_STATE', status: state.toUpperCase(), time: metric },
      ],
      linkedEntities: [entity, metric],
      notes: [
        'Matrix states are live API values: populated, abstain (low confidence on evaluation), failed (null metric with failed extraction on source document), or sparse.',
        'EPS uses np_attributable / shares_outstanding when both are present; EBIT maps to column ebit.',
      ],
    })
  }

  return (
    <CockpitLayout title="Intel Pulse">
      <div className="flex flex-col h-full bg-background font-sans overflow-hidden">
        {/* Top Control Bar */}
        <div className="border-b border-border p-4 space-y-4 bg-background/50 backdrop-blur-sm">
          <ScopeTerminal 
            scope={scope} 
            selectedCompany={selectedCompany} 
            onCompanySelect={handleCompanySelect} 
            streamStatus={streamStatus}
          />
          <PipelineRibbon 
            activeStage={activeStage} 
            onStageSelect={setActiveStage} 
            onStageInspect={inspectStage}
            pipeline={pulseData?.pipeline}
          />
        </div>

        {/* Main Workspace */}
        <div className="flex-1 overflow-hidden">
          <ResizablePanelGroup direction="horizontal">
            <ResizablePanel defaultSize={75} minSize={50}>
              <div className="h-full overflow-y-auto p-4 terminal-container">
                {isLoading ? (
                  <div className="flex items-center justify-center h-full font-mono text-muted-foreground animate-pulse">
                    [ INITIALIZING_PULSE_DATA_STREAM... ]
                  </div>
                ) : (
                  <Tabs value={activeStage} onValueChange={setActiveStage} className="w-full">
                    <TabsContent value="overview" className="mt-0 space-y-6">
                      {pulseErrorMessage ? (
                        <div className="terminal-panel rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-[11px] font-mono text-destructive whitespace-pre-wrap break-words">
                          [ PULSE_QUERY_ERROR ]{'\n'}
                          {pulseErrorMessage}
                        </div>
                      ) : !pulseData ? (
                        <div className="terminal-panel rounded-lg border border-border p-4 text-[11px] font-mono text-muted-foreground whitespace-pre-wrap break-words">
                          [ NO_DATA_AVAILABLE ]
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <div className="terminal-panel p-4 rounded-lg border border-border">
                            <h3 className="text-xs font-mono text-muted-foreground uppercase mb-3">Storage levels (canonical DB)</h3>
                            <dl className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-2 text-[11px] font-mono">
                              <div>
                                <dt className="text-muted-foreground">documents</dt>
                                <dd className="text-primary font-semibold">{pulseData.stats.document_count}</dd>
                              </div>
                              <div>
                                <dt className="text-muted-foreground">periodic_rows_total</dt>
                                <dd className="text-primary font-semibold">
                                  {pulseData.stats.periodic_financial_rows_total ?? '—'}
                                </dd>
                              </div>
                              <div>
                                <dt className="text-muted-foreground">extraction_runs</dt>
                                <dd className="text-primary font-semibold">
                                  {pulseData.stats.extraction_runs_total ?? '—'}
                                </dd>
                              </div>
                              <div>
                                <dt className="text-muted-foreground">sample_rows (population calc)</dt>
                                <dd className="text-primary font-semibold">
                                  {pulseData.stats.recent_financial_rows_sampled ?? pulseData.stats.extraction_count}
                                </dd>
                              </div>
                              <div>
                                <dt className="text-muted-foreground">signals (reserved)</dt>
                                <dd className="text-muted-foreground">{pulseData.stats.signal_count}</dd>
                              </div>
                              <div>
                                <dt className="text-muted-foreground">memory (reserved)</dt>
                                <dd className="text-muted-foreground">{pulseData.stats.memory_count}</dd>
                              </div>
                            </dl>
                            <p className="mt-3 text-[10px] font-mono text-muted-foreground leading-relaxed">
                              Population index uses the last {pulseData.stats.recent_financial_rows_sampled ?? pulseData.stats.extraction_count} periodic row(s) in scope, not the full periodic table.
                            </p>
                          </div>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] font-mono text-muted-foreground border-b border-border/60 pb-3">
                            <span>
                              generated_at:{' '}
                              <span className="text-foreground/90">
                                {pulseData.generated_at
                                  ? new Date(pulseData.generated_at).toISOString()
                                  : '—'}
                              </span>
                            </span>
                            <span>
                              client_refetch:{' '}
                              <span className="text-foreground/90">
                                {dataUpdatedAt ? new Date(dataUpdatedAt).toISOString() : '—'}
                              </span>
                            </span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <div className="terminal-panel p-4 rounded-lg border border-border">
                              <h3 className="text-xs font-mono text-muted-foreground uppercase mb-2">Population Index</h3>
                              <div className="text-2xl font-mono text-primary">[ {`${pulseData.stats.population_index}%`} ]</div>
                              <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-primary" style={{ width: `${pulseData.stats.population_index}%` }} />
                              </div>
                            </div>
                            <div className="terminal-panel p-4 rounded-lg border border-border">
                              <h3 className="text-xs font-mono text-muted-foreground uppercase mb-2">Trust Score (AVG)</h3>
                              <div className="text-2xl font-mono text-[oklch(0.69_0.22_145)]">[ {pulseData.stats.trust_score_avg} ]</div>
                              <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                                <div className="h-full bg-[oklch(0.69_0.22_145)]" style={{ width: `${pulseData.stats.trust_score_avg * 100}%` }} />
                              </div>
                            </div>
                            <div className="terminal-panel p-4 rounded-lg border border-border">
                              <h3 className="text-xs font-mono text-muted-foreground uppercase mb-2">Extraction failure rate</h3>
                              <div className="text-2xl font-mono text-destructive">
                                [
                                {' '}
                                {pulseData.stats.extraction_failure_rate_pct ?? pulseData.stats.quarantine_rate}
                                % ]
                              </div>
                              <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-destructive"
                                  style={{
                                    width: `${pulseData.stats.extraction_failure_rate_pct ?? pulseData.stats.quarantine_rate}%`,
                                  }}
                                />
                              </div>
                              <p className="mt-2 text-[10px] font-mono text-muted-foreground">
                                failed extraction_runs ÷ documents in scope (same as legacy quarantine_rate).
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                      <FailureRegistry
                        compact
                        failures={pulseData?.failures}
                        unavailableMessage={pulseErrorMessage}
                        onFailureSelect={inspectFailure}
                      />
                    </TabsContent>
                    
                    <TabsContent value="extraction" className="mt-0">
                      <DiagnosticMatrix
                        stage="extraction"
                        _scope={scope}
                        company={selectedCompany}
                        onCellSelect={inspectMatrixCell}
                      />
                    </TabsContent>

                    <TabsContent value="evaluation" className="mt-0">
                      <DiagnosticMatrix
                        stage="evaluation"
                        _scope={scope}
                        company={selectedCompany}
                        onCellSelect={inspectMatrixCell}
                      />
                    </TabsContent>

                    <TabsContent value="signals" className="mt-0">
                      <UnavailableStagePanel
                        code="SIGNALS_UNAVAILABLE"
                        message="Intel Pulse does not yet have a canonical backend signals feed on this surface. No synthetic signal map is rendered."
                      />
                    </TabsContent>

                    <TabsContent value="memory" className="mt-0">
                      <UnavailableStagePanel
                        code="MEMORY_UNAVAILABLE"
                        message="Intel Pulse does not yet expose a canonical memory dataset on this surface. The stage remains visible, but the panel is intentionally read-only."
                      />
                    </TabsContent>

                    <TabsContent value="failures" className="mt-0">
                      <FailureRegistry
                        failures={pulseData?.failures}
                        unavailableMessage={pulseErrorMessage}
                        onFailureSelect={inspectFailure}
                      />
                    </TabsContent>
                  </Tabs>
                )}
              </div>
            </ResizablePanel>
            
            <ResizableHandle withHandle />
            
            <ResizablePanel defaultSize={25} minSize={20}>
              <IntelInspector selection={inspectorSelection} dataError={pulseErrorMessage} />
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </CockpitLayout>
  )
}

function UnavailableStagePanel({ code, message }: { code: string; message: string }) {
  return (
    <div className="terminal-panel rounded-lg border border-border p-8 text-center font-mono">
      <div className="text-[11px] text-muted-foreground">[ {code} ]</div>
      <div className="mt-3 text-[12px] text-muted-foreground max-w-2xl mx-auto leading-relaxed">
        {message}
      </div>
    </div>
  )
}
