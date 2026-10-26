import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';
import { signedIn } from './auth-fixtures';
import {
  resultStream,
  syntheticOverview,
} from '../../apps/web/src/ai/__fixtures__/response';
import {
  faceSelection,
  edgeSelection,
} from '../../apps/web/src/onshape/__fixtures__/selection';

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

const output = '.cache/phase6.5-final';
const query = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;

for (const view of ['Material comparison', 'Logo candidates']) {
  test(`refinement ${view} visual comparison`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width: 1320, height: 1080 });
    await page.goto('http://127.0.0.1:4174/#/lab');
    await page.getByLabel('Theme', { exact: true }).selectOption('dark');
    await page.getByLabel('Preview state').selectOption(view);
    await page.getByLabel('Layout').selectOption('wide');
    await expect(page.locator('.refinement-columns > section')).toHaveCount(3);
    if (view === 'Material comparison') {
      for (const input of await page.locator('.composer textarea').all())
        await input.fill('Explain this face.');
      await page
        .getByRole('heading', { name: 'Material comparison', exact: true })
        .click();
    }
    await settleNav(page);
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
      await mkdir(output, { recursive: true });
      await page.screenshot({
        path: `${output}/${view === 'Logo candidates' ? 'logo-candidates' : 'material-abc'}.png`,
        fullPage: true,
      });
      if (view === 'Logo candidates')
        await page
          .locator('.candidate-review')
          .first()
          .screenshot({
            path: `${output}/approved-brand.png`,
          });
    }
  });
}

