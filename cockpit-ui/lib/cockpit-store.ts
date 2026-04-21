import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CockpitPreferences } from './cockpit-types'

const DEFAULT_CHAT_MODEL = 'model:qwen3.5-35b-a3b-apex'
const LEGACY_DEFAULT_CHAT_MODEL = 'model:qwen3.5-35b-a3b'
const DEFAULT_PREFERENCES: CockpitPreferences = {
  webSearchEnabled: true,
  ragEnabled: true,
  dbDiagnosticsEnabled: false,
  showSources: true,
  theme: 'dark',
  marketplaceHomeLocation: '',
  marketplacePreferCloudRouting: false,
  iphoneScale: false,
}

// Generate unique IDs
export function generateId(): string {
  return Math.random().toString(36).substring(2, 9)
}


interface CockpitState {
  activeTicker: string
  sessionId: string
  chatModel: string
  chatCompletionActive: boolean
  apiDefaultEnabled: boolean
  activeSource: 'local' | 'anthropic' | 'unknown'
  preferences: CockpitPreferences
  sessionStats: {
    totalCostUsd: number
    lastLatencyMs: number
    activeModel: string
  }
  isBackendHealthy: boolean
  backendError: string | null

  // Actions
  setActiveTicker: (ticker: string) => void
  setSessionId: (id: string) => void
  setChatModel: (model: string) => void
  setChatCompletionActive: (active: boolean) => void
  setApiDefaultEnabled: (enabled: boolean) => void
  setActiveSource: (source: 'local' | 'anthropic' | 'unknown') => void
  updatePreferences: (prefs: Partial<CockpitPreferences>) => void
  addCost: (cost: number) => void
  setLatency: (latency: number) => void
  setActiveModel: (model: string) => void
  setBackendStatus: (healthy: boolean, error?: string | null) => void
}

export const useCockpitStore = create<CockpitState>()(
  persist(
    (set) => ({
      activeTicker: '',
      sessionId: generateId(),
      chatModel: DEFAULT_CHAT_MODEL,
      chatCompletionActive: false,
      apiDefaultEnabled: false,
      activeSource: 'unknown',
      preferences: DEFAULT_PREFERENCES,
      sessionStats: {
        totalCostUsd: 0,
        lastLatencyMs: 0,
        activeModel: 'local'
      },
      isBackendHealthy: true,
      backendError: null,
      
      setActiveTicker: (ticker) => set({ activeTicker: ticker }),
      setSessionId: (id) => set({ sessionId: id }),
      setChatModel: (model) => set({ chatModel: model }),
      setChatCompletionActive: (active) => set({ chatCompletionActive: active }),
      setApiDefaultEnabled: (enabled) => set({ apiDefaultEnabled: enabled }),
      setActiveSource: (source) => set({ activeSource: source }),
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
      setBackendStatus: (healthy, error = null) => set({ isBackendHealthy: healthy, backendError: error }),
    }),
    {
      name: 'cockpit-storage',
      version: 3,
      migrate: (persistedState) => {
        const state = persistedState as Partial<CockpitState> | undefined
        if (!state) {
          return persistedState as unknown as CockpitState
        }

        const nextState = {
          ...state,
          chatModel:
            state.chatModel === LEGACY_DEFAULT_CHAT_MODEL
              ? DEFAULT_CHAT_MODEL
              : state.chatModel,
          preferences: {
            ...DEFAULT_PREFERENCES,
            ...(state.preferences ?? {}),
          },
        } as CockpitState

        return nextState
      },
      partialize: (state) => ({
        activeTicker: state.activeTicker,
        apiDefaultEnabled: state.apiDefaultEnabled,
        preferences: state.preferences,
        sessionId: state.sessionId,
        chatModel: state.chatModel,
      }),
    }
  )
)
