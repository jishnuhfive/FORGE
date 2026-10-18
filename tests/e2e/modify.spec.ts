import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// All CAD and model outcomes are synthetic; no Onshape REST is contacted.
test.afterEach(async ({ page }) => page.unrouteAll({ behavior: 'wait' }));
const preview = {
  proposal_id: 'p'.repeat(43),
  digest: 'd'.repeat(64),
  expires_at: 2000000000,
  operations: [
    {
      type: 'SET_EXTRUDE_DEPTH',
      label: 'Base extrusion',
      feature_type: 'extrude',
      position: 2,
      field: 'Depth',
      current: '20 mm',
      proposed: '30 mm',
    },
    {
      type: 'SET_FILLET_RADIUS',
      label: 'Edge fillet',
      feature_type: 'fillet',
      position: 3,
      field: 'Radius',
      current: '2 mm',
      proposed: '4 mm',
    },
    {
      type: 'RENAME_FEATURE',
      label: 'Edge fillet',
      feature_type: 'fillet',
      position: 3,
      field: 'Name',
      current: 'Edge fillet',
      proposed: 'Edge Rounds',
    },
  ],
};
async function open(page: Page, mode = 'success') {
  let dispatches = 0;
  let statusReads = 0;
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.route('https://forge-edit.test/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === '/api/me') return route.fulfill({ json: signedIn });
    if (url.pathname === '/api/modify/capabilities')
      return route.fulfill({
        json: {
          state:
            mode === 'disabled'
              ? 'write_disabled'
              : mode === 'permission'
                ? 'write_permission_required'
                : 'available',
        },
      });
    if (url.pathname === '/api/modify/plan') {
      expect(Object.keys(request.postDataJSON() as object).sort()).toEqual([
        'context',
        'request',
      ]);
      return route.fulfill({
        json:
          mode === 'clarification'
            ? {
                outcome: 'clarification',
                reason: 'ambiguous_target',
                choices: [
                  { label: 'Edge fillet', feature_type: 'fillet', position: 3 },
                ],
              }
            : {
                outcome: 'plan',
                preview: {
                  ...preview,
                  expires_at: Math.floor(Date.now() / 1000) + 120,
                },
              },
      });
    }
    if (
      url.pathname ===
      '/api/modify/plans/' + preview.proposal_id + '/cancel'
    ) {
      expect(request.postDataJSON()).toEqual({});
      return route.fulfill({
        json: {
          state: 'cancelled',
          operations: ['skipped', 'skipped', 'skipped'],
        },
      });
    }
    if (
      url.pathname ===
      '/api/modify/plans/' + preview.proposal_id + '/approve'
    ) {
      dispatches++;
      expect(request.postDataJSON()).toEqual({ digest: preview.digest });
      const operations =
        mode === 'partial'
          ? ['verified_success', 'write_failed', 'skipped']
          : mode === 'uncertain'
            ? ['verified_success', 'execution_uncertain', 'skipped']
            : mode === 'stale'
              ? ['rejected_stale', 'skipped', 'skipped']
              : ['verified_success', 'verified_success', 'verified_success'];
      const state =
        mode === 'partial'
          ? 'partial_failure'
          : mode === 'uncertain'
            ? 'execution_uncertain'
            : mode === 'stale'
              ? 'rejected_stale'
              : 'verified_success';
      const events =
        mode === 'incomplete'
          ? [{ type: 'progress', operation: 1, total: 3, stage: 'executing' }]
          : [
              ...operations.flatMap((result, i) =>
                result === 'verified_success'
                  ? [
                      ...['checking', 'executing', 'verifying'].map(
                        (stage) => ({
                          type: 'progress',
                          operation: i + 1,
                          total: 3,
                          stage,
                        }),
                      ),
                      {
                        type: 'operation_result',
                        operation: i + 1,
                        total: 3,
                        state: result,
                      },
                    ]
                  : [
                      {
                        type: 'operation_result',
                        operation: i + 1,
                        total: 3,
                        state: result,
                      },
                    ],
              ),
              { type: 'result', state, operations },
            ];
      return route.fulfill({
        contentType: 'application/x-ndjson',
        body: events.map((e) => JSON.stringify(e) + '\n').join(''),
      });
    }
    if (url.pathname === '/api/modify/plans/' + preview.proposal_id) {
      statusReads++;
      expect(request.method()).toBe('GET');
      return route.fulfill({
        json: {
          state: 'verified_success',
          operations: [
            'verified_success',
            'verified_success',
            'verified_success',
          ],
        },
      });
    }
    if (url.pathname.startsWith('/api/modify/'))
      throw new Error('Unexpected Modify authority path');
    return route.fulfill({
      response: await page.request.get(
        'http://127.0.0.1:4173' + url.pathname + url.search,
      ),
    });
  });
  await page.route('https://cad.onshape.com/forge-edit-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-edit.test/extension?documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-edit-test');
  const frame = page.frameLocator('iframe');
  await frame.getByRole('tab', { name: 'Modify', exact: true }).click();
  return {
    frame,
    dispatches: () => dispatches,
    statusReads: () => statusReads,
  };
}
async function plan(page: Page, mode = 'success') {
  const fixture = await open(page, mode);
  await fixture.frame
    .getByLabel('Modification request')
    .fill(
      'Make the extrude 30 mm deep and fillet 4 mm, then rename the fillet Edge Rounds.',
    );
  await fixture.frame.getByRole('button', { name: 'Prepare plan' }).click();
  await expect(
    fixture.frame.getByRole('heading', { name: 'Plan ready for review' }),
  ).toBeVisible();
  return fixture;
}
test('B2 exact preview and human cancellation make no dispatch', async ({
  page,
}) => {
  const { frame, dispatches } = await plan(page);
  await expect(
    frame.getByRole('list', { name: 'Planned changes' }).getByRole('listitem'),
  ).toHaveCount(3);
  await expect(
    frame.getByRole('heading', { name: '1. Base extrusion' }),
  ).toBeVisible();
  await expect(
    frame.getByRole('heading', { name: '2. Edge fillet' }),
  ).toBeVisible();
  await expect(
    frame.getByRole('heading', { name: '3. Edge fillet' }),
  ).toBeVisible();
  await frame.getByRole('button', { name: 'Cancel plan' }).click();
  await expect(
    frame.getByRole('heading', { name: 'Plan cancelled' }),
  ).toBeVisible();
  expect(dispatches()).toBe(0);
});
test('B2 human approval verifies the ordered plan once', async ({ page }) => {
  const { frame, dispatches } = await plan(page);
  expect(dispatches()).toBe(0);
  await frame.getByRole('button', { name: 'Approve 3 changes' }).click();
  await expect(
    frame.getByRole('heading', { name: 'Plan verified' }),
  ).toBeVisible();
  await expect(frame.getByText('3 of 3 changes verified.')).toBeVisible();
  expect(dispatches()).toBe(1);
});
test('B2 stale plan stops without success', async ({ page }) => {
  const { frame } = await plan(page, 'stale');
  await frame.getByRole('button', { name: 'Approve 3 changes' }).click();
  await expect(
    frame.getByRole('heading', { name: 'Model changed' }),
  ).toBeVisible();
  await expect(
    frame.getByRole('heading', { name: 'Plan verified' }),
  ).toHaveCount(0);
});
test('B2 rapid double approval produces one request', async ({ page }) => {
  const { frame, dispatches } = await plan(page);
  await frame
    .getByRole('button', { name: 'Approve 3 changes' })
    .evaluate((button: HTMLButtonElement) => {
      button.click();
      button.click();
    });
  await expect(
    frame.getByRole('heading', { name: 'Plan verified' }),
  ).toBeVisible();
  expect(dispatches()).toBe(1);
});
for (const mode of ['uncertain', 'incomplete'])
  test(`B2 ${mode} offers GET status without retry`, async ({ page }) => {
    const { frame, dispatches, statusReads } = await plan(page, mode);
    await frame.getByRole('button', { name: 'Approve 3 changes' }).click();
    await expect(
      frame.getByRole('heading', {
        name: 'Forge could not confirm the final result.',
      }),
    ).toBeVisible();
    await expect(frame.getByRole('button', { name: /Approve/ })).toHaveCount(0);
    await frame.getByRole('button', { name: 'Check status' }).click();
    await expect(
      frame.getByRole('heading', { name: 'Plan verified' }),
    ).toBeVisible();
    expect(statusReads()).toBe(1);
    expect(dispatches()).toBe(1);
  });
