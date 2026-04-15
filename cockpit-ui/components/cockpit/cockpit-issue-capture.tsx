'use client'

import { useCallback, useMemo, useState } from 'react'
import type { RefObject } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import html2canvas from 'html2canvas'
import { Camera, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { useCockpitStore } from '@/lib/cockpit-store'
import type { ServiceHealth } from '@/lib/cockpit-types'

type FeedbackCaptureResponse = {
  report_id: string
  feedback_type: 'good' | 'poor'
  capture_kind: 'chat_feedback' | 'ui_issue'
  report_dir: string
  codex_prompt?: string | null
  analysis_summary?: string | null
}

type ScreenshotCapture = {
  dataUrl: string
  width: number
  height: number
  capturedAt: string
}

type CockpitIssueCaptureProps = {
  captureRootRef: RefObject<HTMLDivElement | null>
  pageTitle: string
  backendHealthy: boolean
  backendLastHealthyAt: Date | null
  backendError: string | null
  gpuHealth: ServiceHealth | null
}

async function copyPrompt(prompt: string): Promise<boolean> {
  const text = prompt.trim()
  if (!text) {
    return false
  }
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function CockpitIssueCapture({
  captureRootRef,
  pageTitle,
  backendHealthy,
  backendLastHealthyAt,
  backendError,
  gpuHealth,
}: CockpitIssueCaptureProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [open, setOpen] = useState(false)
  const [description, setDescription] = useState('')
  const [captureError, setCaptureError] = useState<string | null>(null)
  const [captureState, setCaptureState] = useState<'idle' | 'capturing' | 'ready'>('idle')
  const [saveState, setSaveState] = useState<'idle' | 'saving'>('idle')
  const [screenshot, setScreenshot] = useState<ScreenshotCapture | null>(null)
  const {
    activeTicker,
    sessionId,
    chatModel,
    chatCompletionActive,
    activeSource,
    preferences,
    sessionStats,
    apiDefaultEnabled,
  } = useCockpitStore()

  const search = useMemo(() => {
    const query = searchParams.toString()
    return query ? `?${query}` : ''
  }, [searchParams])

  const captureScreenshot = useCallback(async () => {
    const target = captureRootRef.current
    if (!target) {
      throw new Error('Cockpit capture root is unavailable')
    }

    const canvas = await html2canvas(target, {
      backgroundColor: '#09090b',
      logging: false,
      scale: Math.min(window.devicePixelRatio || 1, 2),
      useCORS: true,
      ignoreElements: (element) => element instanceof HTMLElement
        && element.dataset.cockpitIssueDialog === 'true',
    })

    return {
      dataUrl: canvas.toDataURL('image/png'),
      width: canvas.width,
      height: canvas.height,
      capturedAt: new Date().toISOString(),
    } satisfies ScreenshotCapture
  }, [captureRootRef])

  const handleOpen = useCallback(async () => {
    setOpen(true)
    setCaptureState('capturing')
    setCaptureError(null)
    try {
      const nextScreenshot = await captureScreenshot()
      setScreenshot(nextScreenshot)
      setCaptureState('ready')
    } catch (error) {
      setScreenshot(null)
      setCaptureState('idle')
      const message = error instanceof Error ? error.message : 'Screenshot capture failed'
      setCaptureError(message)
      toast.error(`Failed to capture screenshot: ${message}`)
    }
  }, [captureScreenshot])

  const handleRetake = useCallback(async () => {
    setCaptureState('capturing')
    setCaptureError(null)
    try {
      const nextScreenshot = await captureScreenshot()
      setScreenshot(nextScreenshot)
      setCaptureState('ready')
    } catch (error) {
      setScreenshot(null)
      setCaptureState('idle')
      const message = error instanceof Error ? error.message : 'Screenshot capture failed'
      setCaptureError(message)
      toast.error(`Failed to recapture screenshot: ${message}`)
    }
  }, [captureScreenshot])

  const resetDialog = useCallback((options?: { force?: boolean }) => {
    if (saveState === 'saving' && !options?.force) {
      return
    }
    setOpen(false)
    setDescription('')
    setCaptureError(null)
    setCaptureState('idle')
    setScreenshot(null)
  }, [saveState])

  const handleSubmit = useCallback(async () => {
    if (!screenshot) {
      toast.error('Capture a screenshot before saving the issue')
      return
    }

    setSaveState('saving')
    const descriptionText = description.trim()
    const issueText = descriptionText || `UI issue on ${pageTitle}`
    try {
      const response = await fetch('/api/cockpit/feedback/flag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          ticker: activeTicker || undefined,
          feedback_type: 'poor',
          capture_kind: 'ui_issue',
          note: descriptionText || undefined,
          flagged_message: {
            id: `ui-issue-${Date.now()}`,
            role: 'system',
            content: issueText,
          },
          transcript: [],
          frontend_context: {
            source: 'cockpit-ui-issue-capture',
            page_title: pageTitle,
            pathname,
            search,
            href: typeof window !== 'undefined' ? window.location.href : `${pathname}${search}`,
            activeTicker,
            sessionId,
            chatModel,
            activeSource,
            apiDefaultEnabled,
            chatCompletionActive,
            preferences,
            sessionStats,
            backendHealthy,
            backendLastHealthyAt: backendLastHealthyAt?.toISOString() ?? null,
            backendError,
            gpuHealth,
            viewport: {
              width: window.innerWidth,
              height: window.innerHeight,
              devicePixelRatio: window.devicePixelRatio || 1,
            },
            browser: {
              userAgent: navigator.userAgent,
              language: navigator.language,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            },
            clientTimestamp: new Date().toISOString(),
          },
          screenshot: {
            data_url: screenshot.dataUrl,
            mime_type: 'image/png',
            filename: 'ui-screenshot.png',
            width: screenshot.width,
            height: screenshot.height,
            captured_at: screenshot.capturedAt,
          },
        }),
      })

      const payload = (await response.json().catch(() => null)) as FeedbackCaptureResponse | { detail?: string } | null
      if (!response.ok) {
        const detail = payload && typeof payload === 'object' && 'detail' in payload
          ? String(payload.detail || '')
          : ''
        throw new Error(detail || `HTTP ${response.status}`)
      }

      const result = payload as FeedbackCaptureResponse
      const copied = result.codex_prompt?.trim()
        ? await copyPrompt(result.codex_prompt)
        : false
      toast.success(
        result.analysis_summary?.trim()
          ? copied
            ? `Issue saved and Codex prompt copied: ${result.analysis_summary}`
            : `Issue saved: ${result.analysis_summary}`
          : copied
            ? `Issue saved and Codex prompt copied: ${result.report_dir}`
            : `Issue saved to ${result.report_dir}`,
      )
      resetDialog({ force: true })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      toast.error(`Failed to save issue report: ${message}`)
    } finally {
      setSaveState('idle')
    }
  }, [
    activeSource,
    activeTicker,
    apiDefaultEnabled,
    backendError,
    backendHealthy,
    backendLastHealthyAt,
    chatCompletionActive,
    chatModel,
    description,
    gpuHealth,
    pageTitle,
    pathname,
    preferences,
    resetDialog,
    screenshot,
    search,
    sessionId,
    sessionStats,
  ])

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => void handleOpen()}
        disabled={captureState === 'capturing' || saveState === 'saving'}
        className="h-8 gap-2 border-red-500/30 bg-red-500/10 font-mono text-[11px] text-red-100 hover:bg-red-500/20"
      >
        <Camera className="h-3.5 w-3.5" />
        {captureState === 'capturing' ? 'Capturing...' : 'Capture issue'}
      </Button>

      <Dialog open={open} onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          resetDialog()
        }
      }}>
        <DialogContent
          data-cockpit-issue-dialog="true"
          className="border-red-500/30 bg-zinc-950 text-zinc-100 sm:max-w-3xl"
        >
          <DialogHeader>
            <DialogTitle className="font-mono text-sm text-red-300">
              Capture cockpit issue
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Save a screenshot plus runtime context into the shared cockpit flagged-session artifacts.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 lg:grid-cols-[1.35fr_0.95fr]">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="font-mono text-xs text-zinc-400">
                  Screenshot
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void handleRetake()}
                  disabled={captureState === 'capturing' || saveState === 'saving'}
                  className="h-7 gap-1 font-mono text-[11px]"
                >
                  <RotateCcw className="h-3 w-3" />
                  Retake
                </Button>
              </div>
              <div className="overflow-hidden rounded-lg border border-zinc-800 bg-black/40">
                {captureState === 'capturing' ? (
                  <div className="flex min-h-[260px] items-center justify-center font-mono text-xs text-zinc-400">
                    Capturing current cockpit view...
                  </div>
                ) : screenshot ? (
                  <Image
                    src={screenshot.dataUrl}
                    alt="Captured cockpit screenshot"
                    width={screenshot.width}
                    height={screenshot.height}
                    unoptimized
                    className="block max-h-[420px] w-full object-contain"
                  />
                ) : (
                  <div className="flex min-h-[260px] items-center justify-center px-4 text-center font-mono text-xs text-zinc-500">
                    {captureError || 'No screenshot captured yet.'}
                  </div>
                )}
              </div>
            </div>
            <div className="space-y-3">
              <div className="font-mono text-xs text-zinc-400">
                Issue description
              </div>
              <Textarea
                value={description}
                onChange={(event) => setDescription(event.target.value.slice(0, 1200))}
                placeholder="Describe the issue, odd behavior, or refinement you want captured."
                maxLength={1200}
                rows={10}
                disabled={saveState === 'saving'}
                className="border-red-500/20 bg-black/30 font-mono text-sm text-zinc-100 placeholder:text-zinc-500"
              />
              <div className="space-y-1 rounded-lg border border-zinc-800 bg-black/20 p-3 font-mono text-[11px] text-zinc-400">
                <div>page: {pageTitle}</div>
                <div>route: {pathname}{search}</div>
                <div>ticker: {activeTicker || 'none'}</div>
                <div>session: {sessionId}</div>
                <div>model: {chatModel || 'unknown'}</div>
              </div>
              <div className="text-right font-mono text-[11px] text-zinc-500">
                {description.length}/1200
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => resetDialog()}
              disabled={saveState === 'saving'}
              className="font-mono text-xs"
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={saveState === 'saving' || captureState === 'capturing' || !screenshot}
              className="border border-red-500/30 bg-red-500/10 font-mono text-xs text-red-100 hover:bg-red-500/20"
            >
              {saveState === 'saving' ? 'Saving issue...' : 'Save issue report'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
