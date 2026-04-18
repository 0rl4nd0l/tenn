const MARKETPLACE_URL_RE =
  /https?:\/\/(?:www\.|m\.)?facebook\.com\/marketplace\/item\/[^\s?#]+[^\s]*/i

export function isMarketplaceUrl(input: string): boolean {
  return MARKETPLACE_URL_RE.test(input.trim())
}

export function extractMarketplaceUrl(input: string): string | null {
  const match = input.match(MARKETPLACE_URL_RE)
  return match ? match[0] : null
}
