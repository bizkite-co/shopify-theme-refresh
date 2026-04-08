import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    baseURL: 'https://turbo-heat-welding-tools.myshopify.com',
  },
  name: 'PROD',
});