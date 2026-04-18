import { describe, expect, it } from 'vitest'

import { extractYouTubeUrl, isYouTubeUrl } from './youtube-url'

describe('YouTube URL detection', () => {
  it('accepts canonical formats', () => {
    expect(isYouTubeUrl('https://youtu.be/abc123')).toBe(true)
    expect(isYouTubeUrl('https://www.youtube.com/watch?v=abc123')).toBe(true)
    expect(isYouTubeUrl('https://youtube.com/shorts/abc123')).toBe(true)
  })

  it('rejects unrelated URLs', () => {
    expect(isYouTubeUrl('https://example.com')).toBe(false)
    expect(isYouTubeUrl('not a url at all')).toBe(false)
  })

  it('extracts URL from surrounding text', () => {
    expect(extractYouTubeUrl('check this https://youtu.be/abc123 now')).toBe('https://youtu.be/abc123')
  })

  it('returns null when no URL is present', () => {
    expect(extractYouTubeUrl('just text')).toBeNull()
  })
})
