'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { TerminalMessage } from './terminal-message'
import { TerminalInput } from './terminal-input'
import { useCockpitStore, generateId } from '@/lib/cockpit-store'
import { streamChat, sendChatMessage } from '@/lib/api-client'
import type { ChatMessage as ChatMessageType } from '@/lib/cockpit-types'
import { toast } from 'sonner'

export function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingMetadata, setStreamingMetadata] = useState<Partial<ChatMessageType>>({})
  
  const { activeTicker, sessionId, addCost, setLatency, setActiveModel } = useCockpitStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent, scrollToBottom])

  const handleSend = async (content: string) => {
    const userMessage: ChatMessageType = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    setIsStreaming(true)
    setStreamingContent('')
    setStreamingMetadata({})

    // Slash command handling
    if (content.startsWith('/')) {
      try {
        const response = await sendChatMessage({
          message: content,
          mode: 'analysis',
          ticker: activeTicker,
          sessionId: sessionId
        })
        
        const systemMessage: ChatMessageType = {
          id: generateId(),
          role: 'assistant',
          content: response.content.answer,
          timestamp: new Date(),
          metadata: {
            model: response.content.model,
            latencyMs: response.content.latency_ms,
            costUsd: 0,
            source: 'local'
          }
        }
        setMessages(prev => [...prev, systemMessage])
      } catch (err) {
        toast.error('Command failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
      } finally {
        setIsStreaming(false)
      }
      return
    }

    // Normal chat with streaming
    let currentContent = ''
    let currentMetadata: Partial<ChatMessageType> = {
      toolTraces: [],
      sources: []
    }

    streamChat({
      message: content,
      mode: 'analysis',
      ticker: activeTicker,
      sessionId: sessionId,
      onMessage: (event) => {
        switch (event.type) {
          case 'chunk':
            currentContent += event.data.text
            setStreamingContent(currentContent)
            break
          case 'tool_trace':
            currentMetadata.toolTraces = [...(currentMetadata.toolTraces || []), {
              tool: event.data.tool,
              durationMs: event.data.duration_ms,
              status: 'success'
            }]
            setStreamingMetadata({ ...currentMetadata })
            break
          case 'sources':
            currentMetadata.sources = event.data.items.map((s: any) => ({
              title: s.title,
              score: s.score
            }))
            setStreamingMetadata({ ...currentMetadata })
            break
          case 'action_preview':
            currentMetadata.actionPreview = {
              id: event.data.id,
              name: event.data.name,
              description: event.data.description,
              args: event.data.args,
              requiresConfirmation: true
            }
            setStreamingMetadata({ ...currentMetadata })
            break
          case 'done':
            const assistantMessage: ChatMessageType = {
              id: generateId(),
              role: 'assistant',
              content: currentContent,
              timestamp: new Date(),
              metadata: {
                model: event.data.model,
                latencyMs: event.data.latency_ms,
                costUsd: event.data.cost_usd || 0,
                source: event.data.source || 'local'
              },
              sources: currentMetadata.sources,
              toolTraces: currentMetadata.toolTraces,
              actionPreview: currentMetadata.actionPreview
            }
            
            // Update global stats
            if (event.data.cost_usd) addCost(event.data.cost_usd)
            if (event.data.latency_ms) setLatency(event.data.latency_ms)
            if (event.data.model) setActiveModel(event.data.model)
            
            setMessages(prev => [...prev, assistantMessage])
            setStreamingContent('')
            setStreamingMetadata({})
            setIsStreaming(false)
            break
        }
      },
      onError: (err) => {
        toast.error('Streaming error: ' + (err?.data || 'Connection lost'))
        setIsStreaming(false)
      },
      onEnd: () => {
        setIsStreaming(false)
      }
    })
  }

  return (
    <div className="flex h-full flex-col terminal-container overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border/30 bg-black/20 relative z-10">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/80" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
          <div className="w-3 h-3 rounded-full bg-green-500/80" />
        </div>
        <span className="font-mono text-xs terminal-text-dim ml-2">
          cockpit@financial-ai ~ /chat ({activeTicker})
        </span>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4 pb-4">
          {messages.map((msg) => (
            <TerminalMessage key={msg.id} message={msg} />
          ))}
          {isStreaming && streamingContent && (
            <TerminalMessage 
              message={{
                id: 'streaming',
                role: 'assistant',
                content: streamingContent,
                timestamp: new Date(),
                ...streamingMetadata
              }} 
              isStreaming={true}
            />
          )}
          {isStreaming && !streamingContent && (
            <div className="flex items-center gap-2 text-blue-400/60 font-mono text-sm">
              <span className="terminal-cursor" />
              <span>Analyzing market data...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      <TerminalInput onSend={handleSend} disabled={isStreaming} />
    </div>
  )
}
