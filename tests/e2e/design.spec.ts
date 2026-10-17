import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';

for (const width of [320, 360, 400, 480, 600, 1280]) {
  test(`Phase 6.5 answer, evidence, opaque material and focus at ${width}px`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width: width + 32, height: 950 });
    await page.goto('http://127.0.0.1:4174/#/lab');
    await page.getByLabel('Preview state').selectOption('Phase 6.5 workspace');
    await page
      .getByLabel('Layout')
      .selectOption(width > 600 ? 'wide' : String(width));
    if (width <= 600)
      expect((await page.locator('.lab-frame').boundingBox())!.width).toBe(
        width,
      );
    await page.getByLabel('Workspace state').selectOption('Answer');
    const evidence = page.getByRole('button', {
      name: 'Evidence',
      exact: true,
    });
    await expect(evidence).toHaveAttribute('aria-expanded', 'false');
    await evidence.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('list', { name: 'Evidence' })).toBeVisible();
    await expect(page.getByText('verified', { exact: true })).toHaveCount(1);
    await expect(page.getByText('unknown', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Hide evidence' }).press('Enter');
    await expect(page.getByRole('list', { name: 'Evidence' })).toHaveCount(0);
    await expect(evidence).toBeFocused();
    await page.getByLabel('Reduce transparency', { exact: true }).check();
    expect(
      await page
        .locator('.composer')
        .evaluate((node) => getComputedStyle(node, '::before').backdropFilter),
    ).toBe('none');
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
    if (browserName === 'chromium') {
      await page.getByLabel('Reduce transparency', { exact: true }).uncheck();
      await page
        .locator('.lab-frame')
        .screenshot({ path: `.cache/phase6.5/answer-${width}.png` });
    }
  });
}

test('Phase 6.5 state matrix, reduced motion, contrast and no automatic requests', async ({
  page,
  browserName,
}) => {
  const calls: string[] = [];
  page.on('request', (request) => {
    if (
      ['fetch', 'xhr'].includes(request.resourceType()) &&
      new URL(request.url()).pathname.startsWith('/api/')
    )
      calls.push(request.url());
  });
  await page.setViewportSize({ width: 360, height: 950 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page.getByLabel('Preview state').selectOption('Phase 6.5 workspace');
  for (const state of [
    'First launch',
    'Mass unavailable',
    'Validation unavailable',
    'Write request',
    'Capacity limit',
    'Provider timeout',
    'Verification failure',
    'Cancelled',
    'Context changed',
    'Empty Part Studio',
    'Selection unknown',
    'No selection',
    'FACE',
    'EDGE',
    'Sending',
    'Inspecting CAD',
    'Reviewing evidence',
    'Preparing answer',
    'AI unavailable',
    'CAD unavailable',
    'Signed out',
  ]) {
    await page.getByLabel('Workspace state').selectOption(state);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      await page.evaluate(
        () =>
          document
            .getAnimations()
            .filter((animation) => animation.playState === 'running').length,
      ),
    ).toBe(0);
    if (
      [
        'Sending',
        'Inspecting CAD',
        'Reviewing evidence',
        'Preparing answer',
      ].includes(state)
    ) {
      await expect(page.getByLabel('Preview prompt')).toBeDisabled();
      await expect(page.getByRole('status')).toBeVisible();
    }
    if (
      [
        'Capacity limit',
        'Provider timeout',
        'Verification failure',
        'Cancelled',
        'AI unavailable',
        'CAD unavailable',
        'Signed out',
      ].includes(state)
    )
      await expect(page.getByRole('alert')).toBeVisible();
    if (
      browserName === 'chromium' &&
      [
        'First launch',
        'Inspecting CAD',
        'Capacity limit',
        'FACE',
        'EDGE',
        'Empty Part Studio',
      ].includes(state)
    )
      await page.locator('.lab-frame').screenshot({
        path: `.cache/phase6.5/${state.replaceAll(' ', '-').toLowerCase()}-360.png`,
      });
  }
  await page.getByLabel('Increase contrast').check();
  await page
    .getByLabel('Preview state')
    .selectOption('Phase 6.5 design system');
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole('button', { name: 'Material menu' }).click();
  await expect(page.getByRole('menuitem')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(
    page.getByRole('button', { name: 'Material menu' }),
  ).toBeFocused();
  expect(calls).toEqual([]);
});

test('Phase 6.5 material idle and interaction performance sample', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 480, height: 950 });
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page
    .getByLabel('Preview state')
    .selectOption('Phase 6.5 design system');
  const material = page.locator('.material-sample');
  await material.scrollIntoViewIfNeeded();
  const box = (await material.boundingBox())!;
  await page.mouse.move(box.x + 10, box.y + 10);
  for (let i = 0; i < 20; i++)
    await page.mouse.move(box.x + 10 + i * 4, box.y + 10 + i);
  await page.mouse.move(0, 0);
  await expect.poll(() => material.getAttribute('style')).toBe('');
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          document
            .getAnimations()
            .filter((animation) => animation.playState === 'running').length,
      ),
    )
    .toBe(0);
  // Sampling runs in this test only, never in the application.
  const intervals = await page.evaluate(async () => {
    const values: number[] = [];
    let previous = performance.now();
    for (let i = 0; i < 60; i++)
      await new Promise<void>((resolve) =>
        requestAnimationFrame((now) => {
          values.push(now - previous);
          previous = now;
          resolve();
        }),
      );
    return values.slice(1).sort((a, b) => a - b);
  });
  const result = {
    browser: browserName,
    samples: intervals.length,
    medianFrameMs: intervals[Math.floor(intervals.length / 2)],
    p95FrameMs: intervals[Math.floor(intervals.length * 0.95)],
    idleAnimations: await page.evaluate(
      () =>
        document
          .getAnimations()
          .filter((animation) => animation.playState === 'running').length,
    ),
    note: 'Synthetic localhost sample; not real Onshape GPU/trackpad verification.',
  };
  expect(result.medianFrameMs).toBeLessThan(35);
  await mkdir('.cache/phase6.5', { recursive: true });
  await writeFile(
    `.cache/phase6.5/performance-${browserName}.json`,
    JSON.stringify(result, null, 2),
  );
  if (browserName === 'chromium') {
    await page.getByLabel('Bright backdrop stress test').check();
    await material.scrollIntoViewIfNeeded();
    const enhanced = await material.screenshot({
      path: '.cache/phase6.5/material.png',
    });
    await page.addStyleTag({
      content: '.material-sample::after { backdrop-filter: none !important; }',
    });
    const baseline = await material.screenshot();
    expect(
      enhanced.equals(baseline),
      'Supported Chromium edge refraction must affect rendered pixels',
    ).toBe(false);
  }
});
