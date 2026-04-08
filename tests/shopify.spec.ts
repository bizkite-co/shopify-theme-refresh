import { test, expect } from '@playwright/test';

test.describe('Address Update Page', () => {
  test('order-address-update page loads correctly', async ({ page }) => {
    await page.goto('/pages/order-address-update');
    
    // Skip if password protected (common for dev stores)
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Check page loads without error (title may be store name)
    await expect(page).not.toHaveTitle(/error|404|Error/i);
    
    // Check URL contains the page handle
    expect(page.url()).toMatch(/order-address-update|password/);
  });

  test('address update page has form elements', async ({ page }) => {
    await page.goto('/pages/order-address-update');
    
    // Skip if password protected
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Look for form or input elements
    const hasForm = await page.locator('form, input, button, [class*="form"]').count();
    expect(hasForm).toBeGreaterThan(0);
  });
});

test.describe('Homepage', () => {
  test('homepage loads successfully', async ({ page }) => {
    await page.goto('/');
    
    // Skip if password protected
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Check page loads - not an error page
    await expect(page).not.toHaveTitle(/error|404|Error/i);
    
    // Check page content loads (any visible content)
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('homepage has content', async ({ page }) => {
    await page.goto('/');
    
    // Skip if password protected
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Look for any content - body should have text or elements
    const bodyText = await page.locator('body').textContent();
    expect(bodyText?.length).toBeGreaterThan(10);
  });
});

test.describe('Navigation', () => {
  test('cart page loads', async ({ page }) => {
    await page.goto('/cart');
    
    // Skip if password protected
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Cart should load (may be empty or have items)
    await expect(page).not.toHaveTitle(/error|404/i);
    
    // Body should be visible
    await expect(page.locator('body')).toBeVisible();
  });

  test('collections page loads', async ({ page }) => {
    await page.goto('/collections/all');
    
    // Skip if password protected
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Page should load without errors
    await expect(page).not.toHaveTitle(/error|404/i);
    
    // Body should be visible
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Theme Preview', () => {
  test('preview theme param works', async ({ page }) => {
    // This tests the preview theme functionality
    const previewUrl = '/?preview_theme_id=138963943485';
    await page.goto(previewUrl);
    
    // Skip if password protected
    if (page.url().includes('/password')) {
      console.log('Store is password protected - skipping');
      test.skip();
    }
    
    // Page should load without errors
    await expect(page).not.toHaveTitle(/error|404/i);
  });
});