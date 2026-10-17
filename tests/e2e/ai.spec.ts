import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { signedIn, signedOut } from './auth-fixtures';
import {
  resultStream,
  syntheticAnswer,
  syntheticSelectionAnswer,
  syntheticWriteAnswer,
} from '../../apps/web/src/ai/__fixtures__/response';
import {
  faceSelection,
  edgeSelection,
  clearedSelection,
} from '../../apps/web/src/onshape/__fixtures__/selection';
import { inspectorFixture } from '../../apps/web/src/cad/__fixtures__/inspector';

const query = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
async function panel(page: Page) {
  const asks: Record<string, unknown>[] = [];
  let account: typeof signedIn | typeof signedOut = signedIn;
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.route('https://forge-panel.test/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/me') await route.fulfill({ json: account });
    else if (url.pathname === '/api/ai/ask') {
      asks.push(route.request().postDataJSON() as Record<string, unknown>);
      expect(route.request().method()).toBe('POST');
      expect(route.request().headers()['x-csrf-token']).toBe(
        signedIn.csrf_token,
      );
      await route.fulfill({
        contentType: 'application/x-ndjson',
        body: resultStream(),
      });
    } else if (url.pathname === '/api/onshape/part-studio/inspector')
      await route.fulfill({ json: inspectorFixture() });
    else
      await route.fulfill({
        response: await page.request.get(
          `http://127.0.0.1:4173${url.pathname}${url.search}`,
        ),
      });
  });
  await page.route('https://cad.onshape.com/forge-ai-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic Onshape parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-ai-test');
  const frame = page.frameLocator('iframe');
  await expect(frame.getByLabel('Design prompt')).toBeVisible();
  const child = page
    .frames()
    .find((frame) => frame.url().includes('forge-panel.test/extension'))!;
  const send = (message: unknown) =>
    page.evaluate(
      (message) =>
        document
          .querySelector('iframe')
          ?.contentWindow?.postMessage(message, 'https://forge-panel.test'),
      message,
    );
  return {
    frame,
    child,
    asks,
    send,
    disconnect: () => {
      account = { ...signedIn, connection: 'disconnected' };
    },
    changeAccount: (next: typeof signedIn | typeof signedOut) => {
      account = next;
    },
  };
}

