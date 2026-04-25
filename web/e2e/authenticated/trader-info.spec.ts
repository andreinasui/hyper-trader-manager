/**
 * Trader Info - Name/Description Editing E2E tests
 * 
 * Tests editing trader name and description in the detail view.
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks, mockTrader } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Trader Info - Name/Description Editing', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedState(page);
    await setupApiMocks(page);
  });

  test('displays trader name and description in detail view', async ({ page }) => {
    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Check that the Overview tab is selected by default
    const overviewTab = page.locator('[role="tab"][aria-selected="true"]', { hasText: 'Overview' });
    await expect(overviewTab).toBeVisible();
  });

  test('can edit trader name', async ({ page }) => {
    const updatedName = 'Updated Trader Name';
    let updateCalled = false;

    // Mock the PATCH /api/v1/traders/{id} endpoint (add AFTER setupApiMocks)
    // Use unroute + route to override, or just handle PATCH separately
    await page.route(`**/api/v1/traders/${mockTrader.id}`, async (route) => {
      const method = route.request().method();
      
      if (method === 'PATCH') {
        const body = route.request().postDataJSON();
        
        // Verify the request contains the updated name
        expect(body.name).toBe(updatedName);
        updateCalled = true;

        await route.fulfill({
          status: 200,
          json: {
            ...mockTrader,
            name: updatedName,
            display_name: updatedName,
            updated_at: new Date().toISOString(),
          },
        });
        return;
      }
      
      // For GET requests, return the mock trader
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          json: mockTrader,
        });
        return;
      }
      
      await route.continue();
    });

    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Find and fill the name input
    const nameInput = page.locator('input[type="text"]').first();
    await nameInput.clear();
    await nameInput.fill(updatedName);

    // Save button should appear after edit
    const saveButton = page.locator('button:has-text("Save")');
    await expect(saveButton).toBeVisible();

    // Click save button
    await saveButton.click();

    // Wait for the update to complete
    await page.waitForTimeout(500);

    // Verify the API was called
    expect(updateCalled).toBe(true);
  });

  test('shows display_name in traders list', async ({ page }) => {
    // Navigate to traders list
    await page.goto('/traders');
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: 'Traders' })).toBeVisible();

    // Check that display_name is shown in the table
    const displayName = page.locator('td').filter({ hasText: mockTrader.display_name });
    await expect(displayName).toBeVisible();
  });

  test('validates name length', async ({ page }) => {
    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Find the name input
    const nameInput = page.locator('input[type="text"]').first();

    // Try to fill with a name that's too long (>50 chars)
    const tooLongName = 'A'.repeat(51);
    await nameInput.clear();
    await nameInput.fill(tooLongName);

    // Check that input has maxLength attribute that prevents too-long input
    const maxLength = await nameInput.getAttribute('maxLength');
    expect(maxLength).toBe('50');

    // Verify that only 50 characters were actually entered
    const actualValue = await nameInput.inputValue();
    expect(actualValue.length).toBeLessThanOrEqual(50);
  });

  test('can edit trader description', async ({ page }) => {
    const updatedDescription = 'This is an updated description for testing';
    let updateCalled = false;

    // Mock the trader endpoint - handle both GET and PATCH
    await page.route(`**/api/v1/traders/${mockTrader.id}`, async (route) => {
      const method = route.request().method();
      
      if (method === 'PATCH') {
        const body = route.request().postDataJSON();
        
        // Verify the request contains the updated description
        expect(body.description).toBe(updatedDescription);
        updateCalled = true;

        await route.fulfill({
          status: 200,
          json: {
            ...mockTrader,
            description: updatedDescription,
            updated_at: new Date().toISOString(),
          },
        });
        return;
      }
      
      // For GET requests, return the mock trader
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          json: mockTrader,
        });
        return;
      }
      
      await route.continue();
    });

    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Find and fill the description textarea
    const descriptionInput = page.locator('textarea');
    await descriptionInput.clear();
    await descriptionInput.fill(updatedDescription);

    // Save button should appear after edit
    const saveButton = page.locator('button:has-text("Save")');
    await expect(saveButton).toBeVisible();

    // Click save button
    await saveButton.click();

    // Wait for the update to complete
    await page.waitForTimeout(500);

    // Verify the API was called
    expect(updateCalled).toBe(true);
  });

  test('shows save button only when changes are made', async ({ page }) => {
    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Save button should NOT be visible initially
    const saveButton = page.locator('button:has-text("Save")');
    await expect(saveButton).not.toBeVisible();

    // Edit the name
    const nameInput = page.locator('input[type="text"]').first();
    await nameInput.clear();
    await nameInput.fill('Modified Name');

    // Now save button should be visible
    await expect(saveButton).toBeVisible();
  });

  test('displays error message when update fails', async ({ page }) => {
    // Mock the trader endpoint - handle both GET and PATCH (with error)
    await page.route(`**/api/v1/traders/${mockTrader.id}`, async (route) => {
      const method = route.request().method();
      
      if (method === 'PATCH') {
        await route.fulfill({
          status: 400,
          json: {
            detail: 'Failed to update trader info',
          },
        });
        return;
      }
      
      // For GET requests, return the mock trader
      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          json: mockTrader,
        });
        return;
      }
      
      await route.continue();
    });

    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Edit the name
    const nameInput = page.locator('input[type="text"]').first();
    await nameInput.clear();
    await nameInput.fill('Modified Name');

    // Click save button
    const saveButton = page.locator('button:has-text("Save")');
    await saveButton.click();

    // Error message should be displayed
    const errorMessage = page.locator('text=/Failed to update trader info/i');
    await expect(errorMessage).toBeVisible({ timeout: 2000 });
  });

  test('validates description length', async ({ page }) => {
    // Navigate to trader detail page
    await page.goto(`/traders/${mockTrader.id}`);
    await page.waitForLoadState('networkidle');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: mockTrader.display_name })).toBeVisible();

    // Find the description textarea
    const descriptionInput = page.locator('textarea');

    // Check that textarea has maxLength attribute
    const maxLength = await descriptionInput.getAttribute('maxLength');
    expect(maxLength).toBe('255');

    // Try to fill with a description that's too long (>255 chars)
    const tooLongDescription = 'A'.repeat(256);
    await descriptionInput.clear();
    await descriptionInput.fill(tooLongDescription);

    // Verify that only 255 characters were actually entered
    const actualValue = await descriptionInput.inputValue();
    expect(actualValue.length).toBeLessThanOrEqual(255);
  });
});
