'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface LogEntry {
  id: string
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  source: string
  metadata?: Record<string, any>
}

interface LogBufferState {
  logs: LogEntry[]
  maxLogs: number
  
  // Actions
  addLog: (message: string, source: string, level?: LogEntry['level'], metadata?: Record<string, any>) => void
  clearLogs: () => void
  getLogsBySource: (source: string) => LogEntry[]
}

export const useLogBufferStore = create<LogBufferState>()(
  persist(
    (set, get) => ({
      logs: [],
      maxLogs: 1000,
      
      addLog: (message, source, level = 'info', metadata) => {
        const newLog: LogEntry = {
          id: Math.random().toString(36).substring(2, 11),
          timestamp: new Date().toISOString(),
          level,
          message,
          source,
          metadata
        }
        
        set((state) => {
          const updatedLogs = [newLog, ...state.logs].slice(0, state.maxLogs)
          return { logs: updatedLogs }
        })
      },
      
      clearLogs: () => set({ logs: [] }),
      
      getLogsBySource: (source) => {
        return get().logs.filter(log => log.source === source)
      }
    }),
    {
      name: 'cockpit-log-buffer',
      storage: createJSONStorage(() => localStorage)
    }
  )
)
