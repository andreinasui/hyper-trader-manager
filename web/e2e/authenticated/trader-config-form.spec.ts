/**
 * E2E tests for Trader Config Form
 * 
 * Tests both create and edit flows for the TraderConfigForm component.
 * 
 * NOTE: These tests currently skip due to authentication mocking issues.
 * The form component itself is tested via unit tests.
 * These E2E tests serve as documentation for desired behavior.
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Trader Config Form - Create Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
    await page.goto('/traders/new');
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
  });

  test('shows all required form sections', async ({ page }) => {
    // Wait for the page title to appear first
    await expect(page.getByRole('heading', { name: 'New trader' })).toBeVisible();
    
    // Check Account Settings card title
    await expect(page.getByText('Account Settings')).toBeVisible();
    
    // Check network selector
    const networkSelect = page.getByLabel('Network');
    await expect(networkSelect).toBeVisible();
    
    // Check copy account field
    const copyAccountInput = page.getByLabel('Copy Account Address');
    await expect(copyAccountInput).toBeVisible();
  });

  test('validates copy account address format', async ({ page }) => {
    // Wait for form to be ready
    await expect(page.getByText('Account Settings')).toBeVisible();
    
    // Fill with invalid address (too short)
    const copyAccountInput = page.getByLabel('Copy Account Address');
    await copyAccountInput.fill('0x123');
    
    // Fill other required fields
    await page.getByLabel('Wallet Address').fill('0x1234567890123456789012345678901234567890');
    await page.getByLabel('Private Key').fill('0x1234567890123456789012345678901234567890123456789012345678901234');
    
    // Try to submit
    await page.getByRole('button', { name: 'Create Trader' }).click();
    
    // Should see validation error (might be inline or in alert)
    await expect(page.locator('text=/invalid|must|error/i').first()).toBeVisible({ timeout: 3000 });
  });

  test('network selector works', async ({ page }) => {
    // Wait for form to be ready
    await expect(page.getByText('Account Settings')).toBeVisible();
    
    const networkSelect = page.getByLabel('Network');
    
    // Should default to mainnet
    await expect(networkSelect).toHaveValue('mainnet');
    
    // Change to testnet
    await networkSelect.selectOption('testnet');
    
    // Verify value changed
    await expect(networkSelect).toHaveValue('testnet');
  });

  test('strategy type selector works', async ({ page }) => {
    // Wait for form to be ready
    await expect(page.getByText('Account Settings')).toBeVisible();

    // Expand Advanced Settings collapsible to reveal Strategy Type
    await page.getByRole('button', { name: 'Advanced Settings' }).click();
    
    const strategySelect = page.getByLabel('Strategy Type');
    
    // Should default to order_based
    await expect(strategySelect).toHaveValue('order_based');
    
    // Change to position_based
    await strategySelect.selectOption('position_based');
    
    // Verify value changed
    await expect(strategySelect).toHaveValue('position_based');
  });
});

test.describe('Trader Config Form - Edit Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('loads existing config in edit mode', async ({ page }) => {
    // Navigate to trader detail page
    await page.goto('/traders/test-trader-id');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Test Trader' })).toBeVisible({ timeout: 10000 });
    
    // Navigate to Configuration tab
    const configTab = page.locator('button[role="tab"]').filter({ hasText: 'Configuration' });
    await configTab.click();
    
    // Wait for config form to load
    await expect(page.locator('text=Account Settings')).toBeVisible({ timeout: 5000 });
    
    // Check that existing values are loaded
    const copyAccountInput = page.locator('input#copy_account');
    await expect(copyAccountInput).toHaveValue('0xabcdefabcdefabcdefabcdefabcdefabcdefabcd');
    
    // Wallet address and private key fields should NOT be visible in edit mode
    await expect(page.locator('input#wallet_address')).not.toBeVisible();
    await expect(page.locator('input#private_key')).not.toBeVisible();
  });

  test('can save config changes', async ({ page }) => {
    // Set up mock for config update endpoint
    await page.route('**/api/v1/traders/test-trader-id/config', async (route) => {
      if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 200,
          json: {
            id: 'test-trader-id',
            latest_config: route.request().postDataJSON(),
            updated_at: new Date().toISOString(),
          },
        });
      } else {
        await route.continue();
      }
    });
    
    // Navigate to trader detail page
    await page.goto('/traders/test-trader-id');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Test Trader' })).toBeVisible({ timeout: 10000 });
    
    // Navigate to Configuration tab
    const configTab = page.locator('button[role="tab"]').filter({ hasText: 'Configuration' });
    await configTab.click();
    
    // Wait for config form to load
    await expect(page.locator('text=Account Settings')).toBeVisible({ timeout: 5000 });
    
    // Click save
    const saveButton = page.locator('button[type="submit"]').filter({ hasText: /save/i });
    await saveButton.click();
    
    // Wait for success toast
    await expect(page.locator('text=/saved/i')).toBeVisible({ timeout: 3000 });
  });
});

test.describe('Trader Config Form - Advanced Settings', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
    await page.goto('/traders/new');
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Account Settings')).toBeVisible();
  });

  test('can expand advanced settings', async ({ page }) => {
    // Advanced settings should be collapsed by default - Risk Parameters should not be visible
    await expect(page.getByText('Risk Parameters', { exact: true })).not.toBeVisible();
    
    // Click to expand Advanced Settings
    const advancedSettingsButton = page.locator('button').filter({ hasText: 'Advanced Settings' });
    await advancedSettingsButton.click();
    
    // Advanced settings should now be visible
    await expect(page.getByText('Risk Parameters', { exact: true })).toBeVisible();
  });

  test('blocked assets tag input works', async ({ page }) => {
    // Expand advanced settings
    const advancedSettingsButton = page.locator('button').filter({ hasText: 'Advanced Settings' });
    await advancedSettingsButton.click();
    
    // Wait for advanced settings to be visible
    await expect(page.getByText('Risk Parameters', { exact: true })).toBeVisible();
    
    // Find the blocked assets section by its label
    const blockedAssetsLabel = page.getByText('Blocked Assets', { exact: true });
    await expect(blockedAssetsLabel).toBeVisible();
    
    // Find the tag input field for blocked assets using the label structure
    // The TagInput is a sibling of the label within the container
    const blockedAssetsContainer = page.locator('div:has(> label:text-is("Blocked Assets"))');
    const tagInput = blockedAssetsContainer.locator('input[type="text"]');
    
    // Add BTC tag
    await tagInput.fill('BTC');
    await tagInput.press('Enter');
    
    // Wait for the tag to appear
    await page.waitForTimeout(300);
    
    // Verify BTC tag appears (tags are converted to uppercase)
    // The tag is rendered in a div with the badge-like styling inside the container
    const btcTag = blockedAssetsContainer.getByText('BTC', { exact: true });
    await expect(btcTag).toBeVisible();
  });
});