for (const width of [320, 380, 480]) {
  test(`refinement real panel presentation and composition ${width}px`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() =>
      localStorage.setItem(
        'forge.preferences.v1',
        JSON.stringify({ onboarded: true, theme: 'dark' }),
      ),
    );
    const asks: Record<string, unknown>[] = [];
    await page.route('https://forge-panel.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/me') await route.fulfill({ json: signedIn });
      else if (url.pathname === '/api/ai/ask') {
        asks.push(route.request().postDataJSON() as Record<string, unknown>);
        await route.fulfill({
          contentType: 'application/x-ndjson',
          body: resultStream(syntheticOverview),
        });
      } else
        await route.fulfill({
          response: await page.request.get(
            `http://127.0.0.1:4173${url.pathname}${url.search}`,
          ),
        });
    });
    await page.route('https://cad.onshape.com/forge-refinement-test', (route) =>
      route.fulfill({
        contentType: 'text/html',
        body: `<!doctype html><html lang="en"><head><title>Synthetic Onshape parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0;display:block" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
      }),
    );
    await page.goto('https://cad.onshape.com/forge-refinement-test');
    const frame = page.frameLocator('iframe');
    const input = frame.getByLabel('Design prompt');
    await expect(input).toBeVisible();
    await expect(
      frame.getByRole('heading', { name: 'Ask about this Part Studio' }),
    ).toBeVisible();
    await expect(
      frame.getByText('Development tools', { exact: true }),
    ).toHaveCount(0);
    const capture = async (name: string) => {
      if (browserName === 'chromium') {
        await mkdir(output, { recursive: true });
        await page.screenshot({ path: `${output}/${name}-${width}.png` });
      }
    };
    await capture('first-open');
    for (const [kind, selection] of [
      ['face', faceSelection],
      ['edge', edgeSelection],
    ] as const) {
      await page.evaluate(
        (message) =>
          document
            .querySelector('iframe')!
            .contentWindow!.postMessage(message, 'https://forge-panel.test'),
        selection,
      );
      await expect(
        frame.getByText(`1 ${kind} selected`, { exact: true }),
      ).toBeVisible();
      await capture(kind);
    }
    expect(asks).toHaveLength(0);
    const shortHeight = (await input.boundingBox())!.height;
    await input.fill(
      'A long prompt\nwith several lines\nto review bounded auto growth\nand preserve the selection context\nwhen changing the input\nlast line',
    );
    expect((await input.boundingBox())!.height).toBeGreaterThan(shortHeight);
    expect((await input.boundingBox())!.height).toBeLessThanOrEqual(144);
    await input.fill('What is in this Part Studio?');
    await frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(
      frame.getByRole('heading', { name: 'Current model', exact: true }),
    ).toBeVisible();
    await expect(
      frame.getByRole('heading', { name: 'Ask about this Part Studio' }),
    ).toHaveCount(0);
    await expect(frame.locator('.feature-sequence')).toHaveText(
      'Sketch 1Extrude 1',
    );
    await expect(frame.locator('.model-facts')).toHaveText(
      '2 features·1 part·1 body',
    );
    await expect(frame.locator('.topology-note')).toHaveCount(0);
    expect(asks).toHaveLength(1);
    expect(asks[0]?.selection).toBe('EDGE');
    await capture('answer');
    const pane = frame.locator('.workspace-pane');
    expect(
      await pane.evaluate((node) => node.scrollWidth <= node.clientWidth),
    ).toBe(true);
    await frame.getByRole('button', { name: 'Evidence', exact: true }).click();
    await expect(
      frame.getByRole('list', { name: 'Evidence' }).locator('li'),
    ).toHaveCount(8);
    // The concise inventory keeps body topology in Evidence, without losing
    // either the observed face count or the unknown edge/vertex counts.
    await expect(
      frame
        .getByRole('list', { name: 'Evidence' })
        .getByText(
          syntheticOverview.evidence.find((item) => item.id === 'body_1')!
            .statement,
          { exact: true },
        ),
    ).toBeVisible();
    await expect(frame.locator('.evidence-original p')).toHaveText(
      syntheticOverview.answer,
    );
    await capture('expanded-evidence');
    // Single product scroll plane; the composer remains usable while reading long evidence.
    await pane.evaluate((node) => {
      node.scrollTop = node.scrollHeight;
    });
    await expect(input).toBeInViewport();
    await expect(frame.locator('.app-header')).toBeInViewport();
    await settleNav(page);
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    await frame.getByRole('button', { name: 'Hide evidence' }).click();
    await frame.getByRole('button', { name: 'Data use' }).click();
    await expect(
      frame.getByRole('dialog', { name: 'Your data' }),
    ).toContainText('configured AI service');
    await page.keyboard.press('Escape');
    await expect(frame.getByRole('button', { name: 'Data use' })).toBeFocused();
    await frame.getByRole('button', { name: 'Workspace menu' }).click();
    await expect(
      frame.getByRole('menuitem', { name: 'Developer', exact: true }),
    ).toHaveCount(0);
    await frame.getByRole('menuitem', { name: 'Privacy', exact: true }).click();
    await expect(
      frame.getByRole('dialog', { name: 'Your data' }),
    ).toBeVisible();
    await page.keyboard.press('Escape');
  });
}

test('refinement opaque and motion reductions preserve composition and zero idle motion', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 512, height: 1000 });
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page.getByLabel('Preview state').selectOption('Phase 6.5 workspace');
  await page.getByLabel('Layout').selectOption('480');
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await page.getByLabel('Reduce transparency', { exact: true }).check();
  expect(
    await page
      .locator('.composer')
      .evaluate((node) => getComputedStyle(node, '::before').backdropFilter),
  ).toBe('none');
  if (browserName === 'chromium')
    await page
      .locator('.lab-frame')
      .screenshot({ path: `${output}/reduced-transparency.png` });
  await page.getByLabel('Reduce transparency', { exact: true }).uncheck();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.getByLabel('Workspace state').selectOption('Answer');
  expect(
    await page.evaluate(
      () =>
        document
          .getAnimations()
          .filter((animation) => animation.playState === 'running').length,
    ),
  ).toBe(0);
  await settleNav(page);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  if (browserName === 'chromium')
    await page
      .locator('.lab-frame')
      .screenshot({ path: `${output}/reduced-motion.png` });
});
