#!/usr/bin/env bash
# capture-screenshots.sh — Capture screenshots of every cockpit-ui route
#
# Prerequisites:
#   - cockpit-ui dev server running on localhost:3000
#   - pnpm add -D playwright (in cockpit-ui/)
#   - npx playwright install chromium (one-time setup)
#
# Usage:
#   bash docs/design-pack/scripts/capture-screenshots.sh [base_url]
#
# Output: docs/design-pack/screenshots/*.png
#
# Notes:
#   - Uses waitUntil:'load' not 'networkidle' because the cockpit UI has
#     always-on health polling (every 3s) that prevents network idle.
#   - If routes fail to compile, check for stale cockpit-ui/styles/globals.css
#     (it contains @import 'tailwindcss' which Turbopack tries to resolve
#     from the wrong directory).

set -euo pipefail

BASE_URL="${1:-http://localhost:3000}"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT_DIR="${REPO_ROOT}/docs/design-pack/screenshots"

mkdir -p "$OUT_DIR"

echo "=== Cockpit UI Screenshot Capture ==="
echo "Base URL: $BASE_URL"
echo "Output:   $OUT_DIR"
echo ""

# Check if the dev server is reachable
if ! curl -sf "${BASE_URL}" > /dev/null 2>&1; then
  echo "ERROR: Cannot reach ${BASE_URL}"
  echo "Start the cockpit-ui dev server first:"
  echo "  cd cockpit-ui && pnpm dev"
  exit 1
fi

# Phase 1: Warm all routes (triggers Turbopack compilation on first visit)
echo "Phase 1: Warming routes..."
ROUTES="/ /operations /updater /verification /history /settings /news /intel-ops /holdings /boot"
for route in $ROUTES; do
  name=$(echo "$route" | sed 's|^/||; s|^$|home|; s|/|-|g')
  start=$(date +%s)
  code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 300 "${BASE_URL}${route}" 2>/dev/null || echo "000")
  elapsed=$(( $(date +%s) - start ))
  echo "  ${name} -> HTTP ${code} (${elapsed}s)"
done
echo ""

# Phase 2: Capture with Playwright (run from cockpit-ui for node_modules access)
echo "Phase 2: Capturing screenshots..."
cd "${REPO_ROOT}/cockpit-ui"

node -e "
const { chromium } = require('playwright');
const { mkdirSync } = require('fs');
const { resolve } = require('path');

const BASE_URL = '${BASE_URL}';
const OUT = resolve('${OUT_DIR}');
mkdirSync(OUT, { recursive: true });

const routes = [
  { path: '/',              name: 'chat' },
  { path: '/operations',    name: 'operations' },
  { path: '/updater',       name: 'updater' },
  { path: '/verification',  name: 'verification' },
  { path: '/history',       name: 'history' },
  { path: '/settings',      name: 'settings' },
  { path: '/news',          name: 'news' },
  { path: '/intel-ops',     name: 'intel-pulse' },
  { path: '/holdings',      name: 'holdings' },
  { path: '/boot',          name: 'boot' },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  let ok = 0;

  for (const vp of [
    { w: 1920, h: 1080, s: 'desktop' },
    { w: 1280, h: 800,  s: 'laptop' },
  ]) {
    const ctx = await browser.newContext({
      viewport: { width: vp.w, height: vp.h },
      colorScheme: 'dark',
      deviceScaleFactor: 2,
    });
    const page = await ctx.newPage();
    for (const r of routes) {
      try {
        await page.goto(BASE_URL + r.path, { waitUntil: 'load', timeout: 30000 });
        await page.waitForTimeout(3000);
        const f = r.name + '_' + vp.s + '.png';
        await page.screenshot({ path: resolve(OUT, f), fullPage: false });
        console.log('  ' + f + ' OK');
        ok++;
      } catch (e) {
        console.log('  ' + r.name + '_' + vp.s + ' FAILED: ' + e.message.split('\n')[0]);
      }
    }
    await ctx.close();
  }

  // Sidebar states
  console.log('  Capturing sidebar states...');
  const ctx2 = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: 'dark',
    deviceScaleFactor: 2,
  });
  const pg = await ctx2.newPage();
  try {
    await pg.goto(BASE_URL + '/', { waitUntil: 'load', timeout: 30000 });
    await pg.waitForTimeout(3000);
    await pg.screenshot({ path: resolve(OUT, 'sidebar_expanded.png') });
    console.log('  sidebar_expanded.png OK');
    ok++;
    const btn = pg.locator('button[data-sidebar=\"trigger\"]').first();
    if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await btn.click();
      await pg.waitForTimeout(800);
      await pg.screenshot({ path: resolve(OUT, 'sidebar_collapsed.png') });
      console.log('  sidebar_collapsed.png OK');
      ok++;
    }
  } catch(e) {
    console.log('  sidebar FAILED: ' + e.message.split('\n')[0]);
  }

  await browser.close();
  console.log('\nDone! ' + ok + ' screenshots captured to ' + OUT);
})();
" 2>&1

echo ""
echo "=== Screenshot manifest ==="
ls -lh "$OUT_DIR"/*.png 2>/dev/null || echo "(no screenshots captured)"
