#!/usr/bin/env bash
# capture-screenshots.sh — Capture screenshots of every cockpit-ui route
#
# Prerequisites:
#   - cockpit-ui dev server running on localhost:3000
#   - npx playwright install chromium  (one-time setup)
#
# Usage:
#   bash docs/design-pack/scripts/capture-screenshots.sh [base_url]
#
# Output: docs/design-pack/screenshots/*.png

set -euo pipefail

BASE_URL="${1:-http://localhost:3000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/screenshots"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

# Routes to capture
ROUTES=(
  "/:chat"
  "/operations:operations"
  "/updater:updater"
  "/verification:verification"
  "/history:history"
  "/settings:settings"
  "/news:news"
  "/intel-ops:intel-pulse"
  "/boot:boot"
)

# Generate the Playwright script
PLAYWRIGHT_SCRIPT=$(mktemp /tmp/capture-XXXXXX.mjs)

cat > "$PLAYWRIGHT_SCRIPT" << 'PLAYWRIGHT_EOF'
import { chromium } from 'playwright';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const OUT_DIR = process.env.OUT_DIR || './screenshots';
const TIMESTAMP = process.env.TIMESTAMP || 'latest';

const routes = [
  { path: '/',              name: 'chat' },
  { path: '/operations',    name: 'operations' },
  { path: '/updater',       name: 'updater' },
  { path: '/verification',  name: 'verification' },
  { path: '/history',       name: 'history' },
  { path: '/settings',      name: 'settings' },
  { path: '/news',          name: 'news' },
  { path: '/intel-ops',     name: 'intel-pulse' },
  { path: '/boot',          name: 'boot' },
];

const viewports = [
  { width: 1920, height: 1080, suffix: 'desktop' },
  { width: 1280, height: 800,  suffix: 'laptop' },
];

async function main() {
  const browser = await chromium.launch({ headless: true });

  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      colorScheme: 'dark',
      deviceScaleFactor: 2,  // Retina quality
    });
    const page = await context.newPage();

    for (const route of routes) {
      const url = `${BASE_URL}${route.path}`;
      console.log(`  Capturing ${route.name} (${vp.suffix}) ...`);

      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
        // Wait for animations to settle
        await page.waitForTimeout(1500);

        const filename = `${route.name}_${vp.suffix}_${TIMESTAMP}.png`;
        await page.screenshot({
          path: `${OUT_DIR}/${filename}`,
          fullPage: false,
        });
        console.log(`    -> ${filename}`);
      } catch (err) {
        console.error(`    FAILED: ${err.message}`);
      }
    }

    await context.close();
  }

  // Also capture sidebar expanded and collapsed
  console.log('\n  Capturing sidebar states...');
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: 'dark',
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: `${OUT_DIR}/sidebar_expanded_${TIMESTAMP}.png`,
      fullPage: false,
    });

    // Click the sidebar trigger to collapse
    const trigger = page.locator('[data-sidebar="trigger"]').first();
    if (await trigger.isVisible()) {
      await trigger.click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `${OUT_DIR}/sidebar_collapsed_${TIMESTAMP}.png`,
        fullPage: false,
      });
    }
  } catch (err) {
    console.error(`  Sidebar capture failed: ${err.message}`);
  }

  await browser.close();
  console.log('\nDone! Screenshots saved to:', OUT_DIR);
}

main().catch(console.error);
PLAYWRIGHT_EOF

echo "Running Playwright screenshot capture..."
BASE_URL="$BASE_URL" OUT_DIR="$OUT_DIR" TIMESTAMP="$TIMESTAMP" \
  npx --yes playwright test --config=/dev/null 2>/dev/null || \
  node "$PLAYWRIGHT_SCRIPT" 2>&1

rm -f "$PLAYWRIGHT_SCRIPT"

echo ""
echo "=== Screenshot manifest ==="
ls -la "$OUT_DIR"/*.png 2>/dev/null || echo "(no screenshots captured)"
echo ""
echo "To view: open $OUT_DIR in a file browser or image viewer"
