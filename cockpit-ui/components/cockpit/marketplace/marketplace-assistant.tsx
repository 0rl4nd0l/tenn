'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, MapPin, MessageSquareText, Play, Sparkles, X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { useCockpitStore } from '@/lib/cockpit-store'
import {
  buildMarketplaceAssistantGreeting,
  createMarketplaceMissionDraft,
  createTranscriptMessage,
  evaluateMarketplaceMissionDraft,
  getMarketplaceAssistantSessionId,
  mapMarketplaceDraftToMissionPayload,
  mergeMarketplaceMissionDraft,
  resolveMarketplaceAssistantRoutePrefix,
  sendMarketplaceAssistantTurn,
  type MarketplaceMissionDraft,
  type MarketplaceAssistantTranscriptMessage,
} from '@/lib/marketplace-assistant'
import type { MarketplaceBrowserHealth } from '@/lib/marketplace-api'
import {
  createMarketplaceMission,
  triggerMarketplaceScan,
  updateMarketplaceMission,
} from '@/lib/marketplace-api'

interface MarketplaceAssistantProps {
  apiKey: string
  browserHealth: MarketplaceBrowserHealth | null
  onMarketplaceStateChange: () => Promise<void> | void
  onScanQueued?: (jobId: string | null) => void
}

function createInitialMessages(homeLocation: string): MarketplaceAssistantTranscriptMessage[] {
  return [createTranscriptMessage('assistant', buildMarketplaceAssistantGreeting(homeLocation))]
}

function formatList(items: string[]): string {
  return items.length > 0 ? items.join(', ') : 'not set'
}

function formatBudget(draft: MarketplaceMissionDraft): string {
  const min = draft.hardFilters.priceMin
  const max = draft.hardFilters.priceMax
  if (min != null && max != null) {
    return `$${min}-$${max}`
  }
  if (max != null) {
    return `up to $${max}`
  }
  if (min != null) {
    return `from $${min}`
  }
  return 'not set'
}

function DraftSummary({ draft }: { draft: MarketplaceMissionDraft }) {
  return (
    <div className="space-y-3 text-xs">
      <div>
        <div className="font-medium text-foreground">Mission type</div>
        <div className="text-muted-foreground break-words font-mono">{draft.missionType}</div>
      </div>
      <div>
        <div className="font-medium text-foreground">Mission name</div>
        <div className="text-muted-foreground break-words">{draft.name || 'not set'}</div>
      </div>
      <div>
        <div className="font-medium text-foreground">User goal</div>
        <div className="text-muted-foreground break-words">{draft.userGoal || draft.brief || 'not set'}</div>
      </div>
      <div>
        <div className="font-medium text-foreground">Brief</div>
        <div className="text-muted-foreground break-words">{draft.brief || 'not set'}</div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <div className="font-medium text-foreground">Locations</div>
          <div className="text-muted-foreground break-words">{formatList(draft.hardFilters.locationNames)}</div>
        </div>
        <div>
          <div className="font-medium text-foreground">Budget</div>
          <div className="text-muted-foreground">{formatBudget(draft)}</div>
        </div>
      </div>
      <div>
        <div className="font-medium text-foreground">Include keywords</div>
        <div className="text-muted-foreground break-words">{formatList(draft.hardFilters.includeKeywords)}</div>
      </div>
      <div>
        <div className="font-medium text-foreground">Exclude / deal-breakers</div>
        <div className="text-muted-foreground break-words">
          {formatList([...draft.hardFilters.excludeKeywords, ...draft.hardFilters.forbiddenTerms])}
        </div>
      </div>
      <div>
        <div className="font-medium text-foreground">Preferred brands</div>
        <div className="text-muted-foreground break-words">{formatList(draft.softPreferences.preferredBrands)}</div>
      </div>
    </div>
  )
}

