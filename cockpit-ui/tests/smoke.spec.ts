import { test, expect } from '@playwright/test';

test.describe('Cockpit Smoke Tests', () => {
  test('should load the homepage and show the correct title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Financial Cockpit/);
  });

  test('should render the navigation sidebar', async ({ page }) => {
    await page.goto('/');
    
    // Check for the sidebar. The component uses Sidebar from shadcn/ui.
    // We look for navigation links defined in cockpit-sidebar.tsx
    const navItems = [
      'Chat',
      'Operations',
      'Updater',
      'Verification',
      'History',
      'Settings',
      'Holdings',
      'News',
      'Intel Pulse'
    ];

    for (const label of navItems) {
      const link = page.getByRole('link').filter({ hasText: label });
      await expect(link).toBeVisible();
    }
  });

  test('should navigate to Operations page', async ({ page }) => {
    await page.goto('/');
    
    const operationsLink = page.getByRole('link').filter({ hasText: 'Operations' });
    await expect(operationsLink).toBeVisible();
    await operationsLink.click();
    
    // Use a longer timeout for navigation URL check
    await expect(page).toHaveURL(/\/operations/, { timeout: 30000 });
  });

  test('should show Intel Pulse storage levels or no-data indicator', async ({ page }) => {
    await page.goto('/intel-ops');
    
    // Check for either the storage levels (if backend up) or the NO_DATA placeholder (if down)
    await expect(async () => {
      const hasData = await page.getByText('Storage levels (canonical DB)').isVisible();
      const hasNoData = await page.getByText('[ NO_DATA_AVAILABLE ]').isVisible();
      expect(hasData || hasNoData).toBeTruthy();
    }).toPass({ timeout: 20000 });
  });
});
