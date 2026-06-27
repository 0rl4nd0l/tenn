'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

import { getExtractionReviewSnippetObjectUrl } from '@/lib/api-client'
import type {
  ExtractionEvidenceQuality,
  ExtractionReviewItem,
  ExtractionReviewSession,
} from '@/lib/cockpit-types'

import type { SnippetImageState } from './types'
import { evidenceQualityBody } from './utils'

type UseSnippetImageArgs = {
  currentEvidenceKey: string | null
  currentSnippetUrl: string | null
  evidenceSuspendMessage: string | null
  currentReviewItem: ExtractionReviewItem | null
  currentEvidenceQuality: ExtractionEvidenceQuality
  reviewSessionId: string | null
  getReviewSession: (sessionId: string) => Promise<ExtractionReviewSession>
  onSessionRefresh: (session: ExtractionReviewSession, itemId: string | null) => void
}

const IDLE_STATE: SnippetImageState = {
  key: null,
  status: 'idle',
  retryAttempted: false,
  message: null,
}

export function useSnippetImage({
  currentEvidenceKey,
  currentSnippetUrl,
  evidenceSuspendMessage,
  currentReviewItem,
  currentEvidenceQuality,
  reviewSessionId,
  getReviewSession,
  onSessionRefresh,
}: UseSnippetImageArgs) {
  const [snippetImageState, setSnippetImageState] = useState<SnippetImageState>(IDLE_STATE)
  const [snippetImageUrl, setSnippetImageUrl] = useState<string | null>(null)
  const [snippetFetchAttempt, setSnippetFetchAttempt] = useState(0)
  const latestEvidenceKeyRef = useRef<string | null>(null)
  const objectUrlRef = useRef<string | null>(null)

  const revokeSnippetImageUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
    setSnippetImageUrl(null)
  }, [])

  useEffect(() => {
    latestEvidenceKeyRef.current = currentEvidenceKey
  }, [currentEvidenceKey])

  useEffect(() => {
    if (evidenceSuspendMessage) {
      setSnippetImageState({
        key: currentEvidenceKey,
        status: 'idle',
        retryAttempted: false,
        message: evidenceSuspendMessage,
      })
      return
    }

    if (!currentEvidenceKey || !currentSnippetUrl) {
      setSnippetImageState({
        key: currentEvidenceKey,
        status: 'idle',
        retryAttempted: false,
        message: null,
      })
      return
    }

    setSnippetImageState({
      key: currentEvidenceKey,
      status: 'loading',
      retryAttempted: false,
      message: null,
    })
  }, [currentEvidenceKey, currentSnippetUrl, evidenceSuspendMessage])

  const handleSnippetImageLoad = useCallback(() => {
    if (!currentEvidenceKey) return
    setSnippetImageState((previous) => {
      if (previous.key !== currentEvidenceKey) return previous
      return { ...previous, status: 'ready', message: null }
    })
  }, [currentEvidenceKey])

  const handleSnippetImageError = useCallback(() => {
    if (!currentEvidenceKey) return

    const itemId = currentReviewItem?.item_id || null
    const fallbackMessage = currentReviewItem?.snippet.reason
      || (currentEvidenceQuality === 'approximate'
        ? 'Source page/table preview is unavailable for this session item. Exact line evidence was not preserved, so verify from provenance details only.'
        : evidenceQualityBody(currentEvidenceQuality))

    let shouldRetry = false
    setSnippetImageState((previous) => {
      if (previous.key !== currentEvidenceKey) return previous
      shouldRetry = !previous.retryAttempted && Boolean(reviewSessionId && itemId)
      if (!shouldRetry) {
        return { ...previous, status: 'failed', message: fallbackMessage }
      }
      return {
        ...previous,
        status: 'retrying',
        retryAttempted: true,
        message: 'Refreshing the current review session once to recover snippet evidence...',
      }
    })

    if (!shouldRetry || !reviewSessionId) return

    void getReviewSession(reviewSessionId)
      .then((session) => {
        if (latestEvidenceKeyRef.current !== currentEvidenceKey) return
        onSessionRefresh(session, itemId)
        setSnippetImageState((previous) => {
          if (previous.key !== currentEvidenceKey) return previous
          return { ...previous, status: 'loading', message: null }
        })
        setSnippetFetchAttempt((attempt) => attempt + 1)
      })
      .catch(() => {
        if (latestEvidenceKeyRef.current !== currentEvidenceKey) return
        setSnippetImageState((previous) => {
          if (previous.key !== currentEvidenceKey) return previous
          return { ...previous, status: 'failed', message: fallbackMessage }
        })
      })
  }, [
    currentEvidenceKey,
    currentEvidenceQuality,
    currentReviewItem,
    getReviewSession,
    onSessionRefresh,
    reviewSessionId,
  ])

  useEffect(() => {
    if (evidenceSuspendMessage || !currentEvidenceKey || !currentSnippetUrl) {
      revokeSnippetImageUrl()
      return
    }

    let cancelled = false
    revokeSnippetImageUrl()

    void getExtractionReviewSnippetObjectUrl(currentSnippetUrl)
      .then((objectUrl) => {
        if (cancelled || latestEvidenceKeyRef.current !== currentEvidenceKey) {
          URL.revokeObjectURL(objectUrl)
          return
        }
        objectUrlRef.current = objectUrl
        setSnippetImageUrl(objectUrl)
      })
      .catch(() => {
        if (cancelled || latestEvidenceKeyRef.current !== currentEvidenceKey) return
        handleSnippetImageError()
      })

    return () => {
      cancelled = true
    }
  }, [
    currentEvidenceKey,
    currentSnippetUrl,
    evidenceSuspendMessage,
    handleSnippetImageError,
    revokeSnippetImageUrl,
    snippetFetchAttempt,
  ])

  useEffect(() => () => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
    }
  }, [])

  const beginSessionSwap = useCallback((message: string) => {
    revokeSnippetImageUrl()
    setSnippetImageState({
      key: null,
      status: 'idle',
      retryAttempted: false,
      message,
    })
  }, [revokeSnippetImageUrl])

  return {
    snippetImageState,
    snippetImageUrl,
    setSnippetImageState,
    beginSessionSwap,
    handleSnippetImageLoad,
    handleSnippetImageError,
  }
}
