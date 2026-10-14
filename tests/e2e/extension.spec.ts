import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { signedIn, signedOut } from './auth-fixtures';
import {
  clearedSelection,
  edgeSelection,
  faceSelection,
} from '../../apps/web/src/onshape/__fixtures__/selection';
import { inspectorFixture } from '../../apps/web/src/cad/__fixtures__/inspector';
import { syntheticProof } from '../../apps/web/src/cad/__fixtures__/proof';
import { syntheticMassStructure } from '../../apps/web/src/cad/__fixtures__/massStructure';
import { syntheticBodyStructure } from '../../apps/web/src/cad/__fixtures__/bodyStructure';
import { capturedLaunchQuery } from '../../apps/web/src/onshape/__fixtures__/launch';

const search = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
// Test-owned responses simulate a parent at the actual origin; no Onshape request,
// account, token or CAD data is involved. Browser postMessage sets origin/source.
async function parentFixture(
  page: Page,
  query = search,
  authenticated = true,
  origin = 'https://cad.onshape.com',
  port = 4173,
) {
  await page.route('https://forge-panel.test/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/me') {
      await route.fulfill({ json: authenticated ? signedIn : signedOut });
    } else {
      const response = await page.request.get(
        `http://127.0.0.1:${port}${url.pathname}${url.search}`,
      );
      await route.fulfill({ response });
    }
  });
  await page.addInitScript(() => {
    try {
      localStorage.setItem(
        'forge.preferences.v1',
        JSON.stringify({ onboarded: true }),
      );
    } catch {
      /* restricted frame */
    }
  });
  await page.route(`${origin}/forge-panel-test`, (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Test Onshape parent</title></head><body style="margin:0"><script>window.received=[];addEventListener('message',e=>{if(e.origin==='https://forge-panel.test')window.received.push(e.data)});</script><iframe title="Forge extension" style="border:0;width:100vw;height:95vh" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
    }),
  );
  await page.goto(`${origin}/forge-panel-test`);
  return page.frameLocator('iframe');
}

async function inspectedLifecycle(page: Page) {
  const frame = await parentFixture(page);
  let reads = 0;
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    async (route) => {
      reads++;
      const params = new URL(route.request().url()).searchParams;
      const source = structuredClone(syntheticProof);
      if (
        params.get('documentId') !== 'a'.repeat(24) ||
        params.get('workspaceId') !== 'b'.repeat(24) ||
        params.get('elementId') !== 'c'.repeat(24)
      )
        for (const name of ['features', 'parts', 'bodies', 'mass'] as const)
          source[name].count = 0;
      await route.fulfill({ json: inspectorFixture(source) });
    },
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(dialog.getByText('Sketch 1', { exact: true })).toBeVisible();
  const send = async (data: unknown) =>
    page.evaluate(
      (data) =>
        document
          .querySelector('iframe')
          ?.contentWindow?.postMessage(data, 'https://forge-panel.test'),
      data,
    );
  await send(faceSelection);
  await expect(
    dialog.getByText('1 face selected', { exact: true }),
  ).toBeVisible();
  const child = page
    .frames()
    .find((f) => f.url().includes('forge-panel.test/extension'))!;
  return { frame, dialog, child, send, reads: () => reads };
}

test('Phase 5 lifecycle preserves same-frame inspection and FACE through browser visibility, focus and show', async ({
  page,
}) => {
  const h = await inspectedLifecycle(page);
  const capturedAt = await h.dialog.locator('time').getAttribute('datetime');
  const capturedText = await h.dialog.locator('time').textContent();
  let sessionChecks = 0;
  await page.route('https://forge-panel.test/api/me', async (route) => {
    sessionChecks++;
    await route.fulfill({ json: signedIn });
  });
  await h.child.evaluate(() => {
    for (const hidden of [true, false, true, false]) {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: hidden,
      });
      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        value: hidden ? 'hidden' : 'visible',
      });
      document.dispatchEvent(new Event('visibilitychange'));
      window.dispatchEvent(new Event(hidden ? 'blur' : 'focus'));
    }
    Reflect.deleteProperty(document, 'hidden');
    Reflect.deleteProperty(document, 'visibilityState');
  });
  await expect.poll(() => sessionChecks).toBeGreaterThan(0);
  await h.send({ messageName: 'show' });
  await expect(h.dialog.getByText('Sketch 1', { exact: true })).toBeVisible();
  await expect(
    h.dialog.getByText('1 face selected', { exact: true }),
  ).toBeVisible();
  await expect(h.dialog.locator('time')).toHaveAttribute(
    'datetime',
    capturedAt!,
  );
  await expect(h.dialog.locator('time')).toHaveText(capturedText!);
  await expect(h.dialog.getByText(/currentness unverified/)).toBeVisible();
  await expect(
    h.dialog.getByText(/Reopen the Forge panel|Selection needs refresh/),
  ).toHaveCount(0);
  expect(h.reads()).toBe(1);
  expect(
    await page.evaluate(
      () => (window as unknown as { received: object[] }).received.length,
    ),
  ).toBe(1);
  await h.send(clearedSelection);
  await expect(
    h.dialog.getByText('No selection', { exact: true }),
  ).toBeVisible();
  expect(h.reads()).toBe(1);
});

for (const field of ['documentId', 'workspaceOrVersionId', 'elementId']) {
  test(`Phase 5 lifecycle clears inspection and selection on real ${field} navigation`, async ({
    page,
  }) => {
    const h = await inspectedLifecycle(page);
    const query = new URLSearchParams(search);
    query.set(field, 'e'.repeat(24));
    await page.locator('iframe').evaluate((node, query) => {
      (node as HTMLIFrameElement).src =
        `https://forge-panel.test/extension?${query}`;
    }, query.toString());
    await h.frame.getByRole('button', { name: 'View CAD context' }).click();
    await expect(h.dialog.getByText('Sketch 1', { exact: true })).toHaveCount(
      0,
    );
    await expect(h.dialog.locator('time')).toHaveCount(0);
    await expect(
      h.dialog.getByText('Waiting for selection context', { exact: true }),
    ).toBeVisible();
    expect(h.reads()).toBe(1);
    await h.dialog.getByRole('button', { name: 'Refresh CAD' }).click();
    await expect(
      h.dialog.getByText('0 features', { exact: true }),
    ).toBeVisible();
    expect(h.reads()).toBe(2);
  });
}

