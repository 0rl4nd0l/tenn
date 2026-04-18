import { NextResponse } from 'next/server'

import {
  MARKETPLACE_CAPTURE_CHANNEL,
  type MarketplaceCaptureIngestResponse,
  type MarketplaceCaptureRelayResponse,
} from '@/lib/marketplace-capture-helper'
import { getMarketplaceCaptureToken } from '@/lib/marketplace-capture-tokens'
import { resolveBackendUrl } from '@/lib/proxy'

export const runtime = 'nodejs'

function getFormString(formData: FormData, key: string): string {
  const value = formData.get(key)
  return typeof value === 'string' ? value.trim() : ''
}

function parseRawTextLines(raw: string): string[] {
  if (!raw) {
    return []
  }
  try {
    const parsed = JSON.parse(raw) as unknown
    return Array.isArray(parsed) ? parsed.map((item) => String(item || '')) : []
  } catch {
    return []
  }
}

function statusPageHtml(title: string, message: string, payload: MarketplaceCaptureRelayResponse) {
  const serializedPayload = JSON.stringify(payload).replace(/</g, '\\u003c')
  const channelName = JSON.stringify(MARKETPLACE_CAPTURE_CHANNEL)
  const safeTitle = title.replace(/[<&>]/g, '')
  const safeMessage = message.replace(/[<&>]/g, '')
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${safeTitle}</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; background: #f7f4eb; color: #1d1b16; }
    main { max-width: 40rem; margin: 3rem auto; padding: 1.5rem; background: #fffdf7; border: 1px solid #d8d1bf; border-radius: 1rem; }
    h1 { margin-top: 0; font-size: 1.5rem; }
    p { line-height: 1.5; }
    code { background: #f1ead6; padding: 0.125rem 0.375rem; border-radius: 0.375rem; }
  </style>
</head>
<body>
  <main>
    <h1>${safeTitle}</h1>
    <p>${safeMessage}</p>
    <p>You can close this window and return to Cockpit.</p>
  </main>
  <script>
    const payload = ${serializedPayload};
    try {
      const channel = new BroadcastChannel(${channelName});
      channel.postMessage(payload);
      channel.close();
    } catch (error) {
      console.error('Broadcast failed', error);
    }
    window.setTimeout(() => {
      try { window.close(); } catch (error) {}
    }, 1200);
  </script>
</body>
</html>`
}

export async function POST(request: Request): Promise<NextResponse> {
  const formData = await request.formData()
  const token = getFormString(formData, 'token')
  const tokenEntry = getMarketplaceCaptureToken(token)

  if (!tokenEntry) {
    return new NextResponse(
      statusPageHtml('Marketplace helper expired', 'Open the helper from Cockpit again to mint a fresh capture token.', {
        ok: false,
        message: 'Marketplace helper token expired. Reopen the helper from Cockpit and try again.',
      }),
      {
        status: 410,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        },
      },
    )
  }

  const payload = {
    url: getFormString(formData, 'url'),
    captured_at: getFormString(formData, 'captured_at') || undefined,
    title: getFormString(formData, 'title') || undefined,
    price: getFormString(formData, 'price') || undefined,
    seller_name: getFormString(formData, 'seller_name') || undefined,
    location: getFormString(formData, 'location') || undefined,
    description: getFormString(formData, 'description') || undefined,
    raw_text_lines: parseRawTextLines(getFormString(formData, 'raw_text_lines')),
  }

  const headers = new Headers({
    'Content-Type': 'application/json',
  })
  if (tokenEntry.apiKey) {
    headers.set('X-API-Key', tokenEntry.apiKey)
  }

  try {
    const backend = await fetch(`${resolveBackendUrl()}/api/commentary/ingest-marketplace-snapshot`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      cache: 'no-store',
    })
    const rawBody = await backend.text()
    if (!backend.ok) {
      let message = rawBody || `Marketplace capture failed (${backend.status})`
      try {
        const parsed = JSON.parse(rawBody) as { detail?: unknown; error?: unknown }
        message = typeof parsed.detail === 'string'
          ? parsed.detail
          : typeof parsed.error === 'string'
            ? parsed.error
            : message
      } catch {
        // Keep the raw backend response as the error detail.
      }
      return new NextResponse(
        statusPageHtml('Marketplace capture failed', message, {
          ok: false,
          message,
        }),
        {
          status: backend.status,
          headers: {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-store',
          },
        },
      )
    }

    const ingest = JSON.parse(rawBody) as MarketplaceCaptureIngestResponse
    const title = ingest.listing_title || ingest.source_name || 'Facebook Marketplace listing'
    return new NextResponse(
      statusPageHtml('Marketplace listing captured', `${title} was staged in Cockpit.`, {
        ok: true,
        ingest,
      }),
      {
        status: 200,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        },
      },
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to reach Cockpit relay'
    return new NextResponse(
      statusPageHtml('Marketplace relay failed', message, {
        ok: false,
        message,
      }),
      {
        status: 502,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-store',
        },
      },
    )
  }
}
