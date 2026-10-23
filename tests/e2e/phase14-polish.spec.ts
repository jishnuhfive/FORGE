import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';
import { signedIn } from './auth-fixtures';
import { resultStream } from '../../apps/web/src/ai/__fixtures__/response';
import {
  canonicalAnswer,
  fullLimits,
  polishCases,
} from '../../apps/web/src/ai/__fixtures__/phase14';
import type { Answer } from '../../apps/web/src/ai/api';

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
});
const query = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
async function panel(page: Page, result: Answer) {
  const requests: Record<string, unknown>[] = [];
  const unexpected: string[] = [];
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.route('https://forge-panel.test/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/me') await route.fulfill({ json: signedIn });
    else if (url.pathname === '/api/ai/ask') {
      requests.push(route.request().postDataJSON() as Record<string, unknown>);
      await route.fulfill({
        contentType: 'application/x-ndjson',
        body: resultStream(result),
      });
    } else if (url.pathname === '/api/modify/capabilities') {
      await route.fulfill({ json: { state: 'write_disabled' } });
    } else if (url.pathname === '/api/modify/recovery') {
      await route.fulfill({ json: { state: 'none' } });
    } else if (
      url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/auth/')
    ) {
      unexpected.push(url.pathname);
      await route.abort();
    } else
      await route.fulfill({
        response: await page.request.get(
          `http://127.0.0.1:4173${url.pathname}${url.search}`,
        ),
      });
  });
  await page.route('https://cad.onshape.com/forge-polish-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic Phase 14 panel</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-polish-test');
  await page.bringToFront();
  const frame = page.frameLocator('iframe');
  await expect(frame.getByLabel('Design prompt')).toBeVisible();
  const child = page
    .frames()
    .find((frame) => frame.url().includes('forge-panel.test/extension'))!;
  const send = async (prompt: string) => {
    await frame.getByLabel('Design prompt').fill(prompt);
    await frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(frame.locator('.ai-exchange')).toHaveCount(1);
  };
  return { frame, child, send, requests, unexpected };
}

for (const [name, value] of Object.entries(polishCases)) {
  test(`Phase 14 concise ${name} keeps canonical evidence and full limits`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width: 380, height: 800 });
    const h = await panel(page, value.result);
    await h.send(value.prompt);
    for (const text of value.paragraphs)
      await expect(h.frame.getByText(text, { exact: true })).toBeVisible();
    await expect(
      h.frame.getByRole('heading', { name: 'Uncertainties' }),
    ).toHaveCount(0);
    await expect(
      h.frame.getByText(fullLimits[1]!, { exact: true }),
    ).toHaveCount(0);
    await expect(h.frame.getByRole('list', { name: 'Evidence' })).toHaveCount(
      0,
    );
    if (name === 'inventory') {
      await expect(h.frame.getByLabel('Feature order')).toHaveText(
        'Sketch GateExtrude 1Fillet 1',
      );
      await expect(
        h.frame.getByRole('region', { name: 'Limits' }),
      ).toContainText('Feature order does not prove dependency.');
    }
    if (name === 'dependency')
      await expect(
        h.frame.getByRole('region', { name: 'Limits' }),
      ).toContainText('Dependency has not been established.');
    if (name === 'selection')
      await expect(
        h.frame.getByRole('region', { name: 'Limits' }),
      ).toContainText(
        'Owning feature is not available from the current evidence.',
      );
    if (name === 'state' || name === 'empty')
      await expect(h.frame.getByRole('region', { name: 'Limits' })).toHaveCount(
        0,
      );
    if (name === 'empty') {
      await expect(
        h.frame.getByText(
          /0 entries omitted|Compare proposed dimensions|static loading|loads and clearances/,
        ),
      ).toHaveCount(0);
      await expect(h.frame.locator('.model-facts')).toHaveText(
        '0 features·0 parts·0 bodies',
      );
    }
    if (name === 'write') {
      await expect(h.frame.locator('.answer-text')).not.toContainText(
        'Sketch Gate',
      );
      await expect(
        h.frame.getByRole('button', { name: /approve|apply|build/i }),
      ).toHaveCount(0);
    }
    if (browserName === 'chromium') {
      await mkdir('.cache/phase14-polish', { recursive: true });
      await page.screenshot({ path: `.cache/phase14-polish/${name}.png` });
    }
    const disclosure = h.frame.getByRole('button', {
      name: 'Evidence',
      exact: true,
    });
    await disclosure.focus();
    await disclosure.press('Enter');
    await expect(
      h.frame.getByRole('button', { name: 'Hide evidence' }),
    ).toHaveAttribute('aria-expanded', 'true');
    const evidence = h.frame.getByRole('list', { name: 'Evidence' });
    await expect(evidence.getByRole('listitem')).toHaveCount(
      value.result.evidence.length,
    );
    for (const item of value.result.evidence)
      await expect(
        evidence.getByText(item.statement, { exact: true }),
      ).toBeVisible();
    const technical = h.frame
      .getByRole('heading', { name: 'Technical limits' })
      .locator('..');
    await expect(technical.getByRole('listitem')).toHaveText(fullLimits);
    await expect(h.frame.locator('.evidence-original .draft-text')).toHaveText(
      value.result.answer,
    );
    await expect(h.frame.locator('time')).toHaveAttribute(
      'datetime',
      value.result.captured_at!,
    );
    // Exercise native keyboard focus before axe opens/closes its temporary page.
    await h.frame.getByRole('button', { name: 'Hide evidence' }).press('Space');
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await expect(disclosure).toBeFocused();
    await expect(h.frame.getByRole('list', { name: 'Evidence' })).toHaveCount(
      0,
    );
    await disclosure.press('Enter');
    await expect(evidence).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    expect(h.requests).toHaveLength(1);
    expect(h.unexpected).toEqual([]);
  });
}