for (const change of ['logout', 'disconnected', 'revoked']) {
  test(`Phase 5 lifecycle clears inspection when focus detects ${change}`, async ({
    page,
  }) => {
    const h = await inspectedLifecycle(page);
    await page.route('https://forge-panel.test/api/me', (route) =>
      route.fulfill({
        json:
          change === 'logout' ? signedOut : { ...signedIn, connection: change },
      }),
    );
    await h.child.evaluate(() => window.dispatchEvent(new Event('focus')));
    await expect(h.frame.getByText('Sketch 1', { exact: true })).toHaveCount(0);
    await expect(h.frame.locator('time')).toHaveCount(0);
    await expect(
      h.frame.getByRole('button', { name: 'Refresh CAD' }),
    ).toHaveCount(0);
    expect(h.reads()).toBe(1);
  });
}

test('Phase 5 lifecycle panel destruction starts a fresh same-context frame and initialization', async ({
  page,
}) => {
  const h = await inspectedLifecycle(page);
  await page.evaluate(() => {
    const old = document.querySelector('iframe')!;
    const replacement = old.cloneNode() as HTMLIFrameElement;
    old.remove();
    document.body.appendChild(replacement);
  });
  await h.frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(h.dialog.getByText('Sketch 1', { exact: true })).toHaveCount(0);
  await expect(
    h.dialog.getByText('Waiting for selection context', { exact: true }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { received: object[] }).received.length,
      ),
    )
    .toBe(2);
  expect(h.reads()).toBe(1);
  await h.dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(h.dialog.getByText('Sketch 1', { exact: true })).toBeVisible();
  expect(h.reads()).toBe(2);
});

test('Phase 5 lifecycle ignores untrusted messages, clears malformed evidence and blocks genuine mismatch resurrection', async ({
  page,
}) => {
  const h = await inspectedLifecycle(page);
  await h.child.evaluate(
    (data) => window.postMessage(data, 'https://forge-panel.test'),
    edgeSelection,
  );
  await expect(
    h.dialog.getByText('1 face selected', { exact: true }),
  ).toBeVisible();
  await h.send({
    messageName: 'SELECTION',
    selections: [{ entityType: 'FACE' }],
  });
  await expect(h.dialog.getByText('Sketch 1', { exact: true })).toHaveCount(0);
  await expect(
    h.dialog.getByText('Selection details unavailable', { exact: true }),
  ).toBeVisible();
  await h.send({ messageName: 'show' });
  await expect(
    h.dialog.getByRole('button', { name: 'Refresh CAD' }),
  ).toHaveCount(0);
  await h.send(clearedSelection);
  await expect(
    h.dialog.getByRole('button', { name: 'Refresh CAD' }),
  ).toBeEnabled();
  expect(h.reads()).toBe(1);
  await h.dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(h.dialog.getByText('Sketch 1', { exact: true })).toBeVisible();
  await h.send({ ...faceSelection, elementId: 'e'.repeat(24) });
  await expect(
    h.dialog.getByText('Document context could not be validated', {
      exact: true,
    }),
  ).toBeVisible();
  await expect(h.dialog.getByText('Sketch 1', { exact: true })).toHaveCount(0);
  await h.send({ messageName: 'show' });
  await h.send(faceSelection);
  await expect(
    h.dialog.getByRole('button', { name: 'Refresh CAD' }),
  ).toHaveCount(0);
  expect(h.reads()).toBe(2);
});

for (const development of [true, false]) {
  test(`Phase 5 topology unknowns and structure capture in ${development ? 'development' : 'production'}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 950 });
    const frame = await parentFixture(
      page,
      search,
      true,
      'https://cad.onshape.com',
      development ? 4174 : 4173,
    );
    const result = inspectorFixture();
    result.bodies.items[0]!.edge_count = null;
    result.bodies.items[0]!.vertex_count = null;
    result.bodies.completeness = 'partial';
    await page.route(
      'https://forge-panel.test/api/onshape/part-studio/inspector?*',
      (route) =>
        route.fulfill({
          json: result,
          headers: {
            'X-Forge-Body-Structure': JSON.stringify(syntheticBodyStructure),
          },
        }),
    );
    await frame.getByRole('button', { name: 'View CAD context' }).click();
    const dialog = frame.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
    await dialog.locator('summary').filter({ hasText: 'Body 1' }).click();
    const body = dialog
      .locator('details.inspector-item')
      .filter({ has: frame.locator('summary').filter({ hasText: 'Body 1' }) });
    await expect(body.locator('dd')).toHaveText(['6', 'Unknown', 'Unknown']);
    const textbox = dialog.getByRole('textbox', {
      name: 'Sanitized body response structure',
    });
    if (development) {
      await expect(textbox).toBeVisible();
      await expect(textbox).toHaveAttribute('readonly', '');
      expect(await textbox.inputValue()).toBe(
        JSON.stringify(syntheticBodyStructure, null, 2),
      );
      await textbox.evaluate((node: HTMLTextAreaElement) => {
        node.focus();
        node.select();
      });
      expect(
        await textbox.evaluate(
          (node: HTMLTextAreaElement) =>
            node.selectionEnd - node.selectionStart,
        ),
      ).toBe((await textbox.inputValue()).length);
      const bounds = await textbox.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(320);
    } else {
      await expect(textbox).toHaveCount(0);
      await expect(dialog.getByText(/DEVELOPMENT ONLY/)).toHaveCount(0);
    }
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
    await dialog.getByRole('button', { name: 'Close dialog' }).click();
  });
}

test('actual parent messaging initializes once, ignores unsupported payloads and resets on element navigation', async ({
  page,
}) => {
  await page.setViewportSize({ width: 380, height: 950 });
  const frame = await parentFixture(page);
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await expect(dialog.getByText('Onshape launch context')).toBeVisible();
  await expect(
    frame.getByRole('button', { name: 'Show sanitized launch diagnostic' }),
  ).toHaveCount(0);
  await expect(
    frame.getByRole('button', {
      name: 'Enable sanitized selection diagnostic',
    }),
  ).toHaveCount(0);
  await page.screenshot({
    path: `.cache/phase3/embedded-${test.info().project.name}.png`,
    fullPage: true,
  });
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { received: object[] }).received,
      ),
    )
    .toEqual([
      {
        messageName: 'applicationInit',
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
      },
    ]);
  await page.evaluate(() => {
    const child = document.querySelector('iframe')?.contentWindow;
    child?.postMessage(
      { messageName: 'SELECTION', selections: [{ entityType: 'FACE' }] },
      'https://forge-panel.test',
    );
    child?.postMessage(
      { messageName: 'contextChanged', documentId: 'd'.repeat(24) },
      'https://forge-panel.test',
    );
    child?.postMessage(
      { messageName: 'show', extra: true },
      'https://forge-panel.test',
    );
  });
  await expect(dialog.getByText('Selection details unavailable')).toBeVisible();
  await page.evaluate(() =>
    document
      .querySelector('iframe')
      ?.contentWindow?.postMessage(
        { messageName: 'show' },
        'https://forge-panel.test',
      ),
  );
  await expect(dialog.getByText('Selection details unavailable')).toBeVisible();
  await page.locator('iframe').evaluate((node, query) => {
    (node as HTMLIFrameElement).src =
      `https://forge-panel.test/extension?${query.replace('c'.repeat(24), 'd'.repeat(24))}`;
  }, search);
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(
    frame.getByRole('dialog').getByText('Current element'),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { received: object[] }).received,
      ),
    )
    .toEqual([
      {
        messageName: 'applicationInit',
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
      },
      {
        messageName: 'applicationInit',
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'd'.repeat(24),
      },
    ]);
  await expect(
    frame.getByRole('dialog').getByText('Waiting for selection context'),
  ).toBeVisible();
});

