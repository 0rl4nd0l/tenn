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

  test('should show Intel Pulse storage levels strip', async ({ page }) => {
    await page.goto('/intel-ops');
    await expect(page.getByText('Storage levels (canonical DB)')).toBeVisible({ timeout: 30000 });
  });
});
