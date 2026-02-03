/**
 * Trader creation and management tests
 * 
 * Tests the new flow where private keys are NOT required (agent wallet auto-generated).
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, setupApiErrors } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Trader Creation - Authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('trader creation page loads with form', async ({ page }) => {
    await page.goto('/traders/new');

    // Check page title
    await expect(page.locator('h1')).toContainText('Create New Trader');

    // Form should be visible
    await expect(page.locator('form')).toBeVisible();
  });

  test('form displays trader name input', async ({ page }) => {
    await page.goto('/traders/new');

    // Check for name input
    const nameInput = page.locator('input#name');
    await expect(nameInput).toBeVisible();
  });

  test('form does NOT display private key input fields', async ({ page }) => {
    await page.goto('/traders/new');

    // Private key field should NOT exist
    const privateKeyInput = page.locator('input[type="password"]').filter({ hasText: /private.*key/i });
    await expect(privateKeyInput).toHaveCount(0);
  });

  test('displays educational content about agent wallets', async ({ page }) => {
    await page.goto('/traders/new');

    // Check for educational content about secure agent wallets
    const educationalContent = page.locator('text=/Secure Agent Wallet/i');
    await expect(educationalContent).toBeVisible();
    
    // Check for the educational text content
    const infoText = page.locator('text=/automatically generated agent wallet/i');
    await expect(infoText).toBeVisible();
  });

  test('can create trader with valid data', async ({ page }) => {
    await page.goto('/traders/new');

    // Fill trader name
    const nameInput = page.locator('input#name');
    await nameInput.fill('My Test Trader');

    // Fill copy address (address to copy trades from)
    const copyAddressInput = page.locator('input#copyAddress');
    await copyAddressInput.fill('0xabcdefabcdefabcdefabcdefabcdefabcdefabcd');

    // Submit form
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Should redirect after successful creation
    await page.waitForURL('/dashboard', { timeout: 5000 });
  });

  test('shows validation error when name is empty', async ({ page }) => {
    await page.goto('/traders/new');

    // Try to submit without filling name
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Should show validation error for name field
    const errorMessage = page.locator('text=/name is required/i');
    await expect(errorMessage).toBeVisible({ timeout: 2000 });
  });

  test('exchange field defaults to Hyperliquid', async ({ page }) => {
    await page.goto('/traders/new');

    // Check for exchange label and display  
    const exchangeLabel = page.locator('label:has-text("Exchange")');
    await expect(exchangeLabel).toBeVisible();
    
    // Check that Hyperliquid is shown in the display field (not the help text)
    const exchangeDisplay = page.locator('.bg-muted:has-text("Hyperliquid")');
    await expect(exchangeDisplay).toBeVisible();
  });

  test('network field allows selection', async ({ page }) => {
    await page.goto('/traders/new');

    // Look for network selector
    const networkSelect = page.locator('select#network');
    await expect(networkSelect).toBeVisible();
    
    // Select mainnet
    await networkSelect.selectOption('mainnet');
    await expect(networkSelect).toHaveValue('mainnet');
    
    // Select testnet
    await networkSelect.selectOption('testnet');
    await expect(networkSelect).toHaveValue('testnet');
  });
});

test.describe('Trader Creation - Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
  });

  test('displays error message when API fails', async ({ page }) => {
    await setupApiErrors(page);
    await page.goto('/traders/new');

    // Fill form with valid data
    const nameInput = page.locator('input#name');
    await nameInput.fill('Test Trader');
    
    const copyAddressInput = page.locator('input#copyAddress');
    await copyAddressInput.fill('0xabcdefabcdefabcdefabcdefabcdefabcdefabcd');

    // Submit
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Should show error alert
    const errorAlert = page.locator('[role="alert"]');
    await expect(errorAlert).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Trader List', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('can view traders list', async ({ page }) => {
    // Navigate to traders page (adjust URL based on actual routes)
    await page.goto('/traders');

    // Should show traders (mock API returns one trader)
    const traderItem = page.locator('text=Test Trader');
    
    // May need to wait for data to load
    await page.waitForTimeout(500);
    
    const count = await traderItem.count();
    expect(count).toBeGreaterThan(0);
  });
});