test('Phase 14 engineering limit remains visible and malformed evidence keeps the full answer', async ({
  page,
}) => {
  const result = canonicalAnswer([
    {
      id: 'terminal_feature',
      status: 'unknown',
      statement: 'A last visible feature does not establish a terminal.',
    },
  ]);
  const h = await panel(page, result);
  await h.send('Is the final feature safe under load?');
  await expect(h.frame.locator('.answer-text')).toHaveText(result.answer);
  await expect(h.frame.getByRole('region', { name: 'Limits' })).toContainText(
    'Engineering validation has not been run.',
  );
  await h.frame.getByRole('button', { name: 'Evidence' }).click();
  await expect(
    h.frame
      .getByRole('heading', { name: 'Technical limits' })
      .locator('..')
      .getByRole('listitem'),
  ).toHaveText(fullLimits);
  expect(h.unexpected).toEqual([]);
});

for (const width of [320, 380])
  for (const reduced of [false, true]) {
    test(`Phase 14 mode navigation scroll, focus and sticky composer at ${width}px reduced=${reduced}`, async ({
      page,
      browserName,
    }) => {
      await page.setViewportSize({ width, height: 640 });
      await page.emulateMedia({
        reducedMotion: reduced ? 'reduce' : 'no-preference',
      });
      const h = await panel(page, polishCases.inventory.result);
      await h.send(polishCases.inventory.prompt);
      await h.frame.getByRole('button', { name: 'Evidence' }).click();
      const pane = h.frame.getByRole('region', { name: 'Workspace content' });
      const nav = h.frame.getByRole('tablist', { name: 'Engineering mode' });
      const scrollTo = async (y: number) => {
        await pane.evaluate(async (node, y) => {
          node.scrollTop = y;
          await new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
          );
        }, y);
      };
      await scrollTo(0);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'false');
      await expect(nav).toBeVisible();
      const metrics = await h.frame
        .locator('.ai-exchange')
        .evaluate((node) => ({
          top: (node as HTMLElement).offsetTop,
          height: node.closest('.workspace-pane')!.scrollHeight,
        }));
      await scrollTo(140);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'true');
      await expect(nav).toHaveCSS('opacity', '0');
      const uncovered = await nav.evaluate((node) => {
        const pane = node.closest('.workspace-pane')!;
        const bounds = pane.getBoundingClientRect();
        const hit = document.elementFromPoint(
          bounds.left + bounds.width / 2,
          bounds.top + 16,
        );
        return (
          !node.contains(hit) &&
          node.getBoundingClientRect().bottom <= bounds.top
        );
      });
      expect(uncovered).toBe(true);
      await scrollTo(240);
      for (const y of [239, 241, 238, 240]) await scrollTo(y);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'true');
      await scrollTo(210);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'false');
      await expect(nav).toHaveCSS('opacity', '1');
      for (const y of [211, 209, 212, 210]) await scrollTo(y);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'false');
      await scrollTo(300);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'true');
      await scrollTo(12);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'false');
      await scrollTo(180);
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'true');
      await pane.focus();
      await pane.press('Tab');
      await expect(
        h.frame.getByRole('tab', { name: 'Design', exact: true }),
      ).toBeFocused();
      await expect(nav).toHaveAttribute('data-scroll-hidden', 'false');
      await expect(nav).toHaveCSS('opacity', '1');
      await expect(nav).toHaveCSS('transition-duration', '0s');
      await pane.focus();
      await scrollTo(400);
      await expect(h.frame.locator('.composer-area')).toHaveCSS(
        'position',
        'sticky',
      );
      const composer = await h.frame.locator('.composer-area').boundingBox();
      const bounds = await pane.boundingBox();
      expect(composer!.y + composer!.height).toBeLessThanOrEqual(
        bounds!.y + bounds!.height + 1,
      );
      expect(composer!.y).toBeGreaterThanOrEqual(bounds!.y);
      const after = await h.frame.locator('.ai-exchange').evaluate((node) => ({
        top: (node as HTMLElement).offsetTop,
        height: node.closest('.workspace-pane')!.scrollHeight,
      }));
      expect(after).toEqual(metrics);
      expect(
        await h.child.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      if (reduced) await expect(nav).toHaveCSS('transition-duration', '0s');
      if (browserName === 'chromium') {
        await mkdir('.cache/phase14-polish', { recursive: true });
        await page.screenshot({
          path: `.cache/phase14-polish/navigation-${width}-${reduced}.png`,
        });
      }
      for (const name of ['Modify', 'Learn', 'Design']) {
        const tab = h.frame.getByRole('tab', { name, exact: true });
        await tab.focus();
        await expect(tab).toBeFocused();
        await expect(tab).toHaveAttribute('aria-selected', 'true');
        await expect(nav).toHaveAttribute('data-scroll-hidden', 'false');
        await expect(nav).toHaveCSS('opacity', '1');
      }
      expect(h.unexpected).toEqual([]);
    });
  }