test('B2 partial failure preserves earlier verified changes', async ({
  page,
}) => {
  const { frame } = await plan(page, 'partial');
  await frame.getByRole('button', { name: 'Approve 3 changes' }).click();
  await expect(
    frame.getByRole('heading', { name: 'Plan partially completed' }),
  ).toBeVisible();
  await expect(
    frame.getByText(/Earlier verified changes remain applied/),
  ).toBeVisible();
  await expect(frame.getByText('Not applied', { exact: true })).toBeVisible();
  await expect(frame.getByText('Not attempted', { exact: true })).toBeVisible();
});
test('B2 clarification requests a more specific rewrite', async ({ page }) => {
  const { frame, dispatches } = await open(page, 'clarification');
  await frame.getByLabel('Modification request').fill('Change the fillet');
  await frame.getByLabel('Modification request').press('Enter');
  await expect(
    frame.getByRole('heading', { name: 'Make the request more specific' }),
  ).toBeVisible();
  await expect(
    frame.getByText('Edge fillet · Fillet · position 3'),
  ).toBeVisible();
  expect(dispatches()).toBe(0);
});
for (const mode of ['disabled', 'permission'])
  test(`B2 ${mode} cannot offer approval`, async ({ page }) => {
    const { frame, dispatches } = await open(page, mode);
    await expect(
      frame.getByText(
        mode === 'disabled'
          ? 'Safe CAD editing is disabled in this environment.'
          : /Forge needs your permission/,
      ),
    ).toBeVisible();
    await expect(
      frame.getByRole('button', { name: 'Prepare plan' }),
    ).toHaveCount(0);
    expect(dispatches()).toBe(0);
  });
