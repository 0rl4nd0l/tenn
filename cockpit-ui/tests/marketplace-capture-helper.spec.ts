import { expect, test } from '@playwright/test'

test.describe('Marketplace capture helper', () => {
  test('disables capture when the helper token is missing', async ({ page }) => {
    await page.goto('/marketplace-capture')

    await expect(page.getByText(/missing a capture token/i)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Capture Marketplace Listing' })).toBeDisabled()
    await expect(page.getByRole('link', { name: 'Return to Cockpit' })).toHaveAttribute('href', '/full-chat')
    await expect(page.locator('a[href="#"]', { hasText: 'Capture Marketplace Listing' })).toHaveCount(0)
  })

  test('renders a javascript bookmarklet when a helper token is present', async ({ page }) => {
    await page.goto('/marketplace-capture?token=token-123&url=https%3A%2F%2Fwww.facebook.com%2Fmarketplace%2Fitem%2Fabc')

    const captureLink = page.getByRole('link', { name: 'Capture Marketplace Listing' })
    await expect(page.getByText(/missing a capture token/i)).toHaveCount(0)
    await expect(captureLink).toHaveAttribute('href', /^javascript:/)
    await expect(page.getByRole('link', { name: 'Open Listing' })).toHaveAttribute(
      'href',
      'https://www.facebook.com/marketplace/item/abc',
    )
  })
})
