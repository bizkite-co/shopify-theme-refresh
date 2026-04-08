import { test, expect } from '@playwright/test';

const PREVIEW_THEME_ID = '138963943485'; // UAT-on-PROD

test.describe('UAT-on-PROD Theme Preview', () => {
  test('order-address-update page loads in UAT-on-PROD preview', async ({ page }) => {
    // Navigate with preview theme param
    await page.goto(`/pages/order-address-update?preview_theme_id=${PREVIEW_THEME_ID}`);
    
    // Check page loads without error
    await expect(page).not.toHaveTitle(/error|404|Error/i);
    
    // URL should contain the page
    expect(page.url()).toContain('order-address-update');
  });

  test('address update page has form elements in UAT-on-PROD preview', async ({ page }) => {
    await page.goto(`/pages/order-address-update?preview_theme_id=${PREVIEW_THEME_ID}`);
    
    // Look for form or input elements
    const hasForm = await page.locator('form, input, button, [class*="form"], select').count();
    expect(hasForm).toBeGreaterThan(0);
  });

  test('homepage loads in UAT-on-PROD preview', async ({ page }) => {
    await page.goto(`/?preview_theme_id=${PREVIEW_THEME_ID}`);
    
    // Check page loads
    await expect(page).not.toHaveTitle(/error|404|Error/i);
    
    // Body should be visible with content
    const bodyText = await page.locator('body').textContent();
    expect(bodyText?.length).toBeGreaterThan(10);
  });

  test('collections page loads in UAT-on-PROD preview', async ({ page }) => {
    await page.goto(`/collections/all?preview_theme_id=${PREVIEW_THEME_ID}`);
    
    // Page should load
    await expect(page).not.toHaveTitle(/error|404|Error/i);
    await expect(page.locator('body')).toBeVisible();
  });
});