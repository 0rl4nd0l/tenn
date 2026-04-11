import { test, expect } from '@playwright/test';

test.describe('Cockpit Offline Resilience', () => {
  test('should show offline indicator when backend returns 503', async ({ page }) => {
    // Mock health check to fail
    await page.route('**/api/cockpit/health', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'unhealthy', message: 'Service Unavailable' }),
      });
    });

    await page.goto('/');

    // The indicator should appear
    const offlineIndicator = page.getByText(/Cockpit Offline/i);
    await expect(offlineIndicator).toBeVisible({ timeout: 15000 });
    
    // Check for general error indicator inside the fixed container
    const container = page.locator('.fixed').filter({ hasText: /Cockpit Offline/i });
    await expect(container.locator('text=/503|Server error/i').first()).toBeVisible();
  });

  test('should show offline indicator on network failure', async ({ page }) => {
    // Mock network failure
    await page.route('**/api/cockpit/health', route => route.abort('failed'));

    await page.goto('/');

    const offlineIndicator = page.getByText(/Cockpit Offline/i);
    await expect(offlineIndicator).toBeVisible({ timeout: 15000 });
  });

  test('should recover when backend becomes healthy again', async ({ page }) => {
    let fail = true;
    
    // First call fails, subsequent calls succeed
    await page.route('**/api/cockpit/health', route => {
      if (fail) {
        fail = false;
        route.fulfill({ status: 503 });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'healthy', services: [] }),
        });
      }
    });

    await page.goto('/');
    
    // Should be offline initially
    await expect(page.getByText(/Cockpit Offline/i)).toBeVisible();
    
    // Trigger another fetch or wait for polling if implemented
    // For this test, we'll just navigate or reload to trigger apiFetch
    await page.reload();
    
    // Should be gone now
    await expect(page.getByText(/Cockpit Offline/i)).not.toBeVisible();
  });
});
