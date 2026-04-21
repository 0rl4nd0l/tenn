'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { CockpitSidebar } from './cockpit-sidebar'
import { CockpitStatusBar } from './cockpit-status-bar'
import { CockpitIssueCapture } from './cockpit-issue-capture'
import {
  checkHealth,
  getCockpitPreferences,
  isBackendHealthy as getBackendHealthy,
  patchCockpitPreferences,
} from '@/lib/api-client'
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
  const [preferencesHydrated, setPreferencesHydrated] = useState(false)
  const [scale, setScale] = useState(1)
  const captureRootRef = useRef<HTMLDivElement>(null)
  const syncedPreferencesRef = useRef('')
  const {
    activeTicker,
    sessionStats,
    chatCompletionActive,
    apiDefaultEnabled,
    setApiDefaultEnabled,
    preferences,
    updatePreferences,
  } = useCockpitStore()

  const isIPhoneScale = preferences.iphoneScale

  useEffect(() => {
    installBrowserDebugCollector()
  }, [])

  useEffect(() => {
    if (!isIPhoneScale) {
      setScale(1)
      return
    }

    const handleResize = () => {
      // iPhone 11 height is 896px.
      const targetHeight = 896 + 100 // Frame + breathing room
      const availableHeight = window.innerHeight
      if (availableHeight < targetHeight) {
        setScale(Math.max(0.4, availableHeight / targetHeight))
      } else {
        setScale(1)
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [isIPhoneScale])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const remote = await getCockpitPreferences()
        if (cancelled) return
        setApiDefaultEnabled(Boolean(remote.api_default_enabled))
        updatePreferences({
          marketplacePreferCloudRouting: Boolean(remote.marketplace_prefer_cloud_routing),
        })
        syncedPreferencesRef.current = JSON.stringify({
          api_default_enabled: Boolean(remote.api_default_enabled),
          marketplace_prefer_cloud_routing: Boolean(remote.marketplace_prefer_cloud_routing),
        })
      } catch {
        // Keep local defaults when backend preferences are unavailable.
      } finally {
        if (!cancelled) {
          setPreferencesHydrated(true)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [setApiDefaultEnabled, updatePreferences])

  useEffect(() => {
    if (!preferencesHydrated) return
    const snapshot = JSON.stringify({
      api_default_enabled: Boolean(apiDefaultEnabled),
      marketplace_prefer_cloud_routing: Boolean(preferences.marketplacePreferCloudRouting),
    })
    if (snapshot === syncedPreferencesRef.current) return
    let cancelled = false
    ;(async () => {
      try {
        await patchCockpitPreferences({
          api_default_enabled: Boolean(apiDefaultEnabled),
          marketplace_prefer_cloud_routing: Boolean(preferences.marketplacePreferCloudRouting),
        })
        if (!cancelled) {
          syncedPreferencesRef.current = snapshot
        }
      } catch {
        // Keep local behavior even when backend preference sync fails.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [apiDefaultEnabled, preferences.marketplacePreferCloudRouting, preferencesHydrated])

  useEffect(() => {
    if (!preferencesHydrated) return
    let cancelled = false

    async function refreshRemotePreferences() {
      try {
        const remote = await getCockpitPreferences()
        if (cancelled) return
        const remoteSnapshot = JSON.stringify({
          api_default_enabled: Boolean(remote.api_default_enabled),
          marketplace_prefer_cloud_routing: Boolean(remote.marketplace_prefer_cloud_routing),
        })
        if (remoteSnapshot === syncedPreferencesRef.current) return

        // Update the sync marker first to prevent write-back loops.
        syncedPreferencesRef.current = remoteSnapshot
        setApiDefaultEnabled(Boolean(remote.api_default_enabled))
        updatePreferences({
          marketplacePreferCloudRouting: Boolean(remote.marketplace_prefer_cloud_routing),
        })
      } catch {
        // Keep local state when backend preference refresh fails.
      }
    }

    const interval = setInterval(() => void refreshRemotePreferences(), 10_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [preferencesHydrated, setApiDefaultEnabled, updatePreferences])

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
        "flex flex-col transition-all duration-300 overflow-hidden",
        isIPhoneScale ? "bg-muted/30 items-center justify-center" : ""
      )}>
        <div 
          className={cn(
            isIPhoneScale ? "flex items-center justify-center p-8 pointer-events-none" : "flex-1 flex flex-col min-h-0"
          )}
          style={isIPhoneScale ? { 
            transform: `scale(${scale})`,
            transformOrigin: 'center center',
          } : {}}
        >
          <div 
            ref={captureRootRef} 
            className={cn(
              "flex flex-col overflow-hidden transition-all duration-500 shadow-[0_0_50px_-12px_rgba(0,0,0,0.5)] bg-background",
              isIPhoneScale 
                ? "w-[414px] h-[896px] rounded-[3.5rem] border-[12px] border-muted-foreground/20 relative pointer-events-auto shrink-0" 
                : "w-full flex-1 min-h-0"
            )}
          >
            {isIPhoneScale && (
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-7 bg-muted-foreground/20 rounded-b-3xl z-50 flex items-center justify-center backdrop-blur-md">
                <div className="w-16 h-1.5 bg-background/40 rounded-full mx-auto" />
                <div className="absolute right-8 w-2 h-2 rounded-full bg-background/20" />
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
            <main className="flex-1 min-h-0 overflow-hidden relative">
              {children}
            </main>
            <CockpitStatusBar
              backendHealthy={backendHealthy}
              backendLastHealthyAt={backendLastHealthyAt}
              backendError={backendError}
              compact={isIPhoneScale}
            />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
