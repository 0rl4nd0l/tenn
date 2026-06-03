import { describe, expect, it } from 'vitest'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()

describe('cockpit route source surface', () => {
  it('includes config and basic local BFF route sources', () => {
    for (const route of [
      'app/api/cockpit/config/route.ts',
      'app/api/cockpit/health/route.ts',
      'app/api/cockpit/watchlist/route.ts',
      'app/api/cockpit/holdings/route.ts'
    ]) {
      expect(existsSync(join(root, route))).toBe(true)
    }
  })
})
