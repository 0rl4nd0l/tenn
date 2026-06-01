export interface CompactChromeInput {
  iphoneScale: boolean
  isMobileViewport: boolean
}

export function shouldUseCompactChrome({
  iphoneScale,
  isMobileViewport,
}: CompactChromeInput): boolean {
  return iphoneScale || isMobileViewport
}