export function MarketplaceAssistant({
  apiKey,
  browserHealth,
  onMarketplaceStateChange,
  onScanQueued,
}: MarketplaceAssistantProps) {
  const { chatModel, activeSource, apiDefaultEnabled, preferences } = useCockpitStore()
  const homeLocation = preferences.marketplaceHomeLocation.trim()
  const effectiveRoute = resolveMarketplaceAssistantRoutePrefix(
    activeSource,
    chatModel,
    apiDefaultEnabled,
    preferences.marketplacePreferCloudRouting,
  )
  const [draft, setDraft] = useState<MarketplaceMissionDraft>(() => createMarketplaceMissionDraft(homeLocation))
  const [messages, setMessages] = useState<MarketplaceAssistantTranscriptMessage[]>(() =>
    createInitialMessages(homeLocation),
  )
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [requestError, setRequestError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const requestControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    setSessionId(getMarketplaceAssistantSessionId())
  }, [])

  useEffect(() => {
    setDraft((current) => {
      if (current.hardFilters.locationNames.length > 0 || !homeLocation) {
        return current
      }
      return mergeMarketplaceMissionDraft(current, {}, { homeLocation })
    })

    setMessages((current) => {
      if (current.length !== 1 || current[0]?.role !== 'assistant') {
        return current
      }
      return createInitialMessages(homeLocation)
    })
  }, [homeLocation])

  async function handleSendMessage() {
    const userMessage = input.trim()
    if (!userMessage || isSending || !sessionId) {
      return
    }

    const userEntry = createTranscriptMessage('user', userMessage)
    const nextMessages = [...messages, userEntry]

    setInput('')
    setRequestError(null)
    setNotice(null)
    setIsSending(true)
    setMessages(nextMessages)
    const controller = new AbortController()
    requestControllerRef.current = controller

    try {
      const response = await sendMarketplaceAssistantTurn({
        apiKey,
        browserHealth,
        draft,
        homeLocation,
        messages: nextMessages,
        model: chatModel,
        activeSource,
        apiDefaultEnabled,
        marketplacePreferCloudRouting: preferences.marketplacePreferCloudRouting,
        webSearchEnabled: preferences.webSearchEnabled,
        sessionId,
        userMessage,
        signal: controller.signal,
      })

      const mergedDraft = mergeMarketplaceMissionDraft(draft, response.draftDelta, {
        homeLocation,
        modelMissingFields: response.missingFields,
        modelReadyToCreate: response.readyToCreate,
      })

      setDraft(mergedDraft)
      setMessages((current) => [
        ...current,
        createTranscriptMessage('assistant', response.assistantMessage),
      ])
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setNotice('Assistant request cancelled.')
      } else {
        setRequestError(error instanceof Error ? error.message : 'Marketplace assistant request failed')
      }
    } finally {
      setIsSending(false)
      requestControllerRef.current = null
    }
  }

  function handleCancelMessage() {
    requestControllerRef.current?.abort()
  }

  function resetAssistant() {
    setDraft(createMarketplaceMissionDraft(homeLocation))
    setMessages(createInitialMessages(homeLocation))
    setInput('')
  }

  async function handleCreateMission(runNow: boolean) {
    if (isCreating) return

    const evaluated = evaluateMarketplaceMissionDraft(draft)
    if (!evaluated.readyToCreate) {
      setRequestError(`Mission is still missing: ${evaluated.missingFields.join(', ')}`)
      return
    }

    setIsCreating(true)
    setRequestError(null)
    setNotice(null)

    try {
      const createdFromChatMessageId =
        [...messages].reverse().find((message) => message.role === 'user')?.id ?? null
      const createdMission = await createMarketplaceMission(
        apiKey,
        mapMarketplaceDraftToMissionPayload(draft, {
          createdFromChatMessageId,
        }),
      )

      if (!runNow) {
        setMessages((current) => [
          ...current,
          createTranscriptMessage(
            'system',
            `Mission created in paused state: ${createdMission.name} (${createdMission.mission_id}).`,
          ),
        ])
        setNotice(`Created paused mission ${createdMission.name}.`)
        await onMarketplaceStateChange()
        resetAssistant()
        return
      }

      try {
        const queuedScan = await triggerMarketplaceScan(apiKey, createdMission.mission_id)
        onScanQueued?.(queuedScan.job_id ?? null)
        await updateMarketplaceMission(apiKey, createdMission.mission_id, { status: 'active' })
        setMessages((current) => [
          ...current,
          createTranscriptMessage(
            'system',
            `Mission created and scan queued: ${createdMission.name} (${createdMission.mission_id})${queuedScan.job_id ? `, job ${queuedScan.job_id}` : ''}.`,
          ),
        ])
        setNotice(
          queuedScan.job_id
            ? `Created mission and queued scan ${queuedScan.job_id}.`
            : 'Created mission and queued scan.',
        )
        await onMarketplaceStateChange()
        resetAssistant()
      } catch (error) {
        setMessages((current) => [
          ...current,
          createTranscriptMessage(
            'system',
            `Mission created in paused state, but the scan did not queue cleanly: ${createdMission.name} (${createdMission.mission_id}).`,
          ),
        ])
        setRequestError(
          error instanceof Error
            ? `Mission created in paused state, but Create + Run Now failed: ${error.message}`
            : 'Mission created in paused state, but Create + Run Now failed.',
        )
        await onMarketplaceStateChange()
      }
    } catch (error) {
      setRequestError(
        error instanceof Error ? error.message : runNow ? 'Failed to create and run mission' : 'Failed to create mission',
      )
    } finally {
      setIsCreating(false)
    }
  }

  const canRunNow =
    browserHealth?.scan_allowed ?? (browserHealth?.status === 'ready' && !browserHealth?.challenge_detected)
  const scanBlocker =
    browserHealth?.scan_blocker
    || browserHealth?.detail
    || 'Browser health must be ready before the assistant can queue a scan.'
  const readyToCreate = draft.status === 'ready'
  const previewPayload = useMemo(
    () => mapMarketplaceDraftToMissionPayload(draft),
    [draft],
  )

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">Marketplace Assistant</CardTitle>
          <Badge variant="outline" className="font-mono text-[10px]">
            {chatModel}
          </Badge>
        </div>
        <CardDescription>
          Talk to the active model, draft a mission, then explicitly create it or run it.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="secondary" className="gap-1">
            <MapPin className="h-3 w-3" />
            {homeLocation || 'No home location saved'}
          </Badge>
          <Badge variant="outline">Browser: {browserHealth?.status || 'unknown'}</Badge>
          <Badge variant="outline">Route: {effectiveRoute === '/cloud' ? 'cloud' : 'local'}</Badge>
        </div>

        {(requestError || notice) && (
          <div
            className={`rounded-lg border p-3 text-sm ${
              requestError
                ? 'border-destructive/50 bg-destructive/10 text-destructive'
                : 'border-primary/50 bg-primary/10 text-primary'
            }`}
          >
            {requestError || notice}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-[1.35fr_0.95fr]">
          <div className="space-y-3">
            <div className="overflow-hidden rounded-md border border-border/60 bg-muted/20">
              <ScrollArea className="h-[320px]">
                <div className="space-y-3 p-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`rounded-lg border px-3 py-2 text-sm ${
                        message.role === 'user'
                          ? 'border-primary/40 bg-primary/5'
                          : message.role === 'system'
                            ? 'border-secondary/60 bg-secondary/20'
                            : 'border-border/60 bg-background'
                      }`}
                    >
                      <div className="mb-1 flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                        <MessageSquareText className="h-3 w-3" />
                        {message.role}
                      </div>
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>

            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Describe what you want to buy, your budget, location, and deal-breakers..."
              rows={4}
            />

            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => void handleSendMessage()} disabled={isSending || !input.trim() || !sessionId}>
                {isSending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Send
              </Button>
              {isSending && (
                <Button variant="destructive" onClick={handleCancelMessage}>
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              )}
              <Button
                variant="outline"
                onClick={resetAssistant}
                disabled={isSending || isCreating}
              >
                Reset Draft
              </Button>
            </div>
          </div>

          <div className="space-y-4 rounded-lg border border-border/60 bg-muted/10 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-sm font-medium">Draft Summary</div>
              <Badge variant={readyToCreate ? 'default' : 'outline'}>
                {readyToCreate ? 'Ready to create' : 'Collecting details'}
              </Badge>
            </div>
            <DraftSummary draft={draft} />
            <Separator />
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="marketplace-mission-type">
                Mission Type
              </label>
              <select
                id="marketplace-mission-type"
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={draft.missionType}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    missionType: event.target.value as MarketplaceMissionDraft['missionType'],
                  }))
                }
                disabled={isSending || isCreating}
              >
                <option value="find_good_deals">find_good_deals</option>
                <option value="benchmark_listings">benchmark_listings</option>
                <option value="refresh_retail_benchmarks">refresh_retail_benchmarks</option>
                <option value="review_uncertain_matches">review_uncertain_matches</option>
              </select>
            </div>
            <Separator />
            <div className="space-y-2">
              <div className="text-sm font-medium">Missing fields</div>
              <div className="flex flex-wrap gap-2">
                {draft.missingFields.length === 0 ? (
                  <Badge variant="secondary">none</Badge>
                ) : (
                  draft.missingFields.map((field) => (
                    <Badge key={field} variant="outline">
                      {field}
                    </Badge>
                  ))
                )}
              </div>
            </div>
            <Separator />
            <div className="space-y-2">
              <div className="text-sm font-medium">Mission Preview</div>
              <div className="overflow-hidden rounded-md border border-border/60 bg-muted/20">
                <ScrollArea className="h-[180px]">
                  <pre className="p-3 text-[11px] leading-5">
                    {JSON.stringify(previewPayload, null, 2)}
                  </pre>
                </ScrollArea>
              </div>
            </div>
            <Separator />
            <div className="space-y-2">
              <Button
                className="w-full"
                onClick={() => void handleCreateMission(false)}
                disabled={!readyToCreate || isCreating}
              >
                {isCreating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Deploy Mission
              </Button>
              <Button
                className="w-full"
                variant="secondary"
                onClick={() => void handleCreateMission(true)}
                disabled={!readyToCreate || !canRunNow || isCreating}
              >
                {isCreating ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                Deploy + Run Now
              </Button>
              {!canRunNow && (
                <p className="text-xs text-muted-foreground">
                  {scanBlocker}
                </p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
