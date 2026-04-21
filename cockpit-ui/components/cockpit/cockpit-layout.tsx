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
import { Smartphone, Monitor } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

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
  const { activeTicker, sessionStats, chatCompletionActive, preferences, updatePreferences } = useCockpitStore()

  const isIPhoneScale = preferences.iphoneScale

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
      <SidebarInset className={cn(
        "flex flex-col overflow-hidden transition-all duration-300",
        isIPhoneScale && "bg-muted/30 items-center justify-center p-4 lg:p-8"
      )}>
        <div 
          ref={captureRootRef} 
          className={cn(
            "flex min-h-0 flex-1 flex-col overflow-hidden transition-all duration-500",
            isIPhoneScale 
              ? "w-[390px] h-[844px] max-h-full rounded-[3rem] border-[12px] border-muted-foreground/20 shadow-[0_0_50px_-12px_rgba(0,0,0,0.5)] relative bg-background" 
              : "w-full"
          )}
        >
          {isIPhoneScale && (
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-7 bg-muted-foreground/20 rounded-b-3xl z-50 flex items-center justify-center backdrop-blur-md">
              <div className="w-12 h-1.5 bg-background/40 rounded-full" />
            </div>
          )}
          <header className={cn(
            "flex h-12 shrink-0 items-center gap-2 border-b border-border transition-all duration-300",
            isIPhoneScale ? "px-6 pt-2" : "px-4"
          )}>
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <div className="flex items-center gap-3 overflow-hidden">
              <h1 className="text-sm font-medium truncate">{title}</h1>
              {!isIPhoneScale && (
                <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-mono text-primary shrink-0">
                  {activeTicker}
                </span>
              )}
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-full hover:bg-primary/10 transition-colors"
                onClick={() => updatePreferences({ iphoneScale: !isIPhoneScale })}
                title={isIPhoneScale ? "Switch to Desktop Scale" : "Switch to iPhone Scale"}
              >
                {isIPhoneScale ? <Monitor className="h-4 w-4" /> : <Smartphone className="h-4 w-4" />}
              </Button>
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
            compact={isIPhoneScale}
          />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
