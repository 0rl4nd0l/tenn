'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, Copy, Check } from 'lucide-react'
import type { ChatMessage as ChatMessageType } from '@/lib/cockpit-types'

interface TerminalMessageProps {
  message: ChatMessageType
  isStreaming?: boolean
  onConfirmAction?: (actionPreview: ChatMessageType['actionPreview']) => void
  onCancelAction?: (actionPreview: ChatMessageType['actionPreview']) => void
}

export function TerminalMessage({ message, isStreaming, onConfirmAction, onCancelAction }: TerminalMessageProps) {
  const [sourcesExpanded, setSourcesExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  const timestamp = message.timestamp.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatSourceScore = (score: number | undefined): string => {
    const numericScore = Number(score)
    if (!Number.isFinite(numericScore)) {
      return '[--]'
    }
    const pct = Math.max(0, Math.min(100, numericScore * 100))
    return `[${pct.toFixed(0)}%]`
  }

  // Parse content for code blocks and format
  const formatContent = (content: string) => {
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    const matches = Array.from(content.matchAll(codeBlockRegex))

    for (const match of matches) {
      const matchIndex = match.index ?? 0
      // Add text before code block
      if (matchIndex > lastIndex) {
        parts.push(
          <span key={`text-${lastIndex}`}>
            {formatInlineContent(content.slice(lastIndex, matchIndex))}
          </span>
        )
      }
      
      // Add code block
      const lang = match[1] || 'text'
      const code = match[2]
      parts.push(
        <div key={`code-${matchIndex}`} className="my-2 rounded border border-blue-500/30 bg-black/40 overflow-hidden">
          <div className="flex items-center justify-between px-2 py-1 border-b border-blue-500/30 text-[10px] text-blue-400/60">
            <span>{lang}</span>
          </div>
          <pre className="p-2 overflow-x-auto text-base">
            <code className="text-white">{code}</code>
          </pre>
        </div>
      )
      
      lastIndex = matchIndex + match[0].length
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {formatInlineContent(content.slice(lastIndex))}
        </span>
      )
    }

    return parts.length > 0 ? parts : formatInlineContent(content)
  }

  const formatInlineContent = (text: string) => {
    // Handle inline code
    return text.split(/(`[^`]+`)/).map((part, i) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-white text-base">
            {part.slice(1, -1)}
          </code>
        )
      }
      // Handle bold
      return part.split(/(\*\*[^*]+\*\*)/).map((subpart, j) => {
        if (subpart.startsWith('**') && subpart.endsWith('**')) {
          return <strong key={`${i}-${j}`} className="text-white font-semibold">{subpart.slice(2, -2)}</strong>
        }
        return subpart
      })
    })
  }

  if (isUser) {
    return (
      <div className="group rounded-md border border-transparent px-2 py-1 transition-colors duration-150 hover:border-border/40 hover:bg-white/[0.02]">
        <div className="flex items-start gap-2">
          <span className="text-blue-400 shrink-0">{`>`}</span>
          <span className="text-white text-lg whitespace-pre-wrap break-words">{message.content}</span>
        </div>
        <div className="text-[10px] text-blue-400/60 ml-4 opacity-0 group-hover:opacity-100 transition-opacity">
          [{timestamp}]
        </div>
      </div>
    )
  }

  if (isSystem) {
    return (
      <div className="rounded-md border border-[oklch(0.78_0.17_80/0.35)] bg-[oklch(0.78_0.17_80/0.08)] px-2 py-1 text-amber-300 text-xs transition-colors duration-150 hover:bg-[oklch(0.78_0.17_80/0.12)]">
        <span className="text-amber-500">[SYSTEM]</span> {message.content}
      </div>
    )
  }

  // Assistant message
  return (
    <div className="group mt-2 mb-3 rounded-md border border-transparent px-2 py-1 transition-colors duration-150 hover:border-border/40 hover:bg-white/[0.02]">
      {/* Tool traces */}
      {message.toolTraces && message.toolTraces.length > 0 && (
        <div className="text-sm text-blue-400/70 mb-1">
          {message.toolTraces.map((trace, i) => (
            <span key={i} className="mr-3">
              [{trace.tool}: {trace.durationMs}ms]
            </span>
          ))}
        </div>
      )}

      {/* Main content */}
      <div className="flex items-start gap-2">
        <span className="text-blue-400 shrink-0">{`$`}</span>
        <div className="text-white text-lg whitespace-pre-wrap break-words leading-relaxed flex-1">
          {formatContent(message.content)}
          {isStreaming && <span className="terminal-cursor" />}
        </div>
      </div>

      {/* Action Preview */}
      {message.actionPreview && (
        <div className="ml-4 mt-2 p-2 border border-amber-500/30 rounded bg-amber-500/5">
          <div className="text-amber-400 text-xs font-bold mb-1">
            ACTION: {message.actionPreview.name}
          </div>
          <div className="terminal-text-dim text-xs mb-1">
            {message.actionPreview.description}
          </div>
          <div className="terminal-text text-[10px]">
            args: {JSON.stringify(message.actionPreview.args)}
          </div>
          <div className="flex gap-2 mt-2">
            <button
              className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 border border-green-500/30 rounded hover:bg-green-500/30 transition-colors"
              onClick={() => onConfirmAction?.(message.actionPreview)}
            >
              [Y] Confirm
            </button>
            <button
              className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 border border-red-500/30 rounded hover:bg-red-500/30 transition-colors"
              onClick={() => onCancelAction?.(message.actionPreview)}
            >
              [N] Cancel
            </button>
          </div>
        </div>
      )}

      {/* Sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="ml-4 mt-2">
          <button 
            onClick={() => setSourcesExpanded(!sourcesExpanded)}
            className="flex items-center gap-1 text-sm text-blue-400/70 hover:text-blue-400 transition-colors"
          >
            {sourcesExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            [{message.sources.length} sources]
          </button>
          {sourcesExpanded && (
            <div className="mt-1 pl-4 text-sm text-blue-400/60 space-y-0.5">
              {message.sources.map((source, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-blue-500">{`>`}</span>
                  <span className="truncate">{source.title}</span>
                  <span className="text-blue-300">{formatSourceScore(source.score)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Metadata footer */}
      <div className="flex items-center gap-4 ml-4 mt-1 text-sm text-blue-400/60 opacity-0 group-hover:opacity-100 transition-opacity">
        <span>[{timestamp}]</span>
        {message.metadata && (
          <>
            <span>{message.metadata.model}</span>
            {message.metadata.latencyMs && <span>{message.metadata.latencyMs}ms</span>}
            {message.metadata.costUsd !== undefined && <span>${message.metadata.costUsd.toFixed(4)}</span>}
          </>
        )}
        <button 
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-blue-400 transition-colors"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'copied' : 'copy'}
        </button>
      </div>
    </div>
  )
}
