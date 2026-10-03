import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const width of [320, 1280]) {
  test(`foundation renders without overflow at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 800 });
    await page.goto('/');
    await expect(page).toHaveTitle('Forge — AI engineering inside Onshape');
    await expect(
      page.getByRole('heading', { name: 'Forge', exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText('AI engineering inside Onshape', { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText('Phase 0 — Foundation', { exact: true }),
    ).toBeVisible();
    const accessibility = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(accessibility.violations).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  });
}
