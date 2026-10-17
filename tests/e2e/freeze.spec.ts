import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';
import { authenticatedFixture } from './auth-fixtures';

const output = '.cache/phase6.5-final';
for (const width of [320, 360, 380, 400, 480, 640]) {
  test(`approved Settings, privacy and keyboard controls at ${width}px`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await authenticatedFixture(page);
    await page.addInitScript(() =>
      localStorage.setItem(
        'forge.preferences.v1',
        JSON.stringify({ onboarded: true, theme: 'dark' }),
      ),
    );
    await page.goto('/#/settings');
    await expect(
      page.getByRole('heading', { name: 'Settings', exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText('Development tools', { exact: true }),
    ).toHaveCount(0);
    const pane = page.getByRole('region', { name: 'Workspace content' });
    await pane.focus();
    await expect(pane).toBeFocused();
    await page.keyboard.press('PageDown');
    await page.getByLabel('Dark', { exact: true }).focus();
    await page.getByLabel('Reduce transparency', { exact: true }).check();
    await expect(page.locator('html')).toHaveAttribute(
      'data-transparency',
      'reduced',
    );
    await page.getByLabel('Reduce transparency', { exact: true }).uncheck();
    await page.getByLabel('Bed width (mm)').focus();
    await expect(page.getByLabel('Bed width (mm)')).toBeInViewport();
    expect(
      await pane.evaluate((node) => node.scrollWidth <= node.clientWidth),
    ).toBe(true);
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    if (browserName === 'chromium')
      await page.screenshot({ path: `${output}/settings-fields-${width}.png` });
    await pane.evaluate((node) => {
      node.scrollTop = 0;
    });
    if (browserName === 'chromium') {
      await mkdir(output, { recursive: true });
      await page.screenshot({ path: `${output}/settings-${width}.png` });
    }
    await page.getByRole('button', { name: 'Workspace menu' }).click();
    await expect(
      page.getByRole('menuitem', { name: 'Developer', exact: true }),
    ).toHaveCount(0);
    await page.getByRole('menuitem', { name: 'Privacy', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Your data' })).toContainText(
      'provider retention policies apply',
    );
    await page.keyboard.press('Escape');
    await expect(
      page.getByRole('button', { name: 'Workspace menu' }),
    ).toBeFocused();
  });
}

test('approved material has a readable forced-color fallback and nonsemantic optics', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 400, height: 900 });
  await authenticatedFixture(page);
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.goto('/');
  await expect(page.locator('.glass-definitions')).toHaveAttribute(
    'aria-hidden',
    'true',
  );
  await expect(page.locator('.wordmark .forge-mark')).toHaveAttribute(
    'aria-hidden',
    'true',
  );
  // Chromium implements forced-color emulation; the full cross-engine gate also
  // checks increased contrast and explicit opaque/reduced-motion adaptations.
  if (browserName === 'chromium') {
    await page.emulateMedia({
      forcedColors: 'active',
      reducedMotion: 'reduce',
    });
    expect(
      await page
        .locator('.composer')
        .evaluate((node) => getComputedStyle(node, '::before').backdropFilter),
    ).toBe('none');
    await page.getByLabel('Design prompt').focus();
    await expect(page.getByLabel('Design prompt')).toBeFocused();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.screenshot({ path: `${output}/forced-colors.png` });
  }
});
