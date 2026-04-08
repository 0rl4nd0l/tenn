'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { SLASH_COMMANDS } from '@/lib/cockpit-types'
import { cn } from '@/lib/utils'

interface TerminalInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  value?: string
  onValueChange?: (value: string) => void
  onClear?: () => void
}

export function TerminalInput({ onSend, disabled, value: controlledValue, onValueChange, onClear }: TerminalInputProps) {
  const [internalValue, setInternalValue] = useState('')
  const value = controlledValue ?? internalValue
  const setValue = onValueChange ?? setInternalValue

  const [showCommands, setShowCommands] = useState(false)
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0)
  const [inputHistory, setInputHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)

  const filteredCommands = value.startsWith('/')
    ? SLASH_COMMANDS.filter(cmd =>
        cmd.command.toLowerCase().includes(value.toLowerCase())
      )
    : []

  useEffect(() => {
    setShowCommands(value.startsWith('/') && filteredCommands.length > 0)
    setSelectedCommandIndex(0)
  }, [value, filteredCommands.length])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = useCallback(() => {
    if (!value.trim() || disabled) return
    
    onSend(value.trim())
    setInputHistory(prev => [value.trim(), ...prev].slice(0, 50))
    setValue('')
    setHistoryIndex(-1)
    setShowCommands(false)
  }, [value, disabled, onSend, setValue])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Command selection
    if (showCommands) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedCommandIndex(i => Math.min(i + 1, filteredCommands.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedCommandIndex(i => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Tab' || (e.key === 'Enter' && filteredCommands[selectedCommandIndex])) {
        e.preventDefault()
        const cmd = filteredCommands[selectedCommandIndex]
        if (cmd) {
          setValue(cmd.command + ' ')
          setShowCommands(false)
        }
        return
      }
      if (e.key === 'Escape') {
        setShowCommands(false)
        return
      }
    }

    // Send on Enter
    if (e.key === 'Enter' && !showCommands) {
      e.preventDefault()
      handleSend()
      return
    }

    // Input history navigation
    if (e.key === 'ArrowUp' && !showCommands && inputHistory.length > 0) {
      e.preventDefault()
      const newIndex = Math.min(historyIndex + 1, inputHistory.length - 1)
      setHistoryIndex(newIndex)
      setValue(inputHistory[newIndex])
      return
    }
    if (e.key === 'ArrowDown' && !showCommands) {
      e.preventDefault()
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1
        setHistoryIndex(newIndex)
        setValue(inputHistory[newIndex])
      } else {
        setHistoryIndex(-1)
        setValue('')
      }
    }

    // Ctrl+C to clear
    if (e.key === 'c' && e.ctrlKey) {
      e.preventDefault()
      setValue('')
      setHistoryIndex(-1)
    }

    // Ctrl+L to clear chat
    if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault()
      onClear?.()
    }
  }

  const selectCommand = (index: number) => {
      const cmd = filteredCommands[index]
      if (cmd) {
      setValue(cmd.command + ' ')
      setShowCommands(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="terminal-panel relative z-10 border-t border-border/60 supports-[backdrop-filter:blur(0)]:backdrop-blur-sm">
      {/* Command autocomplete */}
      {showCommands && (
        <div className="absolute bottom-full left-0 right-0 mb-0 max-h-48 overflow-y-auto border-x border-t border-blue-500/30 bg-black/90 supports-[backdrop-filter:blur(0)]:backdrop-blur-sm">
          {filteredCommands.slice(0, 8).map((cmd, i) => (
            <button
              key={cmd.command}
              className={cn(
                'flex w-full items-start gap-3 px-4 py-2 text-left text-sm font-mono transition-colors duration-150',
                i === selectedCommandIndex ? 'bg-blue-500/20' : 'hover:bg-black/50'
              )}
              onClick={() => selectCommand(i)}
              onMouseEnter={() => setSelectedCommandIndex(i)}
            >
              <span className="text-blue-400 shrink-0">/</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2">
                  <span className="text-white">{cmd.command.slice(1)}</span>
                  {cmd.args && (
                    <span className="text-blue-400/60">{cmd.args}</span>
                  )}
                </div>
                <p className="text-blue-400/60 truncate">{cmd.description}</p>
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-3">
        <span className="text-blue-400 font-mono shrink-0 text-lg">
          {disabled ? '...' : '>'}
        </span>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Processing...' : 'Enter command or query...'}
          disabled={disabled}
          className="flex-1 border-none bg-transparent font-mono text-lg text-white placeholder:text-blue-400/40 outline-none transition-colors duration-150 focus:placeholder:text-blue-400/60"
          autoComplete="off"
          spellCheck={false}
        />
        {!disabled && (
          <span className="text-xs text-blue-400/60 font-mono hidden sm:block">
            [Enter] send | [Up/Down] history | [Tab] complete
          </span>
        )}
      </div>
    </div>
  )
}
