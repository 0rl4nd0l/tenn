/**
 * screenshot-capture.mjs — Capture screenshots of every cockpit-ui route
 *
 * Run from cockpit-ui/ directory (where playwright is installed):
 *   node ../docs/design-pack/scripts/screenshot-capture.mjs [base_url]
 *
 * Or set NODE_PATH:
 *   NODE_PATH=cockpit-ui/node_modules node docs/design-pack/scripts/screenshot-capture.mjs
 *
 * Requires: pnpm add -D playwright && npx playwright install chromium
 */
import { createRequire } from 'module';
import { mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// Resolve playwright from cockpit-ui/node_modules regardless of where script lives
const __dirname = dirname(fileURLToPath(import.meta.url));
const cockpitUiDir = resolve(__dirname, '..', '..', '..', 'cockpit-ui');
const require = createRequire(resolve(cockpitUiDir, 'package.json'));
const { chromium } = require('playwright');

const BASE_URL = process.argv[2] || 'http://localhost:3000';
const OUT_DIR = resolve(__dirname, '..', 'screenshots');
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);

mkdirSync(OUT_DIR, { recursive: true });

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
  console.log(`\n=== Cockpit UI Screenshot Capture ===`);
  console.log(`Base URL:  ${BASE_URL}`);
  console.log(`Output:    ${OUT_DIR}`);
  console.log(`Timestamp: ${TIMESTAMP}\n`);

  const browser = await chromium.launch({ headless: true });
  let captured = 0;

  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      colorScheme: 'dark',
      deviceScaleFactor: 2,
    });
    const page = await context.newPage();

    for (const route of routes) {
      const url = `${BASE_URL}${route.path}`;
      const filename = `${route.name}_${vp.suffix}.png`;

      try {
        process.stdout.write(`  ${route.name} (${vp.suffix}) ... `);
        await page.goto(url, { waitUntil: 'load', timeout: 90000 });
        await page.waitForTimeout(4000); // let hydration, animations, and polling settle

        await page.screenshot({
          path: resolve(OUT_DIR, filename),
          fullPage: false,
        });
        console.log(`OK -> ${filename}`);
        captured++;
      } catch (err) {
        console.log(`FAILED: ${err.message}`);
      }
    }

    await context.close();
  }

  // Sidebar states
  console.log('\n  Capturing sidebar states...');
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    colorScheme: 'dark',
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'load', timeout: 90000 });
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: resolve(OUT_DIR, `sidebar_expanded.png`),
      fullPage: false,
    });
    console.log('    sidebar_expanded.png OK');
    captured++;

    // Collapse sidebar
    const trigger = page.locator('button[data-sidebar="trigger"]').first();
    if (await trigger.isVisible({ timeout: 2000 }).catch(() => false)) {
      await trigger.click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: resolve(OUT_DIR, `sidebar_collapsed.png`),
        fullPage: false,
      });
      console.log('    sidebar_collapsed.png OK');
      captured++;
    } else {
      console.log('    sidebar trigger not found, skipping collapsed state');
    }
  } catch (err) {
    console.log(`    Sidebar capture failed: ${err.message}`);
  }

  await browser.close();
  console.log(`\nDone! ${captured} screenshots saved to ${OUT_DIR}\n`);
}

main().catch((err) => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