test('workspace-style launch reaches the Design composer and initializes once', async ({
  page,
}) => {
  const query = search.replace(
    'workspaceOrVersion=w&workspaceOrVersionId=',
    'workspaceId=',
  );
  await page.setViewportSize({ width: 380, height: 950 });
  const frame = await parentFixture(page, query);
  await expect(
    frame.getByText('Onshape workspace context', { exact: true }),
  ).toBeVisible();
  await expect(frame.getByText('No CAD context', { exact: true })).toHaveCount(
    0,
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(
    frame.getByRole('dialog').getByText('Onshape launch context'),
  ).toBeVisible();
  await expect(
    frame.getByRole('dialog').getByText('Workspace', { exact: true }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { received: object[] }).received,
      ),
    )
    .toEqual([
      {
        messageName: 'applicationInit',
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
      },
    ]);
});

test('explicit version context is displayed without a workspace initialization', async ({
  page,
}) => {
  const frame = await parentFixture(
    page,
    search.replace('workspaceOrVersion=w', 'workspaceOrVersion=v'),
  );
  await expect(
    frame.getByText('Onshape version context · messaging unverified', {
      exact: true,
    }),
  ).toBeVisible();
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(
    frame.getByRole('dialog').getByText('Version', { exact: true }),
  ).toBeVisible();
  await expect(
    frame
      .getByRole('dialog')
      .getByText(
        'Version context is available. Client messaging for versions is not verified.',
      ),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => (window as unknown as { received: object[] }).received,
    ),
  ).toEqual([]);
});

test('iframe session unavailable uses fixed safe actions and never stores launch IDs or credentials', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 950 });
  const frame = await parentFixture(page, search, false);
  await expect(
    frame.getByText(/Your Forge session is unavailable/),
  ).toBeVisible();
  await expect(
    frame.getByRole('link', { name: 'Continue with Onshape' }),
  ).toHaveAttribute('target', '_top');
  await expect(
    frame.getByRole('link', { name: 'Open Forge in a new tab' }),
  ).toHaveAttribute('href', '/');
  await frame.getByRole('button', { name: 'Check panel session' }).click();
  await page.screenshot({
    path: `.cache/phase3/auth-unavailable-${test.info().project.name}.png`,
    fullPage: true,
  });
  const child = page
    .frames()
    .find((item) => item.url().includes('/extension?'));
  expect(child).toBeDefined();
  const stored = await child!.evaluate(() =>
    JSON.stringify({
      local: { ...localStorage },
      session: { ...sessionStorage },
    }),
  );
  expect(stored).not.toMatch(
    /access_token|refresh_token|csrf_token|documentId|workspaceId|elementId/,
  );
});

test('CSP prevents arbitrary parents and query origins cannot expand the allowlist', async ({
  page,
  request,
}) => {
  const response = await request.get('/extension');
  expect(response.headers()['content-security-policy']).toBe(
    'frame-ancestors https://cad.onshape.com',
  );
  expect(response.headers()['referrer-policy']).toBe('no-referrer');
  const frame = await parentFixture(
    page,
    search.replace('https://cad.onshape.com', 'https://evil.example'),
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(
    frame.getByRole('dialog').getByText('Onshape origin could not be verified'),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => (window as unknown as { received: object[] }).received,
    ),
  ).toEqual([]);
});

