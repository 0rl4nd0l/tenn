'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { OpsJobRun, OpsSSEEvent } from '@/lib/ops-types'
import { listActiveOpsJobs } from '@/lib/ops-api-client'

interface UseJobStreamOptions {
  jobId?: string
  enabled?: boolean
}

interface UseJobStreamReturn {
  activeJobs: Map<string, OpsJobRun>
  recentEvents: OpsSSEEvent[]
  connected: boolean
  error: string | null
}

const MAX_RECENT_EVENTS = 100
const BASE_RECONNECT_MS = 1000
const MAX_RECONNECT_MS = 30000

export function useJobStream(options?: UseJobStreamOptions): UseJobStreamReturn {
  const { jobId, enabled = true } = options ?? {}
  const [activeJobs, setActiveJobs] = useState<Map<string, OpsJobRun>>(new Map())
  const [recentEvents, setRecentEvents] = useState<OpsSSEEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const reconnectDelay = useRef(BASE_RECONNECT_MS)
  const eventSourceRef = useRef<EventSource | null>(null)

  const fetchActiveJobs = useCallback(async () => {
    try {
      const resp = await listActiveOpsJobs()
      const map = new Map<string, OpsJobRun>()
      for (const job of resp.items) {
        map.set(job.job_id, job)
      }
      setActiveJobs(map)
    } catch {
      // Non-fatal — SSE will provide updates
    }
  }, [])

  useEffect(() => {
    if (!enabled) return

    let cancelled = false

    const connect = () => {
      if (cancelled) return

      const url = jobId
        ? `/api/ops/stream?job_id=${encodeURIComponent(jobId)}`
        : '/api/ops/stream'

      const source = new EventSource(url)
      eventSourceRef.current = source

      source.onopen = () => {
        setConnected(true)
        setError(null)
        reconnectDelay.current = BASE_RECONNECT_MS
        // Fetch current state on connect/reconnect
        fetchActiveJobs()
      }

      source.onmessage = (e) => {
        try {
          const event: OpsSSEEvent = JSON.parse(e.data)
          setRecentEvents((prev) => [...prev.slice(-(MAX_RECENT_EVENTS - 1)), event])

          // Update active jobs map based on event
          if (event.event_type === 'job.created' || event.event_type === 'job.started') {
            fetchActiveJobs()
          } else if (
            event.event_type === 'job.completed' ||
            event.event_type === 'job.failed' ||
            event.event_type === 'job.cancelled'
          ) {
            setActiveJobs((prev) => {
              const next = new Map(prev)
              next.delete(event.job_id)
              return next
            })
          }
        } catch {
          // Ignore unparseable messages (e.g. keepalive comments)
        }
      }

      source.onerror = () => {
        source.close()
        setConnected(false)
        if (!cancelled) {
          const delay = reconnectDelay.current
          reconnectDelay.current = Math.min(delay * 2, MAX_RECONNECT_MS)
          setError(`Disconnected. Reconnecting in ${Math.round(delay / 1000)}s...`)
          setTimeout(connect, delay)
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      eventSourceRef.current?.close()
      eventSourceRef.current = null
      setConnected(false)
    }
  }, [jobId, enabled, fetchActiveJobs])

  return { activeJobs, recentEvents, connected, error }
}
