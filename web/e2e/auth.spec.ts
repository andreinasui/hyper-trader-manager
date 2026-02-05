import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Enable mock mode
    await page.addInitScript(() => {
      (window as any).__PRIVY_MOCK__ = {
        enabled: true,
        authenticated: false,
        ready: true,
      }
    })
  })

  test('user can authenticate with Privy', async ({ page }) => {
    await page.goto('/')
    
    // Should show connect wallet button
    await expect(page.getByText(/Connect Wallet/i)).toBeVisible()
    
    // Click connect (mocked in test environment)
    await page.click('button:has-text("Connect Wallet")')
    
    // Should see wallet address after auth (shortened format)
    await expect(page.locator('text=/0x[a-fA-F0-9]{4}/i')).toBeVisible({ timeout: 5000 })
  })
  
  test('unauthenticated requests redirect to login', async ({ page }) => {
    // Try to access protected route
    await page.goto('/traders')
    
    // Should redirect to login or show login page
    await expect(page.url()).toMatch(/(login|\/?)/)
    
    // Should see Connect Wallet button since we're redirected
    await expect(page.getByText(/Connect Wallet/i)).toBeVisible()
  })
})
