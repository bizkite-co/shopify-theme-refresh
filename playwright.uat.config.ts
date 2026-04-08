import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    baseURL: 'https://turboship-uat.myshopify.com',
  },
  name: 'UAT',
});