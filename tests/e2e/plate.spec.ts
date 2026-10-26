import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { authenticatedFixture } from './auth-fixtures';

// The mode switcher tucks away while the pane is scrolled and eases its colours on
// change; audit it in view and at rest.
async function settleNav(page: Page) {
  for (const frame of page.frames())
    await frame
      .evaluate(() => {
        const pane = document.querySelector('.workspace-pane');
        if (pane) pane.scrollTop = 0;
      })
      .catch(() => undefined);
  await page.waitForTimeout(450);
}

test('mounting plate lesson is readable, honest and accessible at 320px', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await authenticatedFixture(page);
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.goto('/');
  await page.getByRole('tab', { name: 'Learn', exact: true }).click();
  await page.getByRole('radio', { name: /^Beginner/ }).check();
  await page
    .getByRole('radio', {
      name: 'Follow a mounting plate from sketch to fillet',
      exact: true,
    })
    .check();
  await page.getByRole('button', { name: 'Review lesson' }).click();
  await page.getByRole('button', { name: 'Begin lesson' }).click();
  await expect(page.getByText(/Forge does not check your model/)).toBeVisible();
  await expect(page.getByText('Verified', { exact: true })).toHaveCount(0);
  // Interactive question gives feedback without grading.
  await page.getByRole('radio', { name: /still a flat outline/ }).check();
  await expect(page.getByText(/matches how sketches work/)).toBeVisible();
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
  await settleNav(page);
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(results.violations).toEqual([]);
  await page.screenshot({ path: '.cache/phase19c/plate-320.png' });
});
