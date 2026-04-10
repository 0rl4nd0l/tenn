'use client'

import React, { useState } from 'react'
import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { ScopeTerminal } from '@/components/intel-ops/scope-terminal'
import { PipelineRibbon } from '@/components/intel-ops/pipeline-ribbon'
import { DiagnosticMatrix } from '@/components/intel-ops/diagnostic-matrix'
import { FailureRegistry } from '@/components/intel-ops/failure-registry'
import { IntelInspector } from '@/components/intel-ops/intel-inspector'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import { useQuery } from '@tanstack/react-query'
import { getIntelPulse } from '@/lib/api-client'

export default function IntelOpsPage() {
  const [scope, setScope] = useState<'global' | 'company'>('global')
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)
  const [activeStage, setActiveStage] = useState<string>('overview')

  const { data: pulseData, isLoading } = useQuery({
    queryKey: ['intel-pulse', selectedCompany],
    queryFn: () => getIntelPulse(selectedCompany || undefined),
    refetchInterval: 30000,
  })

  const handleCompanySelect = (company: string | null) => {
    if (company) {
      setScope('company')
      setSelectedCompany(company)
    } else {
      setScope('global')
      setSelectedCompany(null)
    }
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
          />
          <PipelineRibbon 
            activeStage={activeStage} 
            onStageSelect={setActiveStage} 
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
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div className="terminal-panel p-4 rounded-lg border border-border">
                          <h3 className="text-xs font-mono text-muted-foreground uppercase mb-2">Population Index</h3>
                          <div className="text-2xl font-mono text-primary">[ {pulseData?.stats.population_index || 0}% ]</div>
                          <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary" style={{ width: `${pulseData?.stats.population_index || 0}%` }} />
                          </div>
                        </div>
                        <div className="terminal-panel p-4 rounded-lg border border-border">
                          <h3 className="text-xs font-mono text-muted-foreground uppercase mb-2">Trust Score (AVG)</h3>
                          <div className="text-2xl font-mono text-[oklch(0.69_0.22_145)]">[ {pulseData?.stats.trust_score_avg || 0} ]</div>
                          <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-[oklch(0.69_0.22_145)]" style={{ width: `${(pulseData?.stats.trust_score_avg || 0) * 100}%` }} />
                          </div>
                        </div>
                        <div className="terminal-panel p-4 rounded-lg border border-border">
                          <h3 className="text-xs font-mono text-muted-foreground uppercase mb-2">Quarantine Rate</h3>
                          <div className="text-2xl font-mono text-destructive">[ {pulseData?.stats.quarantine_rate || 0}% ]</div>
                          <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-destructive" style={{ width: `${pulseData?.stats.quarantine_rate || 0}%` }} />
                          </div>
                        </div>
                      </div>
                      <FailureRegistry compact failures={pulseData?.failures} />
                    </TabsContent>
                    
                    <TabsContent value="extraction" className="mt-0">
                      <DiagnosticMatrix stage="extraction" _scope={scope} company={selectedCompany} />
                    </TabsContent>

                    <TabsContent value="evaluation" className="mt-0">
                      <DiagnosticMatrix stage="evaluation" _scope={scope} company={selectedCompany} />
                    </TabsContent>

                    <TabsContent value="signals" className="mt-0">
                      <div className="terminal-panel p-8 text-center text-muted-foreground font-mono">
                        [ SIGNALS_LAYER_MAP_LOADER: PENDING ]
                      </div>
                    </TabsContent>

                    <TabsContent value="failures" className="mt-0">
                      <FailureRegistry failures={pulseData?.failures} />
                    </TabsContent>
                  </Tabs>
                )}
              </div>
            </ResizablePanel>
            
            <ResizableHandle withHandle />
            
            <ResizablePanel defaultSize={25} minSize={20}>
              <IntelInspector />
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </CockpitLayout>
  )
}
