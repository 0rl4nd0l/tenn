import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CockpitPreferences } from './cockpit-types'

// Generate unique IDs
export function generateId(): string {
  return Math.random().toString(36).substring(2, 9)
}

// Available chat models served by llama-server in router mode on port 8001
export const AVAILABLE_CHAT_MODELS = [
  {
    id: 'model:gpt-oss-20b',
    label: 'GPT-OSS 20B',
    description: 'Dense 20B — loaded from local SSD cache',
  },
] as const

interface CockpitState {
  activeTicker: string
  sessionId: string
  chatModel: string
  preferences: CockpitPreferences
  sessionStats: {
    totalCostUsd: number
    lastLatencyMs: number
    activeModel: string
  }

  // Actions
  setActiveTicker: (ticker: string) => void
  setSessionId: (id: string) => void
  setChatModel: (model: string) => void
  updatePreferences: (prefs: Partial<CockpitPreferences>) => void
  addCost: (cost: number) => void
  setLatency: (latency: number) => void
  setActiveModel: (model: string) => void
}

export const useCockpitStore = create<CockpitState>()(
  persist(
    (set) => ({
      activeTicker: 'BHP',
      sessionId: generateId(),
      chatModel: 'model:gpt-oss-20b',
      preferences: {
        webSearchEnabled: true,
        ragEnabled: true,
        dbDiagnosticsEnabled: false,
        showSources: true,
        theme: 'dark'
      },
      sessionStats: {
        totalCostUsd: 0,
        lastLatencyMs: 0,
        activeModel: 'local'
      },
      
      setActiveTicker: (ticker) => set({ activeTicker: ticker }),
      setSessionId: (id) => set({ sessionId: id }),
      setChatModel: (model) => set({ chatModel: model }),
      updatePreferences: (prefs) => set((state) => ({ 
        preferences: { ...state.preferences, ...prefs } 
      })),
      addCost: (cost) => set((state) => ({ 
        sessionStats: { ...state.sessionStats, totalCostUsd: state.sessionStats.totalCostUsd + cost } 
      })),
      setLatency: (latency) => set((state) => ({ 
        sessionStats: { ...state.sessionStats, lastLatencyMs: latency } 
      })),
      setActiveModel: (model) => set((state) => ({ 
        sessionStats: { ...state.sessionStats, activeModel: model } 
      })),
    }),
    {
      name: 'cockpit-storage',
      partialize: (state) => ({
        activeTicker: state.activeTicker,
        preferences: state.preferences,
        sessionId: state.sessionId,
        chatModel: state.chatModel,
      }),
    }
  )
)
