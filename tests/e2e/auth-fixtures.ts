import type { Page } from '@playwright/test';

export const signedOut = {
  status: 'signed_out',
  configured: true,
  display_name: null,
  connection: null,
  csrf_token: null,
  verified_at: null,
};
export const signedIn = {
  ...signedOut,
  status: 'authenticated',
  display_name: 'Browser Test Engineer',
  connection: 'connected',
  csrf_token: 'a'.repeat(64),
  verified_at: 1_700_000_000,
};

export async function authenticatedFixture(page: Page) {
  await page.route('**/api/me', (route) => route.fulfill({ json: signedIn }));
}