for (const width of [320, 380, 480])
  test(`Phase 6 explicit send, grounded evidence, accessibility and overflow at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const h = await panel(page);
    expect(h.asks).toHaveLength(0);
    await h.frame
      .getByLabel('Design prompt')
      .fill('What is in this Part Studio?');
    await h.frame.getByLabel('Design prompt').press('Control+Enter');
    await expect(
      h.frame.getByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
    await h.frame.getByText('Evidence', { exact: true }).click();
    await expect(
      h.frame.getByText('verified', { exact: true }).first(),
    ).toBeVisible();
    await expect(h.frame.getByText('unknown', { exact: true })).toBeVisible();
    await expect(
      h.frame.getByRole('heading', { name: 'Uncertainties' }),
    ).toBeVisible();
    expect(h.asks).toHaveLength(1);
    expect(h.asks[0]?.selection).toBe('unknown');
    expect(
      await h.child.evaluate(
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
    expect(
      await h.child.evaluate(() => JSON.stringify(localStorage)),
    ).not.toContain('Part Studio');
    if (width === 320 || width === 480) {
      await page.screenshot({
        path: `.cache/phase6.5/evidence-${width}.png`,
        fullPage: true,
      });
      await h.frame.getByRole('button', { name: 'Hide evidence' }).click();
      await page.screenshot({
        path: `.cache/phase6.5/workspace-${width}.png`,
        fullPage: true,
      });
    }
  });

test('Phase 6 selection, Refresh CAD and browser focus never initiate AI', async ({
  page,
}) => {
  const h = await panel(page);
  for (const data of [faceSelection, edgeSelection, clearedSelection])
    await h.send(data);
  await h.frame.getByRole('button', { name: 'View CAD context' }).click();
  await h.frame.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(
    h.frame.getByRole('dialog').getByText('Sketch 1', { exact: true }),
  ).toBeVisible();
  await h.child.evaluate(() => {
    document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new Event('focus'));
  });
  expect(h.asks).toHaveLength(0);
});

for (const [data, selection] of [
  [faceSelection, 'FACE'],
  [edgeSelection, 'EDGE'],
  [clearedSelection, 'none'],
] as const)
  test(`Phase 6 sends normalized ${selection} with no raw reference`, async ({
    page,
  }) => {
    const h = await panel(page);
    await h.send(data);
    await h.frame
      .getByLabel('Design prompt')
      .fill('What do you know about my selection?');
    await h.frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(
      h.frame.getByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
    expect(h.asks[0]?.selection).toBe(selection);
    await expect(h.frame.locator('.composer-context')).toContainText(
      selection === 'none'
        ? 'No selection'
        : selection === 'FACE'
          ? '1 face selected'
          : '1 edge selected',
    );
    expect(JSON.stringify(h.asks[0])).not.toContain('reference');
  });

test('Phase 6 same-context tab switching preserves history; real Part Studio change clears it', async ({
  page,
  context,
}) => {
  const h = await panel(page);
  await h.frame.getByLabel('Design prompt').fill('What is in this model?');
  await h.frame.getByRole('button', { name: 'Send prompt' }).click();
  await expect(
    h.frame.getByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    }),
  ).toBeVisible();
  const other = await context.newPage();
  await other.goto('about:blank');
  await page.bringToFront();
  await other.close();
  await h.send({ messageName: 'show' });
  await expect(
    h.frame.getByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    }),
  ).toBeVisible();
  expect(h.asks).toHaveLength(1);
  await expect(h.frame.getByLabel('Design prompt')).toBeEnabled({
    timeout: 8000,
  });
  await h.frame.getByLabel('Design prompt').fill('Which feature comes second?');
  await h.frame.getByRole('button', { name: 'Send prompt' }).click();
  await expect(
    h.frame.getByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    }),
  ).toHaveCount(2);
  expect(h.asks[1]?.history).toHaveLength(2);
  await page.locator('iframe').evaluate(
    (node, next) => {
      (node as HTMLIFrameElement).src =
        `https://forge-panel.test/extension?${next}`;
    },
    query.replace('c'.repeat(24), 'e'.repeat(24)),
  );
  await expect(h.frame.getByLabel('Design prompt')).toBeVisible();
  await expect(
    h.frame.getByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    }),
  ).toHaveCount(0);
  expect(h.asks).toHaveLength(2);
});

for (const code of [
  'not_configured',
  'rate_limited',
  'capacity_unavailable',
  'connection_unavailable',
  'timeout',
])
  test(`Phase 6 safe ${code} and explicit retry`, async ({ page }) => {
    const h = await panel(page);
    let requests = 0;
    await page.route('https://forge-panel.test/api/ai/ask', async (route) => {
      requests++;
      await route.fulfill({
        contentType: 'application/x-ndjson',
        body:
          JSON.stringify({ type: 'error', code, retry_after_seconds: 1 }) +
          '\n',
      });
    });
    await h.frame.getByLabel('Design prompt').fill('Inspect my model');
    await h.frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(h.frame.getByRole('alert')).toBeVisible();
    await expect(
      h.frame.getByRole('button', { name: 'Try again' }),
    ).toBeEnabled();
    expect(requests).toBe(1);
    await h.frame.getByRole('button', { name: 'Try again' }).click();
    await expect.poll(() => requests).toBe(2);
  });

test('Phase 6 prevents duplicate submits and supports cancellation', async ({
  page,
}) => {
  const h = await panel(page);
  let requests = 0;
  await page.route('https://forge-panel.test/api/ai/ask', async (route) => {
    requests++;
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route
      .fulfill({ contentType: 'application/x-ndjson', body: resultStream() })
      .catch(() => undefined);
  });
  await h.frame.getByLabel('Design prompt').fill('Explain this model');
  await h.frame.getByLabel('Design prompt').press('Control+Enter');
  await expect(h.frame.getByText('Understanding request…')).toBeVisible();
  await expect(h.frame.getByLabel('Design prompt')).toBeDisabled();
  await h.frame.getByRole('button', { name: 'Stop request' }).click();
  await expect(h.frame.getByRole('alert')).toContainText('Request cancelled');
  expect(requests).toBeLessThanOrEqual(1);
  await expect(
    h.frame.getByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    }),
  ).toHaveCount(0);
});