test('production excludes the simulator and its selection fixtures', async ({
  page,
  request,
}) => {
  await page.route('**/api/me', (route) => route.fulfill({ json: signedOut }));
  await page.goto('/?diagnostics=true#/onshape-simulator');
  await expect(
    page.getByRole('link', { name: 'Continue with Onshape' }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Onshape context simulator' }),
  ).toHaveCount(0);
  const scripts = await page
    .locator('script[src]')
    .evaluateAll((nodes) =>
      nodes.map((node) => (node as HTMLScriptElement).src),
    );
  for (const src of scripts) {
    const source = await (await request.get(src)).text();
    expect(source).not.toContain('No scenario applied');
    expect(source).not.toContain('forge-selection-structure-v1');
    expect(source).not.toContain('forge-launch-diagnostic-v1');
    expect(source).not.toContain('forge-rest-diagnostic-v1');
    expect(source).not.toContain('forge-mass-structure-v1');
    expect(source).not.toContain('position0_vs_position1');
    expect(source).not.toContain('negative_component');
    expect(source).not.toContain('negative_nominal');
    expect(source).not.toContain('failedPredicates');
    expect(source).not.toContain('massSigns');
    expect(source).not.toContain('massMissingCountCategory');
    expect(source).not.toContain('X-Forge-Mass-Structure');
    expect(source).not.toContain('Sanitized mass response structure');
    expect(source).not.toContain('Copy sanitized read diagnostic');
    expect(source).not.toContain(
      'select and copy the sanitized diagnostic below',
    );
    expect(source).not.toContain(
      'Sanitized read diagnostic exceeds the size limit',
    );
    expect(source).not.toContain('synthetic.client:');
    expect(source).not.toContain('synthetic-edge-reference');
    expect(source).not.toContain('synthetic-face-reference');
    expect(source).not.toContain('Show sanitized launch diagnostic');
    expect(source).not.toContain('Copy sanitized structure');
    expect(source).not.toContain('Enable sanitized selection diagnostic');
  }
  await expect(
    page.getByRole('button', { name: 'Enable sanitized selection diagnostic' }),
  ).toHaveCount(0);
});

for (const width of [320, 380, 480, 1280]) {
  for (const theme of ['light', 'dark'] as const) {
    test(`context visual states ${width}px ${theme}`, async ({
      page,
      browserName,
    }) => {
      await page.setViewportSize({ width, height: 950 });
      await page.goto('http://127.0.0.1:4174/#/onshape-simulator');
      await page
        .getByRole('combobox', { name: 'Theme', exact: true })
        .selectOption(theme);
      const scenarios = [
        'Standalone',
        'Initializing',
        'Valid launch context',
        'No selection',
        'Single face',
        'Multiple edges',
        'Clear selection',
        'Change element',
        'Change document',
        'Invalid context',
        'Untrusted server',
        'Auth unavailable',
        'Invalid message origin',
        'Malformed message',
        'Unsupported message',
      ];
      for (const scenario of scenarios) {
        await page.getByRole('button', { name: scenario, exact: true }).click();
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        if (browserName === 'chromium')
          await page.screenshot({
            path: `.cache/phase3/${width}-${theme}-${scenario.replaceAll(' ', '-')}.png`,
            fullPage: true,
          });
      }
      await expect(
        page.getByText('Boundary probe rejected; displayed context unchanged'),
      ).toBeVisible();
      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    });
  }
}

test('DEV diagnostic captures only sanitized trusted-parent structure and is usable without iframe auth', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 380, height: 950 });
  await parentFixture(
    page,
    search.replace(
      'workspaceOrVersion=w&workspaceOrVersionId=',
      'workspaceId=',
    ),
    false,
    'https://cad.onshape.com',
    4174,
  );
  const frame = page.frameLocator('iframe[title="Forge extension"]');
  const panel = frame.getByRole('region', {
    name: 'Development selection diagnostic',
  });
  await expect(
    panel.getByRole('button', {
      name: 'Enable sanitized selection diagnostic',
    }),
  ).toBeVisible();
  await page.evaluate(() =>
    document.querySelector('iframe')?.contentWindow?.postMessage(
      {
        messageName: 'SELECTION',
        data: { entityType: 'FACE', entityId: 'private-before-enable' },
      },
      'https://forge-panel.test',
    ),
  );
  await expect(panel.getByLabel('Sanitized structure')).toHaveCount(0);
  await panel
    .getByRole('button', { name: 'Enable sanitized selection diagnostic' })
    .click();
  // Two actual sibling senders: one wrong origin, one approved origin but wrong source.
  for (const origin of [
    'https://untrusted.example',
    'https://cad.onshape.com',
  ]) {
    await page.route(`${origin}/sender`, (route) =>
      route.fulfill({
        contentType: 'text/html',
        body: `<script>parent.frames[0].postMessage({messageName:'SELECTION',data:{entityType:'EDGE',id:'private-sibling'}},'https://forge-panel.test')</script>`,
      }),
    );
    await page.evaluate(async (url) => {
      const sender = document.createElement('iframe');
      sender.hidden = true;
      const loaded = new Promise<void>((resolve) => {
        sender.onload = () => resolve();
      });
      sender.src = url;
      document.body.append(sender);
      await loaded;
    }, `${origin}/sender`);
  }
  await expect(panel.getByLabel('Sanitized structure')).toHaveCount(0);
  await page.evaluate(() =>
    document.querySelector('iframe')?.contentWindow?.postMessage(
      {
        messageName: 'SELECTION',
        data: {
          entities: [{ entityType: 'FACE', entityId: 'private-real-id' }],
          documentId: 'a'.repeat(24),
          access_token: 'private-credential',
          'Private customer design': 'private-name',
        },
      },
      'https://forge-panel.test',
    ),
  );
  const output = panel.getByLabel('Sanitized structure');
  await expect(output).toHaveValue(/"category": "FACE"/);
  const sanitized = await output.inputValue();
  for (const value of [
    'private-real-id',
    'private-credential',
    'Private customer design',
    'private-name',
    'a'.repeat(24),
  ])
    expect(sanitized).not.toContain(value);
  const child = page
    .frames()
    .find((entry) => entry.url().includes('forge-panel.test/extension'))!;
  await child.evaluate(() =>
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          (window as unknown as { copiedStructure: string }).copiedStructure =
            text;
        },
      },
    }),
  );
  await panel.getByRole('button', { name: 'Copy sanitized structure' }).click();
  expect(
    await child.evaluate(
      () => (window as unknown as { copiedStructure: string }).copiedStructure,
    ),
  ).toBe(sanitized);
  expect(
    await child.evaluate(() =>
      JSON.stringify({ ...localStorage, ...sessionStorage }),
    ),
  ).not.toContain('forge-selection-structure-v1');
  for (const width of [320, 380, 480]) {
    await page.setViewportSize({ width, height: 950 });
    for (const theme of ['light', 'dark']) {
      await child.evaluate((theme) => {
        document.documentElement.dataset.theme = theme;
      }, theme);
      await panel.scrollIntoViewIfNeeded();
      expect(
        await child.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      if (browserName === 'chromium')
        await page.screenshot({
          path: `.cache/phase3/diagnostic-${width}-${theme}.png`,
          fullPage: true,
        });
    }
  }
  await panel.getByRole('button', { name: 'Clear diagnostic' }).click();
  await expect(output).toHaveCount(0);
  await page.evaluate(() =>
    document
      .querySelector('iframe')
      ?.contentWindow?.postMessage(
        { messageName: 'SELECTION', data: { entities: [] } },
        'https://forge-panel.test',
      ),
  );
  await expect(output).toHaveValue(/"length": 0/);
  await panel.getByRole('button', { name: 'Disable diagnostic' }).click();
  await expect(output).toHaveCount(0);
  await expect(
    panel.getByRole('button', {
      name: 'Enable sanitized selection diagnostic',
    }),
  ).toBeVisible();
});

