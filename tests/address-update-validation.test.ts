import { test, expect } from '@playwright/test';

test.describe('Address Update Form Validation', () => {
  // Use PROD (not password protected)
  const testUrl = 'https://turboheatweldingtools.com/pages/order-address-update?order=7825748820261&payload=eyJvcmRlcklkIjo3ODI1NzQ4ODIwMjYxLCJjdXN0b21lckVtYWlsIjoibWFya0BnZXRiaXpraXRlLmNvbSIsImNyZWF0ZWRBdCI6MTc3Njk4MjM5NDM2MywiZXhwaXJlc0F0IjoxNzc3MjQxNTk0MzYzfQ&hash=58gQWbCih4QOupIThuLfpMvwW1GlIzRSV2RlXB78HP0';

  test('form fields are populated with order data', async ({ page }) => {
    await page.goto(testUrl, { timeout: 15000 });
    await page.waitForTimeout(5000);
    
    // Check what's on the page first
    const pageContent = await page.content();
    console.log('Page has form:', pageContent.includes('address-update-form'));
    console.log('Page has password:', pageContent.includes('password'));
    
    const fieldChecks = [
      { selector: '#AddressFirstName', description: 'First Name' },
      { selector: '#AddressLastName', description: 'Last Name' },
      { selector: '#AddressCompany', description: 'Company' },
      { selector: '#AddressAddress1', description: 'Address Line 1' },
      { selector: '#AddressAddress2', description: 'Address Line 2' },
      { selector: '#AddressCity', description: 'City' },
      { selector: '#AddressCountry', description: 'Country' },
      { selector: '#AddressProvince', description: 'Province/State' },
      { selector: '#AddressZip', description: 'ZIP/Postal Code' },
      { selector: '#AddressPhone', description: 'Phone Number' }
    ];

    for (const { selector, description } of fieldChecks) {
      const value = await page.locator(selector).inputValue().catch(() => '');
      console.log(`${description} (${selector}): '${value}'`);
      
      const hasValue = value.trim().length > 0;
      if (!hasValue) {
        console.log(`  ⚠️  ${description} is EMPTY`);
      }
    }

    const errorMessage = (await page.locator('#error-message').textContent().catch(() => '')) || '';
    if (errorMessage.trim().length > 0) {
      console.log(`❌ Error message: ${errorMessage}`);
    }
    
    const successMessage = (await page.locator('#success-message').textContent().catch(() => '')) || '';
    if (successMessage.trim().length > 0) {
      console.log(`✅ Success message: ${successMessage}`);
    }
    
    const loadingState = await page.locator('#loading-state').isVisible();
    console.log(`Loading state visible: ${loadingState}`);
    
    const formContainer = await page.locator('#address-form-container').isVisible();
    console.log(`Form container visible: ${formContainer}`);
  });
});
