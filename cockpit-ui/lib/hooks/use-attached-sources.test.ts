import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useAttachedSources } from './use-attached-sources'

describe('useAttachedSources', () => {
  it('attaches and detaches sources', () => {
    const { result } = renderHook(() => useAttachedSources())

    act(() => {
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'ephemeral', title: 'A' })
    })

    expect(result.current.attached).toHaveLength(1)
    expect(result.current.attached[0]?.sourceId).toBe('yt_a')

    act(() => {
      result.current.detach('yt_a')
    })

    expect(result.current.attached).toHaveLength(0)
  })

  it('dedupes repeat attaches on same source_id', () => {
    const { result } = renderHook(() => useAttachedSources())

    act(() => {
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'concat', title: 'A' })
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'ephemeral', title: 'A' })
    })

    expect(result.current.attached).toHaveLength(1)
    expect(result.current.attached[0]?.sourceKind).toBe('ephemeral')
  })

  it('serializes to the chat request shape', () => {
    const { result } = renderHook(() => useAttachedSources())

    act(() => {
      result.current.attach({ sourceId: 'yt_a', sourceKind: 'concat', title: 'A' })
    })

    expect(result.current.serialize()).toEqual([
      { source_id: 'yt_a', source_kind: 'concat' },
    ])
  })
})
