import { useCallback, useState } from 'react'

export type AttachedSourceKind = 'ephemeral' | 'concat' | 'primary'

export interface AttachedSource {
  sourceId: string
  sourceKind: AttachedSourceKind
  title: string
}

export interface UseAttachedSources {
  attached: AttachedSource[]
  attach: (source: AttachedSource) => void
  detach: (sourceId: string) => void
  clear: () => void
  serialize: () => Array<{ source_id: string; source_kind: AttachedSourceKind }>
}

export function useAttachedSources(): UseAttachedSources {
  const [attached, setAttached] = useState<AttachedSource[]>([])

  const attach = useCallback((source: AttachedSource) => {
    setAttached((prev) => {
      const others = prev.filter((item) => item.sourceId !== source.sourceId)
      return [...others, source]
    })
  }, [])

  const detach = useCallback((sourceId: string) => {
    setAttached((prev) => prev.filter((item) => item.sourceId !== sourceId))
  }, [])

  const clear = useCallback(() => {
    setAttached([])
  }, [])

  const serialize = useCallback(
    () =>
      attached.map((source) => ({
        source_id: source.sourceId,
        source_kind: source.sourceKind,
      })),
    [attached],
  )

  return { attached, attach, detach, clear, serialize }
}