for (const authenticated of [true, false]) {
  test(`DEV launch diagnostic remains available for invalid context (authenticated=${authenticated}) and exposes no query values`, async ({
    page,
    browserName,
  }) => {
    const query =
      search.replace(
        'workspaceOrVersion=w&workspaceOrVersionId=',
        'workspaceId=',
      ) +
      `&clientId=${'x'.repeat(129)}&applicationId=synthetic-private-application&userId=` +
      'd'.repeat(24) +
      '&companyId=' +
      'e'.repeat(24) +
      '&access_token=synthetic-private-credential';
    await page.setViewportSize({ width: 320, height: 950 });
    const frame = await parentFixture(
      page,
      query,
      authenticated,
      'https://cad.onshape.com',
      4174,
    );
    if (authenticated) {
      await frame.getByRole('button', { name: 'View CAD context' }).click();
      await expect(
        frame
          .getByRole('dialog')
          .getByText('Document context could not be validated'),
      ).toBeVisible();
      await page.keyboard.press('Escape');
    } else {
      await expect(
        frame.getByText('Document context could not be validated'),
      ).toBeVisible();
      await expect(
        frame.getByText(/Your Forge session is unavailable/),
      ).toBeVisible();
    }
    const panel = frame.getByRole('region', {
      name: 'Development launch diagnostic',
    });
    await panel
      .getByRole('button', { name: 'Show sanitized launch diagnostic' })
      .click();
    const output = panel.getByLabel('Sanitized launch context');
    await expect(output).toHaveValue(/invalid-opaque-metadata/);
    const report = await output.inputValue();
    expect(report).toContain('unexpected-parameter');
    expect(report).toContain('applicationId');
    for (const value of [
      'x'.repeat(129),
      'synthetic-private-application',
      'synthetic-private-credential',
      ...['a', 'b', 'c', 'd', 'e'].map((letter) => letter.repeat(24)),
    ])
      expect(report).not.toContain(value);
    expect(
      await page.evaluate(
        () => (window as unknown as { received: object[] }).received,
      ),
    ).toEqual([]);
    const child = page
      .frames()
      .find((entry) => entry.url().includes('forge-panel.test/extension'))!;
    await child.evaluate(() =>
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: {
          writeText: async (text: string) => {
            (window as unknown as { copiedLaunch: string }).copiedLaunch = text;
          },
        },
      }),
    );
    await panel
      .getByRole('button', { name: 'Copy sanitized launch diagnostic' })
      .click();
    expect(
      await child.evaluate(
        () => (window as unknown as { copiedLaunch: string }).copiedLaunch,
      ),
    ).toBe(report);
    expect(
      await child.evaluate(() =>
        JSON.stringify({ ...localStorage, ...sessionStorage }),
      ),
    ).not.toContain('forge-launch-diagnostic-v1');
    for (const width of [320, 380, 480]) {
      await page.setViewportSize({ width, height: 950 });
      for (const theme of ['light', 'dark']) {
        await child.evaluate((theme) => {
          document.documentElement.dataset.theme = theme;
        }, theme);
        await panel.scrollIntoViewIfNeeded();
        expect(
          await child.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        if (browserName === 'chromium')
          await page.screenshot({
            path: `.cache/launch-diagnostic/${width}-${theme}-${authenticated}.png`,
          });
      }
    }
    await panel
      .getByRole('button', { name: 'Clear launch diagnostic' })
      .click();
    await expect(output).toHaveCount(0);
  });
}

test('captured metadata shape normalizes, initializes once and keeps diagnostics sanitized', async ({
  page,
}) => {
  const frame = await parentFixture(
    page,
    capturedLaunchQuery.slice(1),
    true,
    'https://cad.onshape.com',
    4174,
  );
  await expect(
    frame.getByText('Onshape workspace context', { exact: true }),
  ).toBeVisible();
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(
    frame.getByRole('dialog').getByText('Onshape launch context'),
  ).toBeVisible();
  await expect(
    frame.getByRole('dialog').getByText('Workspace', { exact: true }),
  ).toBeVisible();
  await page.keyboard.press('Escape');
  await frame
    .getByRole('button', { name: 'Show sanitized launch diagnostic' })
    .click();
  const output = frame.getByLabel('Sanitized launch context');
  await expect(output).toHaveValue(/"parserReason": "valid-context"/);
  expect(JSON.parse(await output.inputValue()).reasonCodes).toEqual([]);
  expect(await output.inputValue()).not.toContain('synthetic.client:');
  await expect(
    frame.getByRole('button', {
      name: 'Enable sanitized selection diagnostic',
    }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => (window as unknown as { received: object[] }).received,
      ),
    )
    .toEqual([
      {
        messageName: 'applicationInit',
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
      },
    ]);
});

for (const key of ['documentId', 'workspaceId', 'elementId']) {
  test(`live-shape selection replaces/clears without exposing references; fresh ${key} navigation resets`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width: 380, height: 950 });
    const frame = await parentFixture(page, capturedLaunchQuery.slice(1));
    await expect(
      frame.getByText('Onshape workspace context', { exact: true }),
    ).toBeVisible();
    await frame.getByRole('button', { name: 'View CAD context' }).click();
    const dialog = frame.getByRole('dialog');
    const send = async (data: unknown) =>
      page.evaluate(
        (data) =>
          document
            .querySelector('iframe')
            ?.contentWindow?.postMessage(data, 'https://forge-panel.test'),
        data,
      );
    for (const [data, label] of [
      [faceSelection, '1 face selected'],
      [edgeSelection, '1 edge selected'],
      [clearedSelection, 'No selection'],
    ] as const) {
      await send(data);
      await expect(dialog.getByText(label, { exact: true })).toBeVisible();
      await expect(frame.locator('body')).not.toContainText(
        'synthetic-face-reference',
      );
      await expect(frame.locator('body')).not.toContainText(
        'synthetic-edge-reference',
      );
    }
    await send(edgeSelection);
    // Actual sibling messages exercise browser-generated origin AND source.
    for (const origin of [
      'https://untrusted.example',
      'https://cad.onshape.com',
    ]) {
      await page.route(`${origin}/selection-sender`, (route) =>
        route.fulfill({
          contentType: 'text/html',
          body: `<script>parent.frames[0].postMessage({messageName:'SELECTION',selections:[]},'https://forge-panel.test')</script>`,
        }),
      );
      await page.evaluate(async (url) => {
        const sender = document.createElement('iframe');
        sender.hidden = true;
        const loaded = new Promise<void>((resolve) => {
          sender.onload = () => resolve();
        });
        sender.src = url;
        document.body.append(sender);
        await loaded;
        sender.remove();
      }, `${origin}/selection-sender`);
    }
    await expect(
      dialog.getByText('1 edge selected', { exact: true }),
    ).toBeVisible();
    await send({ messageName: 'SELECTION', selections: [{}] });
    await expect(
      dialog.getByText('Selection details unavailable'),
    ).toBeVisible();
    await send(faceSelection);
    const child = page
      .frames()
      .find((item) => item.url().includes('forge-panel.test/extension'))!;
    expect(
      await child.evaluate(() =>
        JSON.stringify({
          local: { ...localStorage },
          session: { ...sessionStorage },
        }),
      ),
    ).not.toMatch(
      /synthetic-.*-reference|selectionId|documentId|workspaceId|elementId|access_token|refresh_token/,
    );
    if (key === 'elementId' && browserName === 'chromium') {
      for (const width of [320, 380, 480]) {
        await page.setViewportSize({ width, height: 950 });
        for (const theme of ['light', 'dark']) {
          await child.evaluate((theme) => {
            document.documentElement.dataset.theme = theme;
          }, theme);
          expect(
            await child.evaluate(
              () => document.documentElement.scrollWidth <= innerWidth,
            ),
          ).toBe(true);
          await page.screenshot({
            path: `.cache/phase3/live-selection-${width}-${theme}.png`,
            fullPage: true,
          });
        }
      }
    }
    const query = new URLSearchParams(capturedLaunchQuery);
    query.set(key, 'e'.repeat(24));
    await page
      .locator('iframe[title="Forge extension"]')
      .evaluate((node, query) => {
        (node as HTMLIFrameElement).src =
          `https://forge-panel.test/extension?${query}`;
      }, query.toString());
    await frame.getByRole('button', { name: 'View CAD context' }).click();
    await expect(dialog.getByText('Current document')).toBeVisible();
    await expect(
      dialog.getByText('Waiting for selection context'),
    ).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(
          () => (window as unknown as { received: object[] }).received.length,
        ),
      )
      .toBe(2);
  });
}

