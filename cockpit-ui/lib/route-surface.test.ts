import { describe, expect, it } from 'vitest'

import {
  REQUIRED_ROUTE_PAIRS,
  REQUIRED_SOURCE_FILES,
  collectRouteSurfaceIssues,
} from '../scripts/check-route-surface.mjs'

describe('cockpit route source surface', () => {
  it('tracks representative cockpit source files', () => {
    expect(REQUIRED_SOURCE_FILES).toContain('cockpit-ui/components/cockpit/chat/chat-screen.tsx')
    expect(REQUIRED_SOURCE_FILES).toContain('cockpit-ui/lib/cockpit-chat-actionability.ts')
  })

  it('covers the core cockpit BFF to backend route pairs', () => {
    expect(REQUIRED_ROUTE_PAIRS).toContainEqual({
      frontendRoute: '/api/cockpit/config',
      localSource: 'cockpit-ui/app/api/cockpit/config/route.ts',
      backendDecorator: '/config',
    })
  })

  it('passes the core route-surface parity check for this worktree', () => {
    expect(collectRouteSurfaceIssues()).toEqual([])
  })
})