for (const change of ['session', 'logout', 'revoked'])
  test(`Phase 6 ${change} clears AI conversation`, async ({ page }) => {
    const h = await panel(page);
    await h.frame.getByLabel('Design prompt').fill('What is in this model?');
    await h.frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(
      h.frame.getByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
    h.changeAccount(
      change === 'logout'
        ? signedOut
        : change === 'revoked'
          ? { ...signedIn, connection: 'revoked' }
          : { ...signedIn, csrf_token: 'e'.repeat(64) },
    );
    await h.child.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(
      h.frame.getByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toHaveCount(0);
  });

test('Phase 6 rejects raw provider events without displaying reasoning or tool internals', async ({
  page,
}) => {
  const h = await panel(page);
  await page.route('https://forge-panel.test/api/ai/ask', (route) =>
    route.fulfill({
      contentType: 'application/x-ndjson',
      body:
        JSON.stringify({
          type: 'response.reasoning_summary_text.delta',
          delta: 'synthetic-private-reasoning',
          tool: 'synthetic-hidden-tool',
        }) + '\n',
    }),
  );
  await h.frame.getByLabel('Design prompt').fill('Explain this model');
  await h.frame.getByRole('button', { name: 'Send prompt' }).click();
  await expect(h.frame.getByRole('alert')).toContainText(
    'response could not be verified',
  );
  await expect(
    h.frame.getByText(/synthetic-private-reasoning|synthetic-hidden-tool/),
  ).toHaveCount(0);
});

test('Phase 6 disconnect clears the old conversation and unsupported write stays read-only', async ({
  page,
}) => {
  const h = await panel(page);
  await page.route('https://forge-panel.test/api/ai/ask', (route) =>
    route.fulfill({
      contentType: 'application/x-ndjson',
      body: resultStream(syntheticWriteAnswer),
    }),
  );
  await h.frame
    .getByLabel('Design prompt')
    .fill('Make this model 20 mm wider.');
  await h.frame.getByRole('button', { name: 'Send prompt' }).click();
  await expect(h.frame.getByText(/currently read-only/)).toBeVisible();
  await expect(h.frame.getByText(/width-driving dimension/)).toBeVisible();
  await expect(h.frame.getByText(/performed no CAD writes/)).toBeVisible();
  await expect(h.frame.getByRole('alert')).toHaveCount(0);
  await expect(h.frame.getByRole('list', { name: 'Evidence' })).toHaveCount(0);
  await h.frame.getByRole('button', { name: 'Evidence' }).click();
  await expect(h.frame.getByText('unknown', { exact: true })).toBeVisible();
  await expect(
    h.frame.getByRole('heading', { name: 'Assumptions' }),
  ).toHaveCount(0);
  await expect(
    h.frame.getByRole('heading', { name: 'Suggestions · unverified' }),
  ).toHaveCount(0);
  h.disconnect();
  await h.child.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(
    h.frame.getByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    }),
  ).toHaveCount(0);
});