test('Phase 4 explicit read shows bounded summary, loading, accessibility and context invalidation', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 380, height: 950 });
  const frame = await parentFixture(page);
  let calls = 0;
  let release!: () => void;
  const ready = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    async (route) => {
      ++calls;
      expect(route.request().method()).toBe('GET');
      expect(route.request().headers()['x-csrf-token']).toBe(
        signedIn.csrf_token,
      );
      const query = new URL(route.request().url()).searchParams;
      expect([...query.keys()].sort()).toEqual([
        'documentId',
        'elementId',
        'revisionKind',
        'workspaceId',
      ]);
      await ready;
      await route.fulfill({ json: inspectorFixture() });
    },
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  expect(calls).toBe(0);
  await dialog
    .getByRole('button', { name: 'Refresh CAD', exact: true })
    .click();
  await expect(
    dialog.getByRole('button', { name: 'Reading CAD data…' }),
  ).toBeDisabled();
  release();
  await expect(dialog.getByText('Onshape data connected')).toBeVisible();
  await expect(dialog.getByText('2 features', { exact: true })).toBeVisible();
  await expect(dialog.getByText('1 part', { exact: true })).toBeVisible();
  await expect(dialog.getByText('Mass properties available')).toBeVisible();
  await expect(
    dialog.getByText(/single consistent CAD version is unverified/),
  ).toBeVisible();
  await expect(dialog.getByText(/DEVELOPMENT ONLY/)).toHaveCount(0);
  expect(calls).toBe(1);
  for (const value of [
    'a'.repeat(24),
    'b'.repeat(24),
    'c'.repeat(24),
    'access_token',
    'btType',
  ])
    await expect(dialog).not.toContainText(value);
  const child = page
    .frames()
    .find((item) => item.url().includes('forge-panel.test/extension'))!;
  for (const width of [320, 380, 480, 1280]) {
    await page.setViewportSize({ width, height: 950 });
    for (const theme of ['light', 'dark']) {
      await child.evaluate((theme) => {
        document.documentElement.dataset.theme = theme;
      }, theme);
      expect(
        await child.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      if (browserName === 'chromium')
        await page.screenshot({
          path: `.cache/phase4/read-${width}-${theme}.png`,
          fullPage: true,
        });
    }
  }
  const accessibility = await new AxeBuilder({ page })
    .include('iframe')
    .analyze();
  expect(accessibility.violations).toEqual([]);
  const query = new URLSearchParams(search);
  query.set('elementId', 'e'.repeat(24));
  await page
    .locator('iframe[title="Forge extension"]')
    .evaluate((node, query) => {
      (node as HTMLIFrameElement).src =
        `https://forge-panel.test/extension?${query}`;
    }, query.toString());
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(dialog.getByText('Onshape data connected')).toHaveCount(0);
  expect(calls).toBe(1);
});

for (const [status, code, message] of [
  [
    'unauthorized',
    'read_permission_required',
    'Additional Onshape read permission required',
  ],
  [
    'forbidden',
    'permission_or_access_required',
    'Check the app’s document-read permission',
  ],
  ['forbidden', 'document_forbidden', 'Access to this document is forbidden'],
  ['rate_limited', 'rate_limited', 'Onshape API rate limit reached'],
  [
    'provider_failure',
    'provider_unavailable',
    'Onshape temporarily unavailable',
  ],
] as const) {
  test(`Phase 4 read safely presents ${code}`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 950 });
    const frame = await parentFixture(page);
    const section = {
      status,
      code,
      count: null,
      retry_after_seconds: status === 'rate_limited' ? 120 : null,
    };
    await page.route(
      'https://forge-panel.test/api/onshape/part-studio/inspector?*',
      (route) =>
        route.fulfill({
          json: inspectorFixture({
            ...syntheticProof,
            features: section,
            parts: section,
            bodies: section,
            mass: section,
            has_mass: null,
          }),
        }),
    );
    await frame.getByRole('button', { name: 'View CAD context' }).click();
    const dialog = frame.getByRole('dialog');
    await dialog
      .getByRole('button', { name: 'Refresh CAD', exact: true })
      .click();
    await expect(
      dialog.getByText(message, { exact: false }).first(),
    ).toBeVisible();
    await expect(dialog.getByText('Onshape data connected')).toHaveCount(0);
    await expect(dialog.getByText(/not found/)).toHaveCount(0);
  });
}

test('Phase 4 successfully read missing mass preserves CAD counts without a provider error', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 950 });
  const frame = await parentFixture(page);
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    (route) =>
      route.fulfill({
        json: inspectorFixture({ ...syntheticProof, has_mass: false }),
      }),
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog
    .getByRole('button', { name: 'Refresh CAD', exact: true })
    .click();
  await expect(dialog.getByText('Onshape data connected')).toBeVisible();
  await expect(dialog.getByText('2 features')).toBeVisible();
  await expect(dialog.getByText('1 part')).toBeVisible();
  await expect(dialog.getByText('1 body')).toBeVisible();
  await expect(
    dialog.getByText('Mass unavailable; material/density may be missing'),
  ).toBeVisible();
  await expect(dialog.getByText('Mass properties available')).toHaveCount(0);
  await expect(
    dialog.getByText(/Onshape returned data Forge could not verify/),
  ).toHaveCount(0);
  await expect(
    dialog.getByRole('textbox', { name: 'Sanitized mass response structure' }),
  ).toHaveCount(0);
  await expect(dialog).not.toContainText(/nominal|massSigns|principalAxes/);
});

