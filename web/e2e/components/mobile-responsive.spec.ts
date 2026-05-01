/**
 * Mobile-responsive primitive integration tests.
 *
 * Verifies that the Phase 3 primitives (<PageActions>, <ResponsiveTable>,
 * <KpiStrip>, <FormGrid>) and the existing Sidebar drawer behave correctly
 * at mobile viewport widths.
 *
 * Mobile-project only — see playwright.config.ts.
 */

import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../fixtures/api-handlers.js';
import { setupAuthenticatedState } from '../utils/auth-helpers.js';

test.describe('Mobile Responsive Primitives', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile-only suite');
    await setupApiMocks(page);
  });

  test.describe('Sidebar mobile drawer', () => {
    test('should show mobile drawer and hide desktop sidebar', async ({ page }) => {
      await setupAuthenticatedState(page);
      await page.goto('/traders');
      await page.waitForLoadState('networkidle');

      // Desktop sidebar should be hidden at mobile viewport
      const desktopSidebar = page.locator('aside.hidden.lg\\:flex');
      await expect(desktopSidebar).toBeHidden();

      // Mobile trigger button should be visible
      const mobileTrigger = page.locator('[data-mobile-sidebar-trigger]');
      await expect(mobileTrigger).toBeVisible();

      // Click trigger to open drawer
      await mobileTrigger.click();

      // Drawer aside should be visible with navigation content
      const mobileDrawer = page.locator('[data-mobile-sidebar]');
      await expect(mobileDrawer.getByText('HyperTrader')).toBeVisible();
      await expect(mobileDrawer.getByRole('link', { name: 'Traders' })).toBeVisible();
      await expect(mobileDrawer.getByRole('link', { name: 'Settings' })).toBeVisible();

      // Backdrop should be visible
      const backdrop = page.locator('[data-mobile-sidebar-backdrop]');
      await expect(backdrop).toBeVisible();

      // Click backdrop to close
      await backdrop.click();

      // Backdrop should disappear (removed from DOM via <Show>)
      await expect(backdrop).toBeHidden();
    });
  });

  test.describe('PageActions overflow', () => {
    test('should collapse secondary actions into overflow menu on trader detail', async ({ page }) => {
      await setupAuthenticatedState(page);
      await page.goto('/traders/test-trader-id');
      await page.waitForLoadState('networkidle');

      // Primary actions should be visible
      const primaryActions = page.locator('[data-page-actions-inline]');
      await expect(primaryActions).toBeVisible();

      // Secondary actions inline should be hidden on mobile
      const secondaryInline = page.locator('[data-page-actions-secondary-inline]');
      await expect(secondaryInline).toBeHidden();

      // Overflow trigger should be visible
      const overflowTrigger = page.locator('[data-page-actions-overflow]');
      await expect(overflowTrigger).toBeVisible();

      // Click overflow trigger
      const overflowButton = overflowTrigger.locator('button');
      await overflowButton.click();

      // Dropdown menu items should appear (Kobalte portals to body)
      // For a running trader, we expect at least Restart and Delete
      await expect(page.getByRole('menuitem', { name: 'Restart' })).toBeVisible();
      await expect(page.getByRole('menuitem', { name: 'Delete' })).toBeVisible();
    });
  });

  test.describe('ResponsiveTable card mode', () => {
    test('should show phone card layout and hide desktop table on /traders', async ({ page }) => {
      await setupAuthenticatedState(page);
      await page.goto('/traders');
      await page.waitForLoadState('networkidle');

      // Desktop header should be hidden
      const tableHeader = page.locator('[data-rt-header]');
      await expect(tableHeader).toBeHidden();

      // At least one row should exist (mockTrader is provided)
      const rows = page.locator('[data-rt-row]');
      await expect(rows.first()).toBeVisible();

      // First row: desktop variant hidden, phone variant visible
      const firstRow = rows.first();
      const desktopRow = firstRow.locator('[data-rt-row-desktop]');
      const phoneRow = firstRow.locator('[data-rt-row-phone]');

      await expect(desktopRow).toBeHidden();
      await expect(phoneRow).toBeVisible();

      // Trader name should be visible in phone card
      await expect(phoneRow.getByText('Test Trader')).toBeVisible();
    });
  });

  test.describe('KpiStrip 2×2 wrap', () => {
    test('should wrap KPI cards into 2×2 grid on phone', async ({ page }) => {
      await setupAuthenticatedState(page);
      await page.goto('/traders');
      await page.waitForLoadState('networkidle');

      // Locate the four KPI cards by walking up from each label to the parent <KpiCard>.
      // `..` selects the immediate XPath parent; KpiCard renders the label as a direct child.
      const totalKpi = page.getByText('Total').locator('..');
      const runningKpi = page.getByText('Running').locator('..');
      const stoppedKpi = page.getByText('Stopped').locator('..');
      const failedKpi = page.getByText('Failed').locator('..');

      // All four should be visible
      await expect(totalKpi).toBeVisible();
      await expect(runningKpi).toBeVisible();
      await expect(stoppedKpi).toBeVisible();
      await expect(failedKpi).toBeVisible();

      // Get bounding boxes
      const firstBox = await totalKpi.boundingBox();
      const thirdBox = await stoppedKpi.boundingBox();

      // The third KPI should be on a new row (its y > first's y + height)
      expect(firstBox).not.toBeNull();
      expect(thirdBox).not.toBeNull();
      expect(thirdBox!.y).toBeGreaterThan(firstBox!.y + firstBox!.height);
    });
  });

  test.describe('FormGrid stacking', () => {
    test('should stack form fields vertically on /traders/new', async ({ page }) => {
      await setupAuthenticatedState(page);
      await page.goto('/traders/new');
      await page.waitForLoadState('networkidle');

      // Locate first FormGrid (Name + Description row)
      const formGrid = page.locator('[data-form-grid]').first();
      await expect(formGrid).toBeVisible();

      // Get first two children (form field containers)
      const children = formGrid.locator('> *');
      const count = await children.count();
      expect(count).toBeGreaterThanOrEqual(2);

      const firstChild = children.nth(0);
      const secondChild = children.nth(1);

      const firstBox = await firstChild.boundingBox();
      const secondBox = await secondChild.boundingBox();

      // On mobile, second child should be stacked below first (its y > first's y + height)
      expect(firstBox).not.toBeNull();
      expect(secondBox).not.toBeNull();
      expect(secondBox!.y).toBeGreaterThan(firstBox!.y + firstBox!.height);
    });
  });
});
