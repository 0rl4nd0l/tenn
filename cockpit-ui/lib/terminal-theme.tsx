'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

export interface TerminalTheme {
  id: string
  name: string
  heading: string      // Main text color (Tailwind class)
  subheading: string   // Secondary text color (Tailwind class)
  prompt: string       // Prompt character color
  cursor: string       // Cursor color
}

export const TERMINAL_THEMES: TerminalTheme[] = [
  {
    id: 'classic-green',
    name: 'Classic Green',
    heading: 'text-green-400',
    subheading: 'text-green-600',
    prompt: 'text-green-500',
    cursor: 'bg-green-400',
  },
  {
    id: 'matrix',
    name: 'Matrix',
    heading: 'text-emerald-300',
    subheading: 'text-emerald-600',
    prompt: 'text-emerald-400',
    cursor: 'bg-emerald-300',
  },
  {
    id: 'cyan-ice',
    name: 'Cyan Ice',
    heading: 'text-cyan-300',
    subheading: 'text-cyan-600',
    prompt: 'text-cyan-400',
    cursor: 'bg-cyan-300',
  },
  {
    id: 'ocean-blue',
    name: 'Ocean Blue',
    heading: 'text-blue-300',
    subheading: 'text-blue-500',
    prompt: 'text-blue-400',
    cursor: 'bg-blue-300',
  },
  {
    id: 'arctic',
    name: 'Arctic',
    heading: 'text-sky-200',
    subheading: 'text-sky-500',
    prompt: 'text-sky-400',
    cursor: 'bg-sky-200',
  },
  {
    id: 'teal-mint',
    name: 'Teal Mint',
    heading: 'text-teal-300',
    subheading: 'text-teal-600',
    prompt: 'text-teal-400',
    cursor: 'bg-teal-300',
  },
  {
    id: 'white-blue',
    name: 'White / Blue',
    heading: 'text-white',
    subheading: 'text-blue-400',
    prompt: 'text-blue-400',
    cursor: 'bg-white',
  },
  {
    id: 'white-green',
    name: 'White / Green',
    heading: 'text-white',
    subheading: 'text-green-500',
    prompt: 'text-green-500',
    cursor: 'bg-white',
  },
]

interface TerminalThemeContextType {
  theme: TerminalTheme
  setTheme: (theme: TerminalTheme) => void
}

const TerminalThemeContext = createContext<TerminalThemeContextType | undefined>(undefined)

export function TerminalThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<TerminalTheme>(TERMINAL_THEMES[6]) // Default to white/blue

  return (
    <TerminalThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </TerminalThemeContext.Provider>
  )
}

export function useTerminalTheme() {
  const context = useContext(TerminalThemeContext)
  if (!context) {
    throw new Error('useTerminalTheme must be used within a TerminalThemeProvider')
  }
  return context
}