test('Phase 4 development diagnostic copies only fixed metadata', async ({
  page,
}) => {
  const frame = await parentFixture(
    page,
    search,
    true,
    'https://cad.onshape.com',
    4174,
  );
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    (route) => route.fulfill({ json: inspectorFixture() }),
  );
  const child = page
    .frames()
    .find((item) => item.url().includes('forge-panel.test/extension'))!;
  await child.evaluate(() =>
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          (window as unknown as { copiedRead: string }).copiedRead = text;
        },
      },
    }),
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog
    .getByRole('button', { name: 'Refresh CAD', exact: true })
    .click();
  await expect(
    dialog.getByText(/DEVELOPMENT ONLY · REST diagnostic/),
  ).toBeVisible();
  await dialog
    .getByRole('button', { name: 'Copy sanitized read diagnostic' })
    .click();
  const copied = await child.evaluate(
    () => (window as unknown as { copiedRead: string }).copiedRead,
  );
  expect(copied).toContain('forge-rest-diagnostic-v1');
  expect(copied.length).toBeLessThan(2000);
  expect(copied).not.toMatch(
    /count|has_mass|token|documentId|workspaceId|elementId|raw/,
  );
  await expect(
    dialog.getByRole('textbox', { name: 'Sanitized read diagnostic' }),
  ).toHaveCount(0);
});

for (const clipboard of ['missing', 'rejected'] as const) {
  test(`Phase 4 development diagnostic offers manual copying with ${clipboard} clipboard`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 950 });
    const frame = await parentFixture(
      page,
      search,
      true,
      'https://cad.onshape.com',
      4174,
    );
    await page.route(
      'https://forge-panel.test/api/onshape/part-studio/inspector?*',
      (route) =>
        route.fulfill({
          json: inspectorFixture({
            ...syntheticProof,
            has_mass: null,
            mass: {
              status: 'provider_failure',
              code: 'invalid_response',
              count: null,
              retry_after_seconds: null,
            },
          }),
        }),
    );
    const child = page
      .frames()
      .find((item) => item.url().includes('forge-panel.test/extension'))!;
    await child.evaluate(
      (failure) =>
        Object.defineProperty(navigator, 'clipboard', {
          configurable: true,
          value:
            failure === 'missing'
              ? undefined
              : {
                  writeText: async (text: string) => {
                    (
                      window as unknown as { attemptedRead: string }
                    ).attemptedRead = text;
                    throw new Error('Denied');
                  },
                },
        }),
      clipboard,
    );
    await frame.getByRole('button', { name: 'View CAD context' }).click();
    const dialog = frame.getByRole('dialog');
    await dialog
      .getByRole('button', { name: 'Refresh CAD', exact: true })
      .click();
    await expect(
      dialog.getByText('Onshape returned data Forge could not verify.'),
    ).toBeVisible();
    const textbox = dialog.getByRole('textbox', {
      name: 'Sanitized read diagnostic',
    });
    await expect(textbox).toHaveCount(0);
    await dialog
      .getByRole('button', { name: 'Copy sanitized read diagnostic' })
      .click();
    await expect(
      dialog.getByText(
        'Clipboard unavailable — select and copy the sanitized diagnostic below.',
      ),
    ).toBeVisible();
    await expect(textbox).toBeVisible();
    await expect(textbox).toHaveAttribute('readonly', '');
    const text = await textbox.inputValue();
    expect(text.length).toBeLessThanOrEqual(2000);
    expect(JSON.parse(text).sections.mass).toEqual({
      status: 'provider_failure',
      code: 'invalid_response',
      retryAfterSeconds: null,
    });
    expect(text).not.toMatch(
      /count|has_mass|token|secret|documentId|workspaceId|elementId|selection|raw|https?:/,
    );
    for (const id of ['a', 'b', 'c']) expect(text).not.toContain(id.repeat(24));
    if (clipboard === 'rejected')
      expect(text).toBe(
        await child.evaluate(
          () => (window as unknown as { attemptedRead: string }).attemptedRead,
        ),
      );
    await textbox.evaluate((node: HTMLTextAreaElement) => {
      node.focus();
      node.select();
    });
    expect(
      await textbox.evaluate(
        (node: HTMLTextAreaElement) => node.selectionEnd - node.selectionStart,
      ),
    ).toBe(text.length);
    const bounds = await textbox.boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(320);
    expect(bounds!.height).toBeLessThanOrEqual(256);
  });
}

test('Phase 4 development diagnostic shows only validated mass structure for manual capture', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 950 });
  const frame = await parentFixture(
    page,
    search,
    true,
    'https://cad.onshape.com',
    4174,
  );
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    (route) =>
      route.fulfill({
        json: inspectorFixture({
          ...syntheticProof,
          has_mass: null,
          mass: {
            status: 'provider_failure',
            code: 'invalid_response',
            count: null,
            retry_after_seconds: null,
          },
        }),
        headers: {
          'X-Forge-Mass-Structure': JSON.stringify(syntheticMassStructure),
        },
      }),
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog
    .getByRole('button', { name: 'Refresh CAD', exact: true })
    .click();
  const textbox = dialog.getByRole('textbox', {
    name: 'Sanitized mass response structure',
  });
  await expect(textbox).toBeVisible();
  await expect(textbox).toHaveAttribute('readonly', '');
  expect(await textbox.inputValue()).toBe(
    JSON.stringify(syntheticMassStructure, null, 2),
  );
  await textbox.evaluate((node: HTMLTextAreaElement) => {
    node.focus();
    node.select();
  });
  expect(
    await textbox.evaluate(
      (node: HTMLTextAreaElement) => node.selectionEnd - node.selectionStart,
    ),
  ).toBe((await textbox.inputValue()).length);
  const bounds = await textbox.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(320);
  expect(bounds!.height).toBeLessThanOrEqual(256);
  await expect(dialog.getByText('2 features')).toBeVisible();
  await expect(dialog.getByText('1 part')).toBeVisible();
  await expect(dialog.getByText('1 body')).toBeVisible();
});

