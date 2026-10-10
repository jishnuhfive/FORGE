import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { signedIn, signedOut } from './auth-fixtures';
import {
  clearedSelection,
  edgeSelection,
  faceSelection,
} from '../../apps/web/src/onshape/__fixtures__/selection';
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
      body: `<!doctype html><html><head><title>Test Onshape parent</title></head><body style="margin:0"><script>window.received=[];addEventListener('message',e=>{if(e.origin==='https://forge-panel.test')window.received.push(e.data)});</script><iframe title="Forge extension" style="border:0;width:100vw;height:95vh" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
    }),
  );
  await page.goto(`${origin}/forge-panel-test`);
  return page.frameLocator('iframe');
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
  await expect(dialog.getByText('Selection needs refresh')).toBeVisible();
  await page.locator('iframe').evaluate((node, query) => {
    (node as HTMLIFrameElement).src =
      `https://forge-panel.test/extension?${query.replace('c'.repeat(24), 'd'.repeat(24))}`;
  }, search);
  await frame.getByRole('button', { name: 'View CAD context' }).click();
  await expect(
    frame.getByRole('dialog').getByText('dddddd…dddd'),
  ).toBeVisible();
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
    await expect(dialog.getByText('eeeeee…eeee')).toBeVisible();
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
