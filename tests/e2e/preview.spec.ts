import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const states = [
  'Design empty',
  'Engineering brief',
  'Plan',
  'Agent running',
  'Agent failed',
  'Validation report',
  'Validation failure',
  'No validation results',
  'Modify mode',
  'Learn mode',
  'Settings',
  'History',
  'Onshape disconnected',
  'No document',
  'Error states',
  'Loading states',
  'Components',
];
for (const [width, theme] of [
  [320, 'dark'],
  [1280, 'light'],
] as const) {
  for (const state of states) {
    test(`mock ${state} is accessible without overflow at ${width}px / ${theme}`, async ({
      page,
    }, testInfo) => {
      await page.setViewportSize({ width, height: 850 });
      await page.goto('http://127.0.0.1:4174/#/lab');
      await expect(page.getByText('Forge UI lab')).toBeVisible();
      await page
        .getByLabel('Layout')
        .selectOption(width === 320 ? 'narrow' : 'wide');
      await page.getByLabel('Theme', { exact: true }).selectOption(theme);
      await page.getByLabel('Preview state').selectOption(state);
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
      // A full-page capture makes below-the-fold actions reviewable as well.
      if (testInfo.project.name === 'chromium')
        await page.screenshot({
          path: `.cache/phase1/${state.replaceAll(' ', '-').toLowerCase()}-${width}-${theme}.png`,
          fullPage: true,
        });
    });
  }
}

test('local preview workflow and stale selection never authorize CAD writes', async ({
  page,
}) => {
  const calls: string[] = [];
  page.on('request', (request) => {
    if (request.resourceType() === 'fetch' || request.resourceType() === 'xhr')
      calls.push(request.url());
  });
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page
    .getByRole('button', {
      name: 'Help me design a belt-driven camera slider.',
    })
    .click();
  await page.getByRole('button', { name: 'Send prompt' }).click();
  await expect(
    page.getByRole('heading', { name: 'Engineering brief', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Review sample plan' }).click();
  await page.getByRole('button', { name: /Approve and Build/ }).click();
  await page.getByRole('button', { name: 'Cancel preview' }).click();
  await expect(
    page.getByText('Preview cancelled. No CAD was changed.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Open sample report' }).click();
  await expect(
    page.locator('.validation-summary .status--unverified'),
  ).toContainText('1 Unverified');
  await page.getByLabel('Preview state').selectOption('Modify mode');
  await page.getByLabel('Preview selection').selectOption('face');
  await page.getByLabel('Modification prompt').fill('Make this 5 mm thicker.');
  await page.getByRole('button', { name: 'Send prompt' }).click();
  await page.getByLabel('Preview selection').selectOption('stale');
  await expect(page.getByRole('button', { name: /Apply/ })).toHaveCount(0);
  await expect(page.getByLabel('Modification prompt')).toBeDisabled();
  expect(calls).toEqual([]);
});

test('Phase 5 synthetic inspector states are accessible at narrow widths', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 320, height: 950 });
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page.getByLabel('Preview state').selectOption('CAD inspector');
  for (const state of [
    'Simple Part Studio',
    'Empty Part Studio',
    'Many features',
    'Suppressed feature',
    'Unknown feature',
    'Partial provider failure',
    'Unavailable mass',
    'Selected FACE',
    'Selected EDGE',
  ]) {
    await page.getByLabel('Inspector state').selectOption(state);
    await expect(
      page.getByText(
        'Synthetic evidence only. No Onshape request or CAD change.',
      ),
    ).toBeVisible();
    if (state === 'Unknown feature') {
      await page
        .locator('summary')
        .filter({ hasText: 'Synthetic custom feature' })
        .click();
      await expect(
        page.getByText('Type not yet interpreted by Forge.'),
      ).toBeVisible();
    }
    if (state === 'Partial provider failure') {
      await expect(page.getByText(/Onshape took too long/)).toBeVisible();
      await expect(page.getByText('Sketch 1', { exact: true })).toBeVisible();
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    if (browserName === 'chromium' && state === 'Simple Part Studio')
      await page.screenshot({
        path: '.cache/phase5/lab-320.png',
        fullPage: true,
      });
  }
});
