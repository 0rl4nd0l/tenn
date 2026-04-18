'use client'

import { Suspense, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { Button } from '@/components/ui/button'
import { buildMarketplaceCaptureBookmarklet } from '@/lib/marketplace-capture-helper'

function MarketplaceCapturePageContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const listingUrl = searchParams.get('url') ?? 'https://www.facebook.com/marketplace/'
  const submitUrl = useMemo(() => {
    if (typeof window === 'undefined') {
      return ''
    }
    return `${window.location.origin}/api/cockpit/commentary/marketplace-capture/submit`
  }, [])

  const bookmarkletHref = useMemo(() => {
    if (!token || !submitUrl) {
      return '#'
    }
    return buildMarketplaceCaptureBookmarklet({
      submitUrl,
      token,
    })
  }, [submitUrl, token])

  return (
    <CockpitLayout title="Marketplace Helper">
      <div className="mx-auto flex max-w-3xl flex-col gap-6 rounded-3xl border border-stone-300 bg-stone-50 p-6 shadow-sm">
        <div className="space-y-3">
          <h2 className="text-2xl font-semibold text-stone-900">Browser Helper</h2>
          <p className="text-sm leading-6 text-stone-700">
            This helper works in Firefox, Opera, and Chromium browsers. Open the listing in the browser
            you want to use, sign in to Facebook there, then click the bookmarklet once on the listing page.
            Cockpit will stage the capture automatically.
          </p>
        </div>

        <div className="grid gap-3 rounded-2xl border border-stone-200 bg-white p-4 text-sm text-stone-700">
          <p>1. Open the Facebook Marketplace listing in this browser.</p>
          <p>2. Sign in if Facebook prompts you.</p>
          <p>3. Drag the bookmarklet below to your bookmarks bar, or right-click and bookmark it.</p>
          <p>4. On the listing page, click the bookmarklet once to send the snapshot back to Cockpit.</p>
          <p>5. After the success popup appears, you can minimize or close Facebook. No persistent tab is required.</p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <a href={listingUrl} target="_blank" rel="noreferrer">
              Open Listing
            </a>
          </Button>
          <Button asChild variant="secondary">
            <a href={bookmarkletHref}>
              Capture Marketplace Listing
            </a>
          </Button>
        </div>

        <p className="text-xs leading-5 text-stone-600">
          Limitation: a web app cannot force a different desktop browser to open. The helper runs in whichever
          browser tab opened this page. If you want Firefox or Opera specifically, open Cockpit there first and
          use the helper from that browser.
        </p>
      </div>
    </CockpitLayout>
  )
}

function MarketplaceCaptureFallback() {
  return (
    <CockpitLayout title="Marketplace Helper">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 rounded-3xl border border-stone-300 bg-stone-50 p-6 shadow-sm">
        <h2 className="text-2xl font-semibold text-stone-900">Browser Helper</h2>
        <p className="text-sm leading-6 text-stone-700">Loading Marketplace helper…</p>
      </div>
    </CockpitLayout>
  )
}

export default function MarketplaceCapturePage() {
  return (
    <Suspense fallback={<MarketplaceCaptureFallback />}>
      <MarketplaceCapturePageContent />
    </Suspense>
  )
}
