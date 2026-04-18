'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { CockpitSidebar } from './cockpit-sidebar'
import { CockpitStatusBar } from './cockpit-status-bar'
import { CockpitIssueCapture } from './cockpit-issue-capture'
import { checkHealth, isBackendHealthy as getBackendHealthy } from '@/lib/api-client'
import type { ServiceHealth } from '@/lib/cockpit-types'
import { useCockpitStore } from '@/lib/cockpit-store'
import { installBrowserDebugCollector } from '@/lib/browser-debug'
import { Separator } from '@/components/ui/separator'

interface CockpitLayoutProps {
  children: React.ReactNode
  title: string
}

export function CockpitLayout({ children, title }: CockpitLayoutProps) {
  const [backendHealthy, setBackendHealthy] = useState(false)
  const [backendLastHealthyAt, setBackendLastHealthyAt] = useState<Date | null>(null)
  const [backendError, setBackendError] = useState<string | null>(null)
  const [gpuHealth, setGpuHealth] = useState<ServiceHealth | null>(null)
  const [hostHealth, setHostHealth] = useState<ServiceHealth | null>(null)
  const captureRootRef = useRef<HTMLDivElement>(null)
  const { activeTicker, sessionStats, chatCompletionActive } = useCockpitStore()

  useEffect(() => {
    installBrowserDebugCollector()
  }, [])

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const res = await checkHealth()
        const healthy = getBackendHealthy(res)

        if (cancelled) return

        setBackendHealthy(healthy)
        setGpuHealth(res.services?.find((service) => service.name === 'gpu') ?? null)
        setHostHealth(res.services?.find((service) => service.name === 'host') ?? null)
        if (healthy) {
          setBackendLastHealthyAt(new Date())
          setBackendError(null)
          return
        }

        const backendService = res.services?.find((service) => service.name === 'backend')
        const statusSuffix = backendService?.status ? ` (${backendService.status})` : ''
        const detail = backendService?.error ?? 'No health response from backend service'
        setBackendError(`${detail}${statusSuffix}`)
      } catch (error) {
        if (cancelled) return
        setBackendHealthy(false)
        setGpuHealth(null)
        setBackendError(error instanceof Error ? error.message : 'Backend is unreachable')
      }
    }

    poll()
    const intervalMs = chatCompletionActive ? 3_000 : 15_000
    const interval = setInterval(poll, intervalMs)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [chatCompletionActive])

  return (
    <SidebarProvider>
      <CockpitSidebar 
        backendHealthy={backendHealthy} 
        backendLastHealthyAt={backendLastHealthyAt}
        backendError={backendError}
        gpuHealth={gpuHealth}
        hostHealth={hostHealth}
        sessionCost={sessionStats.totalCostUsd} 
      />
      <SidebarInset className="flex flex-col overflow-hidden">
        <div ref={captureRootRef} className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <div className="flex items-center gap-3">
              <h1 className="text-sm font-medium">{title}</h1>
              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-mono text-primary">
                {activeTicker}
              </span>
            </div>
            <div className="ml-auto">
              <Suspense>
                <CockpitIssueCapture
                  captureRootRef={captureRootRef}
                  pageTitle={title}
                  backendHealthy={backendHealthy}
                  backendLastHealthyAt={backendLastHealthyAt}
                  backendError={backendError}
                  gpuHealth={gpuHealth}
                  hostHealth={hostHealth}
                />
              </Suspense>
            </div>
          </header>
          <main className="flex-1 overflow-hidden">
            {children}
          </main>
          <CockpitStatusBar
            backendHealthy={backendHealthy}
            backendLastHealthyAt={backendLastHealthyAt}
            backendError={backendError}
          />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
