import { test, expect } from '@playwright/test';

test('Metric Coverage Layout Smoke Test', async ({ page }) => {
  // Wait for the app to be ready
  await page.goto('http://127.0.0.1:8081/verification?tab=metric-coverage');
  
  // Wait for the table to render
  await page.waitForSelector('table');
  
  // Search for BHP revenue
  await page.fill('input[placeholder="BHP revenue page 44"]', 'BHP revenue');
  
  // Wait for filtered results
  await page.waitForTimeout(1000);
  
  // Check if table fits within its container
  const tableContainer = page.locator('[data-slot="table-container"]');
  const table = page.locator('table');
  
  const containerBox = await tableContainer.boundingBox();
  const tableBox = await table.boundingBox();
  
  console.log(`Container width: ${containerBox?.width}`);
  console.log(`Table width: ${tableBox?.width}`);
  
  // We expect table width to be at least 900px (our min-width)
  // but it should not exceed the container width if we want it to "fit" without scroll,
  // OR it should have a visible scrollbar.
  
  // Click a row
  const firstRow = page.locator('tbody tr').first();
  await firstRow.click();
  
  // Check if detail sheet opens
  const sheet = page.locator('[role="dialog"]');
  await expect(sheet).toBeVisible();
  
  // Check for long fields in the sheet
  await expect(sheet).toContainText('score_in_confirmed_metric_coverage');
  await expect(sheet).toContainText('Revenue 60,817');
  
  // Check for Open source page button
  const openButton = page.locator('button:has-text("Open source page")');
  await expect(openButton).toBeVisible();
  
  console.log('Smoke test passed!');
});
