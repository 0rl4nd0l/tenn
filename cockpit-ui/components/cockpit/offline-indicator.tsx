'use client'

import { useCockpitStore } from '@/lib/cockpit-store'
import { AlertTriangle, WifiOff, RefreshCw } from 'lucide-react'
import { useState } from 'react'

export function OfflineIndicator() {
  const isHealthy = useCockpitStore((state) => state.isBackendHealthy)
  const error = useCockpitStore((state) => state.backendError)
  const setBackendStatus = useCockpitStore((state) => state.setBackendStatus)
  const [retrying, setRetrying] = useState(false)

  const handleRetry = async () => {
    setRetrying(true)
    try {
      // Simple fetch to root or health to trigger apiFetch logic
      await fetch('/api/cockpit/health')
    } catch (e) {
      // apiFetch will handle the store update
    } finally {
      setTimeout(() => setRetrying(false), 500)
    }
  }

  if (isHealthy) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-destructive backdrop-blur-md shadow-lg">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/20">
            <WifiOff className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold uppercase tracking-wider">Cockpit Offline</span>
            <span className="text-xs opacity-80 max-w-[200px] truncate">
              {error || 'Backend communication failed'}
            </span>
          </div>
          <button 
            onClick={handleRetry}
            disabled={retrying}
            className="ml-2 p-2 hover:bg-destructive/20 rounded-md transition-colors disabled:opacity-50"
            title="Retry Connection"
          >
            <RefreshCw className={`h-4 w-4 ${retrying ? 'animate-spin' : ''}`} />
          </button>
          <AlertTriangle className="h-4 w-4 opacity-50 ml-1" />
        </div>
      </div>
    </div>
  )
}
