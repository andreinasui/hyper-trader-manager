import { test, expect } from '@playwright/test'
import { setupApiMocks } from './fixtures/api-handlers.js'
import { setupUnauthenticatedState, setupAuthenticatedState } from './utils/auth-helpers.js'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page)
  })

  test('user can login with username and password', async ({ page }) => {
    await setupUnauthenticatedState(page)
    await page.goto('/')
    
    // Should show login form
    await expect(page.getByLabel('Username')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    
    // Fill in credentials
    await page.getByLabel('Username').fill('admin')
    await page.getByLabel('Password').fill('password123')
    
    // Submit
    await page.getByRole('button', { name: 'Sign In' }).click()
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/)
  })
  
  test('unauthenticated requests redirect to login', async ({ page }) => {
    await setupUnauthenticatedState(page)
    
    // Try to access protected route
    await page.goto('/dashboard')
    
    // Should redirect to login page
    await expect(page).toHaveURL('/')
    
    // Should see login form
    await expect(page.getByLabel('Username')).toBeVisible()
  })

  test('authenticated user can access dashboard', async ({ page }) => {
    await setupAuthenticatedState(page)
    await page.goto('/dashboard')
    
    // Should stay on dashboard
    await expect(page).toHaveURL(/\/dashboard/)
  })
})