test('Phase 6 collapsed and expanded evidence copies contain no empty list rows', async ({
  page,
  browserName,
}) => {
  const h = await panel(page);
  await expect(h.frame.locator('.composer-context')).toContainText(
    'Selection unknown',
  );
  await h.frame
    .getByLabel('Design prompt')
    .fill('What is in this Part Studio?');
  await h.frame.getByRole('button', { name: 'Send prompt' }).click();
  const heading = h.frame.getByRole('heading', {
    name: /^(Response|Current model|Selected face|Selected edge)$/,
  });
  await expect(heading).toBeVisible();
  const evidence = h.frame.getByRole('list', { name: 'Evidence' });
  await expect(
    h.frame.getByRole('button', { name: 'Evidence' }),
  ).toHaveAttribute('aria-expanded', 'false');
  await expect(evidence).toHaveCount(0);
  if (browserName === 'chromium') {
    await page
      .context()
      .grantPermissions(['clipboard-read', 'clipboard-write'], {
        origin: 'https://cad.onshape.com',
      });
  }
  const copiedRows = async () => {
    await page.bringToFront();
    await h.frame.locator('.ai-exchange .user-prompt').click();
    // Initialize first, so this test can never read existing user clipboard data.
    if (browserName === 'chromium')
      await page.evaluate(() =>
        navigator.clipboard.writeText('synthetic-copy-marker'),
      );
    await h.frame.locator('.ai-exchange .user-prompt').click();
    await h.frame.locator('.ai-exchange').evaluate((element) => {
      const range = document.createRange();
      range.selectNodeContents(element);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    });
    if (browserName !== 'chromium') return null;
    await page.keyboard.press('ControlOrMeta+C');
    return page.evaluate(async () => {
      const items = await navigator.clipboard.read();
      const item = items.find((item) => item.types.includes('text/html'));
      if (!item) throw new Error('Synthetic HTML clipboard not produced');
      const html = await (await item.getType('text/html')).text();
      const document = new DOMParser().parseFromString(html, 'text/html');
      return [...document.querySelectorAll('li')].map((row) =>
        row.textContent?.trim(),
      );
    });
  };
  let rows = await copiedRows();
  // Only the visible uncertainty list is copied while evidence is collapsed.
  if (rows) {
    expect(rows.every(Boolean)).toBe(true);
    expect(rows).not.toContain(
      'verifiedSketch 1 is first in the returned feature list.',
    );
  }
  await h.frame.getByRole('button', { name: 'Evidence' }).click();
  await expect(evidence.getByRole('listitem')).toHaveCount(
    syntheticAnswer.evidence.length,
  );
  for (const statement of syntheticAnswer.evidence) {
    await expect(
      evidence.getByText(statement.statement, { exact: true }),
    ).toBeVisible();
  }
  rows = await copiedRows();
  if (rows) {
    expect(rows.every(Boolean)).toBe(true);
    expect(
      rows.some((row) => row?.includes(syntheticAnswer.evidence[0]!.statement)),
    ).toBe(true);
  }
  await h.frame.getByRole('button', { name: 'Hide evidence' }).click();
  await expect(evidence).toHaveCount(0);
  expect(h.asks).toHaveLength(1);
});

for (const blank of ['', ' \n\t '])
  test(`Phase 6 rejects ${blank.length === 0 ? 'empty' : 'whitespace'} evidence without rendering empty bullets`, async ({
    page,
  }) => {
    const h = await panel(page);
    await page.route('https://forge-panel.test/api/ai/ask', (route) =>
      route.fulfill({
        contentType: 'application/x-ndjson',
        body: resultStream({
          ...syntheticAnswer,
          evidence: [{ id: 'blank', status: 'verified', statement: blank }],
        }),
      }),
    );
    await h.frame.getByLabel('Design prompt').fill('Explain this model');
    await h.frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(h.frame.getByRole('alert')).toContainText(
      'response could not be verified',
    );
    await expect(h.frame.locator('.ai-evidence li')).toHaveCount(0);
  });

for (const [selection, message] of [
  ['FACE', faceSelection],
  ['EDGE', edgeSelection],
] as const)
  test(`Phase 6 selected ${selection} keeps ownership unknown across all sections`, async ({
    page,
  }) => {
    const h = await panel(page);
    await h.send(message);
    await page.route('https://forge-panel.test/api/ai/ask', (route) => {
      expect(route.request().postDataJSON().selection).toBe(selection);
      return route.fulfill({
        contentType: 'application/x-ndjson',
        body: resultStream(syntheticSelectionAnswer(selection)),
      });
    });
    await h.frame
      .getByLabel('Design prompt')
      .fill(
        `What do you know about the ${selection.toLowerCase()} I selected?`,
      );
    await h.frame.getByRole('button', { name: 'Send prompt' }).click();
    await expect(
      h.frame.getByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
    await expect(
      h.frame.getByText(
        /Owning part, body, feature, dimensions.*are currently unknown/,
      ),
    ).toBeVisible();
    await expect(
      h.frame.getByText(/measurements aren't available yet/),
    ).toBeVisible();
    for (const name of [
      'Assumptions',
      'Suggestions · unverified',
      'To explore next',
    ])
      await expect(h.frame.getByRole('heading', { name })).toHaveCount(0);
    await h.frame.getByRole('button', { name: 'Evidence' }).click();
    for (const owner of ['body', 'part', 'feature'])
      await expect(
        h.frame.getByText(
          `The selected ${selection.toLowerCase()}'s owning ${owner} is unknown.`,
          { exact: true },
        ),
      ).toBeVisible();
    await expect(h.frame.locator('.ai-exchange')).not.toContainText(
      'belongs to',
    );
    await expect(h.frame.locator('.ai-exchange')).not.toContainText('Part 1');
    await expect(h.frame.locator('.ai-exchange')).not.toContainText(
      'Extrude 1',
    );
  });