test('Phase 5 ordered inspector details, keyboard, filtering, selection and partial evidence', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 320, height: 950 });
  const frame = await parentFixture(page);
  let reads = 0;
  const result = inspectorFixture({ ...syntheticProof, has_mass: false });
  result.bodies.items[0]!.face_count = null;
  result.bodies.completeness = 'partial';
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    async (route) => {
      reads++;
      await route.fulfill({ json: result });
    },
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(dialog.getByText('2 features', { exact: true })).toBeVisible();
  await expect(
    dialog.getByRole('list', { name: 'Feature order' }).locator('li strong'),
  ).toHaveText(['Sketch 1', 'Extrude 1']);
  const extrude = dialog.locator('summary').filter({ hasText: 'Extrude 1' });
  await extrude.focus();
  await page.keyboard.press('Enter');
  await expect(dialog.getByText(/12 mm/)).toBeVisible();
  await expect(extrude).toBeFocused();
  await page.keyboard.press('Space');
  await expect(dialog.getByText(/12 mm/)).not.toBeVisible();
  await dialog.getByLabel('Search features').fill('extrude');
  await expect(dialog.getByText('Sketch 1', { exact: true })).toHaveCount(0);
  await expect(dialog.getByText('Extrude 1', { exact: true })).toBeVisible();
  await dialog.getByLabel('Search features').fill('');
  await dialog.locator('summary').filter({ hasText: 'Part 1' }).click();
  await expect(dialog.getByText('DEMO-001')).toBeVisible();
  await dialog.locator('summary').filter({ hasText: 'Body 1' }).click();
  await expect(dialog.getByText('Unknown', { exact: true })).toBeVisible();
  await dialog
    .locator('summary')
    .filter({ hasText: 'Physical properties' })
    .click();
  await expect(
    dialog.getByText(/Numeric mass and volume are withheld/),
  ).toBeVisible();
  for (const [selection, label] of [
    [faceSelection, '1 face selected'],
    [edgeSelection, '1 edge selected'],
    [clearedSelection, 'No selection'],
  ] as const) {
    await page.evaluate(
      (data) =>
        document
          .querySelector('iframe')
          ?.contentWindow?.postMessage(data, 'https://forge-panel.test'),
      selection,
    );
    await expect(dialog.getByText(label, { exact: true })).toBeVisible();
  }
  expect(reads).toBe(1);
  const child = page
    .frames()
    .find((f) => f.url().includes('forge-panel.test/extension'))!;
  for (const width of [320, 380, 480, 1280]) {
    await page.setViewportSize({ width, height: 950 });
    for (const theme of ['dark', 'light']) {
      await child.evaluate((theme) => {
        document.documentElement.dataset.theme = theme;
      }, theme);
      expect(
        await child.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
  }
  expect(
    (await new AxeBuilder({ page }).include('iframe').analyze()).violations,
  ).toEqual([]);
  if (browserName === 'chromium') {
    await page.setViewportSize({ width: 380, height: 950 });
    await page.screenshot({
      path: '.cache/phase5/inspector-details.png',
      fullPage: true,
    });
  }
  expect(
    await child.evaluate(() =>
      JSON.stringify({ ...localStorage, ...sessionStorage }),
    ),
  ).not.toMatch(/Sketch 1|DEMO-001|12 mm/);
  await expect(dialog).not.toContainText(
    /synthetic-sketch|featureId|btType|aaaaaa…aaaa/,
  );
});

test('Phase 5 account rotation and empty context discard prior evidence without polling', async ({
  page,
}) => {
  const frame = await parentFixture(page);
  let calls = 0;
  let empty = false;
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    async (route) => {
      calls++;
      const source = structuredClone(syntheticProof);
      if (empty)
        for (const name of ['features', 'parts', 'bodies', 'mass'] as const)
          source[name].count = 0;
      await route.fulfill({ json: inspectorFixture(source) });
    },
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(dialog.getByText('Sketch 1', { exact: true })).toBeVisible();
  await page.route('https://forge-panel.test/api/me', (route) =>
    route.fulfill({
      json: {
        ...signedIn,
        display_name: 'Another synthetic engineer',
        csrf_token: 'b'.repeat(64),
      },
    }),
  );
  const child = page
    .frames()
    .find((f) => f.url().includes('forge-panel.test/extension'))!;
  await child.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(dialog.getByText('Sketch 1', { exact: true })).toHaveCount(0);
  expect(calls).toBe(1);
  await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(dialog.getByText('Sketch 1', { exact: true })).toBeVisible();
  empty = true;
  const query = new URLSearchParams(search);
  query.set('elementId', 'e'.repeat(24));
  await page.locator('iframe').evaluate((node, query) => {
    (node as HTMLIFrameElement).src =
      `https://forge-panel.test/extension?${query}`;
  }, query.toString());
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(dialog.getByText('Sketch 1', { exact: true })).toHaveCount(0);
  expect(calls).toBe(2);
  await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await expect(dialog.getByText('0 features', { exact: true })).toBeVisible();
  await expect(dialog.getByText('No parts returned.')).toBeVisible();
  await expect(
    dialog.getByText('No mass-property bodies returned'),
  ).toBeVisible();
  expect(calls).toBe(3);
});

test('Phase 5 unsupported parameters and bounded summaries stay explicit in production', async ({
  page,
}) => {
  const frame = await parentFixture(page);
  const result = inspectorFixture();
  result.source.features.count = 103;
  result.features.returned_count = 103;
  result.features.omitted_count = 101;
  result.features.completeness = 'partial';
  const item = result.features.items[0]!;
  item.feature_type = 'unknown';
  item.completeness = 'partial';
  item.suppression = 'suppressed';
  item.parameters = [
    {
      label: 'Option',
      kind: 'unsupported',
      state: 'unsupported',
      text: null,
      boolean: null,
      count: null,
    },
    {
      label: 'Long expression',
      kind: 'expression',
      state: 'omitted',
      text: null,
      boolean: null,
      count: null,
    },
  ];
  await page.route(
    'https://forge-panel.test/api/onshape/part-studio/inspector?*',
    (route) => route.fulfill({ json: result }),
  );
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  const dialog = frame.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Refresh CAD' }).click();
  await dialog.locator('summary').filter({ hasText: 'Sketch 1' }).click();
  await expect(dialog.getByText('Unsupported parameter type')).toBeVisible();
  await expect(dialog.getByText('Value omitted: display limit')).toBeVisible();
  await expect(
    dialog.getByText(/101 omitted by the display limit/),
  ).toBeVisible();
  await expect(
    dialog.getByText(/Custom or unknown feature · Suppressed/),
  ).toBeVisible();
});
