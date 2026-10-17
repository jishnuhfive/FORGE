import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn, signedOut } from './auth-fixtures';

test('sign in, account verification, disconnect, reconnect, and logout', async ({
  page,
}) => {
  let authenticated = false;
  let connection = 'connected';
  await page.route('**/api/me', (route) =>
    route.fulfill({
      json: authenticated ? { ...signedIn, connection } : signedOut,
    }),
  );
  // Browser fixture presents synthetic consent. Backend tests verify real 303s.
  await page.route('**/auth/onshape/start', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: '<title>Synthetic Onshape fixture</title><a href="/auth/onshape/callback?code=synthetic-code&state=synthetic-state">Authorize Forge test</a>',
    }),
  );
  await page.route('**/auth/onshape/callback?*', (route) => {
    authenticated = true;
    connection = 'connected';
    return route.fulfill({
      contentType: 'text/html',
      body: '<script>location.replace("/")</script>',
    });
  });
  for (const action of ['check', 'disconnect']) {
    await page.route(`**/api/onshape/${action}`, async (route) => {
      expect(route.request().method()).toBe('POST');
      expect(route.request().headers()['x-csrf-token']).toBe(
        signedIn.csrf_token,
      );
      if (action === 'disconnect') connection = 'disconnected';
      await route.fulfill({ status: 204 });
    });
  }
  await page.route('**/auth/logout', (route) => {
    expect(route.request().method()).toBe('POST');
    expect(route.request().headers()['x-csrf-token']).toBe(signedIn.csrf_token);
    authenticated = false;
    return route.fulfill({ status: 204 });
  });
  await page.setViewportSize({ width: 320, height: 850 });
  await page.goto('/');
  await page.getByRole('link', { name: 'Continue with Onshape' }).click();
  await page.getByRole('link', { name: 'Authorize Forge test' }).click();
  await page.getByRole('button', { name: 'Skip introduction' }).click();
  await expect(page.getByLabel('Design prompt')).toBeVisible();
  await expect(page).toHaveURL('http://127.0.0.1:4173/');
  await page.getByRole('button', { name: 'Workspace menu' }).click();
  await page.getByRole('menuitem', { name: 'Appearance & settings' }).click();
  await page.getByRole('button', { name: 'Check connection' }).click();
  await expect(
    page.getByText('Onshape verified your connection.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Disconnect Onshape' }).click();
  await expect(page.getByRole('dialog')).toContainText('does not revoke');
  await page.getByRole('button', { name: 'Confirm disconnect' }).click();
  await expect(page.getByText('Reconnect required')).toBeVisible();
  await page.getByRole('link', { name: 'Reconnect Onshape' }).click();
  await page.getByRole('link', { name: 'Authorize Forge test' }).click();
  await page.getByRole('button', { name: 'Workspace menu' }).click();
  await page.getByRole('menuitem', { name: 'Appearance & settings' }).click();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(
    page.getByRole('link', { name: 'Continue with Onshape' }),
  ).toBeVisible();
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(
    signedIn.csrf_token,
  );
});

for (const state of [
  'authorization_denied',
  'authorization_error',
  'invalid_state',
  'session_expired',
  'network_error',
]) {
  test(`recoverable ${state} state`, async ({ page }) => {
    await page.route('**/api/me', (route) =>
      state === 'network_error'
        ? route.abort()
        : route.fulfill({
            json: {
              ...signedOut,
              status: state === 'session_expired' ? state : 'signed_out',
            },
          }),
    );
    await page.goto(`/#/auth/${state}`);
    if (state === 'network_error')
      await expect(
        page.getByRole('button', { name: 'Try again' }),
      ).toBeVisible();
    else
      await expect(
        page.getByRole('link', { name: 'Continue with Onshape' }),
      ).toBeVisible();
    await expect(page.getByLabel('Design prompt')).toHaveCount(0);
  });
}

for (const theme of ['light', 'dark']) {
  test(`sign-in accessibility and narrow layout in ${theme}`, async ({
    page,
  }) => {
    await page.emulateMedia({
      colorScheme: theme === 'dark' ? 'dark' : 'light',
    });
    await page.setViewportSize({ width: 320, height: 850 });
    await page.route('**/api/me', (route) =>
      route.fulfill({ json: signedOut }),
    );
    await page.goto('/');
    await expect(
      page.getByRole('link', { name: 'Continue with Onshape' }),
    ).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if (test.info().project.name === 'chromium')
      await page.screenshot({
        path: `.cache/phase2/signin-${theme}.png`,
        fullPage: true,
      });
  });
}
