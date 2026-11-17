import { test, expect, type Page } from '@playwright/test';

function sidebarNavLink(page: Page, label: string) {
  return page.locator('a[data-sidebar="menu-button"]').filter({ hasText: label });
}

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
      const link = sidebarNavLink(page, label);
      await expect(link).toBeVisible();
    }
  });

  test('should navigate to Operations page', async ({ page }) => {
    await page.goto('/');
    
    const operationsLink = sidebarNavLink(page, 'Operations');
    await expect(operationsLink).toBeVisible();
    await operationsLink.click();
    
    await expect(page).toHaveURL(/\/operations/, { timeout: 30000 });
    await expect(page.getByTestId('operations-ready')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('operations-ready')).toHaveAttribute('data-operations-ready', 'true');
  });

  test('should show Intel Pulse storage levels or no-data indicator', async ({ page }) => {
    await page.goto('/intel-ops');
    
    // Check for either storage data, explicit no-data state, or global offline banner.
    await expect(async () => {
      const hasData = await page.getByText('Storage levels (canonical DB)').isVisible();
      const hasNoData = await page.getByText(/NO_DATA_AVAILABLE/i).isVisible();
      const hasOffline = await page.getByText(/Cockpit Offline/i).isVisible();
      expect(hasData || hasNoData || hasOffline).toBeTruthy();
    }).toPass({ timeout: 20000 });
  });
});
