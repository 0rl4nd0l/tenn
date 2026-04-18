const YOUTUBE_URL_RE =
  /https?:\/\/(?:www\.)?(?:youtu\.be\/[A-Za-z0-9_-]{6,}|youtube\.com\/(?:watch\?[^\s#]*v=[A-Za-z0-9_-]{6,}|shorts\/[A-Za-z0-9_-]{6,}))[^\s]*/i

export function isYouTubeUrl(input: string): boolean {
  return YOUTUBE_URL_RE.test(input.trim())
}

export function extractYouTubeUrl(input: string): string | null {
  const match = input.match(YOUTUBE_URL_RE)
  return match ? match[0] : null
}
