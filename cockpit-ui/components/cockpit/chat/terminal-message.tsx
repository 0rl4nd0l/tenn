'use client'

import { useEffect, useState } from 'react'
import { ChevronRight, ChevronDown, Copy, Check, Maximize2, ExternalLink } from 'lucide-react'
import type { ChatMessage as ChatMessageType } from '@/lib/cockpit-types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface TerminalMessageProps {
  message: ChatMessageType
  isStreaming?: boolean
  showSources?: boolean
  onConfirmAction?: (actionPreview: ChatMessageType['actionPreview']) => void
  onCancelAction?: (actionPreview: ChatMessageType['actionPreview']) => void
}

export function TerminalMessage({
  message,
  isStreaming,
  showSources = true,
  onConfirmAction,
  onCancelAction
}: TerminalMessageProps) {
  const [sourcesExpanded, setSourcesExpanded] = useState(Boolean(showSources))
  const [thinkingExpanded, setThinkingExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [rawDumpExpanded, setRawDumpExpanded] = useState(false)
  const [chartDialogOpen, setChartDialogOpen] = useState(false)
  const [autoOpenedFilestatsChart, setAutoOpenedFilestatsChart] = useState(false)

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

  const formatSourceDate = (value: string | undefined): string | null => {
    if (!value) {
      return null
    }

    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
      return value.slice(0, 10) || value
    }

    return parsed.toISOString().slice(0, 10)
  }

  const isFilestatsDump = message.content.includes('Company Data Dump:')
  const hasFilestatsChart = Boolean(message.chart && /filestats/i.test(message.chart.title || ''))
  const shouldCollapseRawDump = isFilestatsDump && hasFilestatsChart
  const filestatsPreview = message.content.split('\n').slice(0, 10).join('\n')

  useEffect(() => {
    if (hasFilestatsChart && !autoOpenedFilestatsChart) {
      setChartDialogOpen(true)
      setAutoOpenedFilestatsChart(true)
    }
  }, [autoOpenedFilestatsChart, hasFilestatsChart])

  useEffect(() => {
    setSourcesExpanded(Boolean(showSources))
  }, [message.id, showSources])

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
      {/* Thinking trace */}
      {message.thinking && (message.thinking.assessment || message.thinking.plan) && (
        <div className="ml-4 mb-1">
          <button
            onClick={() => setThinkingExpanded(!thinkingExpanded)}
            className="flex items-center gap-1 text-sm text-purple-400/70 hover:text-purple-400 transition-colors"
          >
            {thinkingExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            [reasoning]
          </button>
          {thinkingExpanded && (
            <div className="mt-1 pl-4 text-sm text-purple-400/60 space-y-1 border-l border-purple-500/20">
              {message.thinking.assessment && (
                <div>
                  <span className="text-purple-400/80 font-semibold">Assessment: </span>
                  <span className="whitespace-pre-wrap">{message.thinking.assessment}</span>
                </div>
              )}
              {message.thinking.plan && (
                <div>
                  <span className="text-purple-400/80 font-semibold">Plan: </span>
                  <span className="whitespace-pre-wrap">{message.thinking.plan}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

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
        {shouldCollapseRawDump ? (
          <div className="flex-1 space-y-2">
            <div className="rounded-md border border-cyan-500/30 bg-cyan-500/8 p-3">
              <div className="text-sm uppercase tracking-[0.16em] text-cyan-300/90">Filestats Visual Mode</div>
              <div className="mt-1 text-sm text-cyan-100/90">
                Interactive dashboard rendered below. Raw dump is collapsed for readability.
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setChartDialogOpen(true)}
                  className="inline-flex items-center gap-1 rounded border border-cyan-400/50 bg-cyan-500/12 px-2 py-1 text-xs text-cyan-100 hover:bg-cyan-500/20 transition-colors"
                >
                  <Maximize2 className="h-3 w-3" />
                  Open dashboard fullscreen
                </button>
                <button
                  onClick={() => setRawDumpExpanded(!rawDumpExpanded)}
                  className="inline-flex items-center gap-1 rounded border border-cyan-500/40 px-2 py-1 text-xs text-cyan-200 hover:bg-cyan-500/12 transition-colors"
                >
                  {rawDumpExpanded ? 'Hide raw dump' : 'Show raw dump'}
                </button>
              </div>
            </div>
            {rawDumpExpanded && (
              <div className="rounded-md border border-blue-500/25 bg-black/25 p-2 text-white text-base whitespace-pre-wrap break-words leading-relaxed">
                {formatContent(message.content)}
              </div>
            )}
            {!rawDumpExpanded && (
              <div className="rounded-md border border-blue-500/20 bg-blue-500/5 p-2 text-sm text-blue-100/80 whitespace-pre-wrap break-words">
                {filestatsPreview}
              </div>
            )}
          </div>
        ) : (
          <div className="text-white text-lg whitespace-pre-wrap break-words leading-relaxed flex-1">
            {formatContent(message.content)}
            {isStreaming && <span className="terminal-cursor" />}
          </div>
        )}
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
          <div className="terminal-text-dim mt-1 text-[10px]">
            Click a button or type <code>yes</code>/<code>no</code>.
          </div>
          <div className="flex gap-2 mt-2">
            <button
              className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 border border-green-500/30 rounded hover:bg-green-500/30 transition-colors"
              onClick={() => onConfirmAction?.(message.actionPreview)}
            >
              Confirm
            </button>
            <button
              className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 border border-red-500/30 rounded hover:bg-red-500/30 transition-colors"
              onClick={() => onCancelAction?.(message.actionPreview)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {message.chart && (
        hasFilestatsChart ? (
          <div className="ml-4 mt-3 rounded border border-cyan-500/30 bg-cyan-500/6 p-3">
            <div className="text-xs uppercase tracking-[0.16em] text-cyan-300/90">Visual dashboard</div>
            <div className="mt-1 text-sm text-cyan-100/85">
              Filestats dashboard is opened in fullscreen mode for chart-like readability.
            </div>
            <button
              onClick={() => setChartDialogOpen(true)}
              className="mt-2 inline-flex items-center gap-1 rounded border border-cyan-400/50 bg-cyan-500/12 px-2 py-1 text-xs text-cyan-100 hover:bg-cyan-500/20 transition-colors"
            >
              <Maximize2 className="h-3 w-3" />
              Re-open fullscreen dashboard
            </button>
          </div>
        ) : (
          <div className="ml-4 mt-3 overflow-hidden rounded border border-cyan-500/30 bg-cyan-500/5">
            <div className="border-b border-cyan-500/20 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300/90">
              {message.chart.title}
            </div>
            <iframe
              title={message.chart.title}
              srcDoc={message.chart.html}
              sandbox="allow-scripts allow-same-origin"
              loading="lazy"
              className="h-[720px] w-full bg-black"
            />
          </div>
        )
      )}

      {message.chart && (
        <Dialog open={chartDialogOpen} onOpenChange={setChartDialogOpen}>
          <DialogContent className="h-[94vh] w-[97vw] max-w-[97vw] border-cyan-500/30 bg-zinc-950 p-0 text-zinc-100">
            <DialogHeader className="border-b border-cyan-500/20 px-4 py-3">
              <DialogTitle className="font-mono text-sm uppercase tracking-[0.14em] text-cyan-200">
                {message.chart.title}
              </DialogTitle>
              <DialogDescription className="text-xs text-cyan-100/70">
                Interactive dashboard view. Press Esc to close.
              </DialogDescription>
            </DialogHeader>
            <iframe
              title={`${message.chart.title}-fullscreen`}
              srcDoc={message.chart.html}
              sandbox="allow-scripts allow-same-origin"
              loading="lazy"
              className="h-[calc(94vh-74px)] w-full bg-black"
            />
          </DialogContent>
        </Dialog>
      )}

      {/* Sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="ml-4 mt-2">
          <button
            onClick={() => setSourcesExpanded(!sourcesExpanded)}
            className="flex items-center gap-1 text-sm text-blue-400/80 hover:text-blue-300 transition-colors"
          >
            {sourcesExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            [{message.sources.length} source{message.sources.length === 1 ? '' : 's'}]
          </button>
          {sourcesExpanded && (
            <div className="mt-2 space-y-2 rounded-md border border-blue-500/15 bg-blue-500/5 px-3 py-2 text-sm">
              {message.sources.map((source, i) => (
                <div
                  key={`${source.sourceId || source.documentId || source.url || source.title}-${i}`}
                  className="flex items-start gap-2"
                >
                  <span className="mt-0.5 text-blue-500">{`>`}</span>
                  <div className="min-w-0 flex-1">
                    {source.url ? (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex max-w-full items-center gap-1 break-all text-blue-300 underline decoration-blue-500/40 underline-offset-2 hover:text-blue-200"
                      >
                        <span>{source.title}</span>
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <div className="break-words text-blue-200">{source.title}</div>
                    )}
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-blue-200/60">
                      {source.kind && <span>{source.kind}</span>}
                      {source.docType && <span>{source.docType}</span>}
                      {formatSourceDate(source.publishedAt) && (
                        <span>{formatSourceDate(source.publishedAt)}</span>
                      )}
                      {source.documentId && (
                        <span className="font-mono">doc {source.documentId.slice(0, 12)}</span>
                      )}
                    </div>
                    {source.snippet && (
                      <p className="mt-1 whitespace-pre-wrap break-words text-blue-100/70">
                        {source.snippet}
                      </p>
                    )}
                    {!source.url && source.path && (
                      <p className="mt-1 break-all font-mono text-[11px] text-blue-100/45">
                        {source.path}
                      </p>
                    )}
                  </div>
                  <span className="shrink-0 text-blue-300/80">{formatSourceScore(source.score)}</span>
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
