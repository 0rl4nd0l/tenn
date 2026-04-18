interface CitationLinkProps {
  videoId: string
  segmentStartSeconds: number
}

function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(total / 60)
  const remainder = total % 60
  return `${minutes}:${remainder.toString().padStart(2, '0')}`
}

export function CitationLink({ videoId, segmentStartSeconds }: CitationLinkProps) {
  const roundedSeconds = Math.max(0, Math.floor(segmentStartSeconds))
  const href = `https://youtu.be/${videoId}?t=${roundedSeconds}s`

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="text-xs underline-offset-2 hover:underline"
    >
      ▶ {formatTimestamp(segmentStartSeconds)}
    </a>
  )
}