test('B2 320px preview is accessible without horizontal overflow', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, dispatches } = await plan(page);
  await frame.getByRole('button', { name: 'Approve 3 changes' }).focus();
  await expect(
    frame.getByRole('button', { name: 'Approve 3 changes' }),
  ).toBeFocused();
  const actualFrame = page
    .frames()
    .find((f) => f.url().startsWith('https://forge-edit.test'))!;
  expect(
    await actualFrame.evaluate(
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
  if (browserName === 'chromium')
    await page.screenshot({ path: '.cache/b2/plan-320.png' });
  expect(dispatches()).toBe(0);
});
test('B2 320px keyboard approval', async ({ page, browserName }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, dispatches } = await plan(page);
  const cancel = frame.getByRole('button', { name: 'Cancel plan' });
  const approve = frame.getByRole('button', { name: 'Approve 3 changes' });
  await cancel.focus();
  await cancel.press(browserName === 'webkit' ? 'Alt+Tab' : 'Tab');
  await expect(approve).toBeFocused();
  await approve.press('Enter');
  await expect(
    frame.getByRole('heading', { name: 'Plan verified' }),
  ).toBeVisible();
  expect(dispatches()).toBe(1);
});
test('B2 reduced motion and forced colors retain exact values', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce', forcedColors: 'active' });
  const { frame } = await plan(page);
  await expect(frame.getByText('20 mm', { exact: true })).toBeVisible();
  await expect(frame.getByText('30 mm', { exact: true })).toBeVisible();
  await expect(
    frame.getByRole('button', { name: 'Approve 3 changes' }),
  ).toBeEnabled();
});
