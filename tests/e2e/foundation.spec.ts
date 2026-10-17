import { expect, test } from '@playwright/test';
import { authenticatedFixture } from './auth-fixtures';
import AxeBuilder from '@axe-core/playwright';

test.beforeEach(async ({ page }) => {
  await authenticatedFixture(page);
});

for (const width of [320, 380, 480, 1280]) {
  test(`workspace modes, settings and focus fit at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 850 });
    await page.goto('/');
    await expect(page).toHaveTitle('Forge — AI engineering inside Onshape');
    await expect(
      page.getByRole('dialog', { name: 'Welcome to Forge' }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Skip introduction' }).click();
    const contextButton = page.getByRole('button', {
      name: 'View CAD context',
    });
    await contextButton.click();
    await expect(
      page.getByRole('dialog', { name: 'Document & selection' }),
    ).toBeVisible();
    await expect(
      page
        .getByRole('dialog', { name: 'Document & selection' })
        .getByText('Not inside Onshape', { exact: true }),
    ).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(contextButton).toBeFocused();
    await expect(page.getByRole('main')).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Forge workspace' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Ask about this Part Studio' }),
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Send prompt' }),
    ).toBeDisabled();
    await page
      .getByRole('button', { name: 'Design a NEMA 17 motor mount.' })
      .click();
    await expect(page.getByLabel('Design prompt')).toBeFocused();
    await expect(page.getByLabel('Design prompt')).toHaveValue(
      'Design a NEMA 17 motor mount.',
    );
    await page.getByLabel('Design prompt').press('Control+Enter');
    await expect(page.getByText('Your local draft')).toBeVisible();
    const designTab = page.getByRole('tab', { name: 'Design', exact: true });
    await designTab.focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: 'Modify' })).toBeFocused();
    await expect(
      page.getByRole('heading', { name: 'Refine with intention.' }),
    ).toBeVisible();
    await expect(page.getByLabel('Modification prompt')).toBeDisabled();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: 'Learn' })).toBeFocused();
    await page.getByRole('radio', { name: /^Beginner/ }).check();
    await page
      .getByRole('radio', { name: 'Learn CAD fundamentals', exact: true })
      .check();
    await page.getByRole('button', { name: 'Review sample lesson' }).click();
    await page.getByRole('button', { name: 'Begin lesson' }).click();
    await expect(
      page.getByText(/Forge isn’t checking the model/),
    ).toBeVisible();
    await page
      .getByRole('button', { name: 'Mark step done', exact: true })
      .click();
    await page.getByRole('button', { name: 'Next step', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Turn the profile into depth' }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Workspace menu' }).click();
    await page.getByRole('menuitem', { name: 'Appearance & settings' }).click();
    await expect(
      page.getByRole('heading', { name: 'Settings', exact: true }),
    ).toBeVisible();
    await page.getByLabel('Dark', { exact: true }).check();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.getByLabel('Bed width (mm)').fill('250');
    await page.getByRole('button', { name: 'Save local profile' }).click();
    await expect(page.getByRole('main').getByRole('status')).toContainText(
      'Profile saved in this browser',
    );
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.reload();
    await expect(page.getByLabel('Bed width (mm)')).toHaveValue('250');
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });
}

test('production excludes the development lab, fixtures and AI/CAD requests', async ({
  page,
}) => {
  const unexpectedRequests: string[] = [];
  page.on('request', (request) => {
    if (
      (request.resourceType() === 'fetch' ||
        request.resourceType() === 'xhr') &&
      !request.url().endsWith('/api/me')
    )
      unexpectedRequests.push(request.url());
  });
  await page.goto('/#/lab');
  await expect(page.getByText('Forge UI lab')).toHaveCount(0);
  // An unknown production hash still offers onboarding and the disconnected workspace.
  await expect(
    page.getByRole('dialog', { name: 'Welcome to Forge' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Skip introduction' }).click();
  await expect(
    page.getByRole('heading', { name: 'Ask about this Part Studio' }),
  ).toBeVisible();
  await expect(
    page.getByRole('link', { name: /development preview|UI development lab/ }),
  ).toHaveCount(0);
  expect(unexpectedRequests).toEqual([]);
  for (const script of await page.locator('script[src]').all()) {
    const src = await script.getAttribute('src');
    const asset = await page.request.get(src!);
    const code = await asset.text();
    for (const marker of [
      'Synthetic preview part',
      'Open joint',
      'Stepped billet',
      'Three planes, one identity',
      'Development-only sanitized diagnostics',
      'forge:open-developer-tools',
      'Synthetic Phase 6.5 review.',
      'Phase 6.5 design system',
      'Bright backdrop stress test',
      'Synthetic custom feature',
      'forge-rest-diagnostic-v1',
      'forge-selection-structure-v1',
      'BTMParameterBoolean-144',
      'Sanitized body response structure',
      'X-Forge-Body-Structure',
      'Sketch 1 is first in the returned feature list.',
    ])
      expect(code).not.toContain(marker);
  }
});

test('dialog traps keyboard focus, closes with Escape and restores the opener', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Skip introduction' }).click();
  const menu = page.getByRole('button', { name: 'Workspace menu' });
  await menu.focus();
  await page.keyboard.press('Enter');
  await page.getByRole('menuitem', { name: 'Introduction' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press('Tab');
    expect(
      await dialog.evaluate((el) => el.contains(document.activeElement)),
    ).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(menu).toBeFocused();
});

test('explicit system theme follows OS preference and reduced motion disables skeleton animation', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
  await page.goto('/');
  await page.getByRole('button', { name: 'Skip introduction' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: 'Workspace menu' }).click();
  await page.getByRole('menuitem', { name: 'Appearance & settings' }).click();
  await page.getByLabel('System', { exact: true }).check();
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page.getByLabel('Preview state').selectOption('Loading states');
  expect(
    await page
      .locator('.skeleton')
      .first()
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe('none');
});

for (const theme of ['light', 'dark']) {
  test(`workspace accessibility in ${theme} mode`, async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Skip introduction' }).click();
    await page.getByRole('button', { name: 'Workspace menu' }).click();
    await page.getByRole('menuitem', { name: 'Appearance & settings' }).click();
    await page
      .getByLabel(theme === 'dark' ? 'Dark' : 'Light', { exact: true })
      .check();
    await page.getByRole('button', { name: /Back to workspace/ }).click();
    for (const mode of ['Design', 'Modify', 'Learn']) {
      await page.getByRole('tab', { name: mode, exact: true }).click();
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
            .analyze()
        ).violations,
      ).toEqual([]);
    }
  });
}
