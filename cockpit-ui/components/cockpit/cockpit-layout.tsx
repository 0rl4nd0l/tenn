'use client'

import { useState, useEffect } from 'react'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { CockpitSidebar } from './cockpit-sidebar'
import { CockpitStatusBar } from './cockpit-status-bar'
import { checkHealth } from '@/lib/api-client'
import { useCockpitStore } from '@/lib/cockpit-store'
import { Separator } from '@/components/ui/separator'

interface CockpitLayoutProps {
  children: React.ReactNode
  title: string
}

export function CockpitLayout({ children, title }: CockpitLayoutProps) {
  const [backendHealthy, setBackendHealthy] = useState(false)
  const { activeTicker, sessionStats } = useCockpitStore()

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const res = await checkHealth()
        if (!cancelled) setBackendHealthy(res.status === 'ok')
      } catch {
        if (!cancelled) setBackendHealthy(false)
      }
    }

    poll()
    const interval = setInterval(poll, 30_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return (
    <SidebarProvider>
      <CockpitSidebar 
        backendHealthy={backendHealthy} 
        sessionCost={sessionStats.totalCostUsd} 
      />
      <SidebarInset className="flex flex-col overflow-hidden">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-medium">{title}</h1>
            <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-mono text-primary">
              {activeTicker}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
        <CockpitStatusBar />
      </SidebarInset>
    </SidebarProvider>
  )
}
