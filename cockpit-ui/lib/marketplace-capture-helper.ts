export const MARKETPLACE_CAPTURE_CHANNEL = 'cockpit-marketplace-capture'

export type MarketplaceCaptureIngestResponse = {
  source_id: string
  listing_title?: string
  source_name?: string
  webpage_url?: string
  staged?: boolean
  chunks_staged?: number
  chunks_indexed?: number
  detected_tickers?: string[]
  source_kind?: 'ephemeral' | 'concat' | 'primary'
}

export type MarketplaceCaptureRelayResponse =
  | {
      ok: true
      ingest: MarketplaceCaptureIngestResponse
    }
  | {
      ok: false
      message: string
    }

export function isMarketplaceCaptureRelayResponse(
  value: unknown,
): value is MarketplaceCaptureRelayResponse {
  if (!value || typeof value !== 'object') {
    return false
  }
  const candidate = value as { ok?: unknown; ingest?: unknown; message?: unknown }
  if (candidate.ok === true) {
    return !!candidate.ingest && typeof candidate.ingest === 'object'
  }
  if (candidate.ok === false) {
    return typeof candidate.message === 'string'
  }
  return false
}

export function buildMarketplaceCaptureScript(params: {
  submitUrl: string
  token: string
}): string {
  const submitUrl = JSON.stringify(params.submitUrl)
  const token = JSON.stringify(params.token)
  return [
    '(() => {',
    '  const listingUrl = String(window.location.href || "").trim()',
    '  if (!/^https?:\\/\\/(?:www\\.|m\\.)?facebook\\.com\\/marketplace\\/item\\//i.test(listingUrl)) {',
    '    window.alert("Open a Facebook Marketplace item page before running this helper.");',
    '    return;',
    '  }',
    '  const clean = (value) => String(value || "").replace(/\\s+/g, " ").trim()',
    '  const dedupe = (items) => {',
    '    const out = []',
    '    const seen = new Set()',
    '    for (const item of items) {',
    '      const cleaned = clean(item)',
    '      if (!cleaned) continue',
    '      const key = cleaned.toLowerCase()',
    '      if (seen.has(key)) continue',
    '      seen.add(key)',
    '      out.push(cleaned)',
    '    }',
    '    return out',
    '  }',
    '  const collect = (selector) => Array.from(document.querySelectorAll(selector)).map((node) => clean(node.innerText || node.textContent || ""))',
    '  const visible = dedupe(',
    "    collect('h1,h2,h3,span,div,p,a,li').filter((text) => text.length >= 2 && text.length <= 280)",
    '  )',
    '  const byHeading = (heading) => {',
    '    const index = visible.findIndex((text) => text.toLowerCase() === heading)',
    '    if (index < 0) return null',
    '    for (let i = index + 1; i < Math.min(visible.length, index + 6); i += 1) {',
    '      const candidate = visible[i]',
    '      if (candidate && candidate.toLowerCase() !== heading) return candidate',
    '    }',
    '    return null',
    '  }',
    '  const title = clean(document.querySelector(\'meta[property="og:title"]\')?.content) || clean(document.querySelector("h1")?.textContent) || clean(document.title)',
    '  const metaDescription = clean(document.querySelector(\'meta[property="og:description"]\')?.content) || clean(document.querySelector(\'meta[name="description"]\')?.content)',
    '  const price = visible.find((text) => /(?:A\\$|AU\\$|USD\\s*\\$|\\$)\\s?\\d[\\d,]*(?:\\.\\d{2})?/.test(text)) || clean(document.querySelector(\'meta[property="product:price:amount"]\')?.content)',
    '  const sellerName = byHeading("seller details") || byHeading("seller information") || byHeading("seller") || ""',
    '  let location = visible.find((text) => /^Location is approximate/i.test(text)) || byHeading("location") || ""',
    '  if (!location && metaDescription) {',
    '    const match = metaDescription.match(/\\bin\\s+([A-Za-z0-9 ,.\'-]{3,80})/i)',
    '    if (match) location = clean(match[1])',
    '  }',
    '  const description = byHeading("description") || metaDescription || visible.find((text) => text.length >= 80) || ""',
    '  const popup = window.open("about:blank", "marketplaceCaptureStatus", "popup=yes,width=560,height=700")',
    '  if (!popup) {',
    '    window.alert("Allow pop-ups for Cockpit to finish the Marketplace capture.")',
    '    return',
    '  }',
    '  try {',
    '    popup.document.title = "Marketplace capture"',
    '    popup.document.body.innerHTML = \'<p style="font-family: sans-serif; padding: 16px;">Submitting Marketplace listing to Cockpit...</p>\'',
    '  } catch (error) {',
    '    // Ignore popup document access failures and continue with form submission.',
    '  }',
    '  const form = document.createElement("form")',
    '  form.method = "POST"',
    `  form.action = ${submitUrl}`,
    '  form.target = "marketplaceCaptureStatus"',
    '  const append = (name, value) => {',
    '    const input = document.createElement("input")',
    '    input.type = "hidden"',
    '    input.name = name',
    '    input.value = clean(value)',
    '    form.appendChild(input)',
    '  }',
    `  append("token", ${token})`,
    '  append("url", listingUrl)',
    '  append("captured_at", new Date().toISOString())',
    '  append("title", title)',
    '  append("price", price)',
    '  append("seller_name", sellerName)',
    '  append("location", location)',
    '  append("description", description)',
    '  append("raw_text_lines", JSON.stringify(visible.slice(0, 80)))',
    '  document.body.appendChild(form)',
    '  form.submit()',
    '  form.remove()',
    '})()',
  ].join('\n')
}

export function buildMarketplaceCaptureBookmarklet(params: {
  submitUrl: string
  token: string
}): string {
  return `javascript:${encodeURIComponent(buildMarketplaceCaptureScript(params))}`
}
