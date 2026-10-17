import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// All provider outcomes synthetic. These tests can never call Onshape REST.
test.afterEach(async ({ page }) => page.unrouteAll({ behavior: 'wait' }));
const proposal = {
  proposal_id: 'p'.repeat(43),
  digest: 'd'.repeat(64),
  operation_type: 'suppress_terminal_fillet_v1',
  label: 'Fillet fixture',
  position: 3,
  current: 'Active',
  proposed: 'Suppressed',
  expires_at: 2000000000,
};
async function open(page: Page, mode = 'success') {
  let dispatches = 0;
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.route('https://forge-edit.test/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
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
    if (url.pathname === '/api/modify/targets') {
      const body = req.postDataJSON() as { intent: string };
      if (body.intent === 'delete fillet')
        return route.fulfill({
          status: 422,
          json: { detail: 'unsupported_edit' },
        });
      return route.fulfill({
        json: {
          candidates: [
            {
              handle: 'c'.repeat(43),
              label: 'Fillet fixture',
              position: 3,
              expires_at: 2000000000,
            },
          ],
        },
      });
    }
    if (url.pathname === '/api/modify/proposals')
      return route.fulfill({ json: { proposal } });
    if (url.pathname.endsWith('/cancel'))
      return route.fulfill({ json: { state: 'cancelled' } });
    if (url.pathname.endsWith('/approve')) {
      dispatches++;
      expect(req.postDataJSON()).toEqual({ digest: proposal.digest });
      const events =
        mode === 'stale'
          ? [
              { type: 'progress', stage: 'checking' },
              { type: 'error', code: 'model_changed' },
            ]
          : [
              { type: 'progress', stage: 'checking' },
              { type: 'progress', stage: 'executing' },
              { type: 'progress', stage: 'verifying' },
              {
                type: 'result',
                state:
                  mode === 'timeout'
                    ? 'execution_uncertain'
                    : 'verified_success',
              },
            ];
      return route.fulfill({
        contentType: 'application/x-ndjson',
        body: events.map((e) => JSON.stringify(e) + '\n').join(''),
      });
    }
    if (url.pathname.startsWith('/api/modify/proposals/'))
      return route.fulfill({ json: { state: 'execution_uncertain' } });
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
  return { frame, dispatches: () => dispatches };
}
async function preview(page: Page, mode = 'success') {
  const fixture = await open(page, mode);
  const f = fixture.frame;
  await f.getByLabel('Modification request').fill('Suppress the final fillet.');
  await f.getByRole('button', { name: 'Find supported target' }).click();
  await f
    .getByRole('button', { name: 'Prepare change for Fillet fixture' })
    .click();
  await expect(f.getByText('Active → Suppressed')).toBeVisible();
  return fixture;
}
test('Phase 9 supported request and explicit target preview cancel has zero dispatch', async ({
  page,
}) => {
  const { frame, dispatches } = await preview(page);
  await frame.getByRole('button', { name: 'Cancel' }).click();
  await expect(
    frame.getByText('Proposal cancelled. Forge made no CAD change.'),
  ).toBeVisible();
  expect(dispatches()).toBe(0);
});
test('Phase 9 explicit approval reports verified only after evidence', async ({
  page,
}) => {
  const { frame, dispatches } = await preview(page);
  await frame.getByRole('button', { name: 'Approve change' }).click();
  await expect(frame.getByText(/Change verified\./)).toBeVisible();
  expect(dispatches()).toBe(1);
});
test('Phase 9 stale proposal is rejected', async ({ page }) => {
  const { frame } = await preview(page, 'stale');
  await frame.getByRole('button', { name: 'Approve change' }).click();
  await expect(frame.getByText(/The model changed since/)).toBeVisible();
  await expect(frame.getByText(/Change verified\./)).toHaveCount(0);
});
test('Phase 9 rapid double approval produces one request', async ({ page }) => {
  const { frame, dispatches } = await preview(page);
  await frame
    .getByRole('button', { name: 'Approve change' })
    .evaluate((button: HTMLButtonElement) => {
      button.click();
      button.click();
    });
  await expect(frame.getByText(/Change verified\./)).toBeVisible();
  expect(dispatches()).toBe(1);
});
test('Phase 9 timeout remains uncertain without automatic retry', async ({
  page,
}) => {
  const { frame, dispatches } = await preview(page, 'timeout');
  await frame.getByRole('button', { name: 'Approve change' }).click();
  await expect(
    frame.getByRole('button', { name: 'Check operation status' }),
  ).toBeVisible();
  await expect(
    frame.getByRole('button', { name: 'Approve change' }),
  ).toBeDisabled();
  expect(dispatches()).toBe(1);
});
test('Phase 9 unsupported operation cannot create approval', async ({
  page,
}) => {
  const { frame, dispatches } = await open(page);
  await frame.getByLabel('Modification request').fill('delete fillet');
  await frame.getByRole('button', { name: 'Find supported target' }).click();
  await expect(
    frame.getByText(/Other CAD edits are not supported/),
  ).toBeVisible();
  expect(dispatches()).toBe(0);
});
for (const mode of ['disabled', 'permission'])
  test(`Phase 9 ${mode} cannot offer approval`, async ({ page }) => {
    const { frame, dispatches } = await open(page, mode);
    await expect(
      frame.getByText(
        mode === 'disabled'
          ? 'Safe CAD editing is disabled in this environment.'
          : /Forge needs your permission/,
      ),
    ).toBeVisible();
    await expect(
      frame.getByRole('button', { name: 'Approve change' }),
    ).toHaveCount(0);
    expect(dispatches()).toBe(0);
  });
test('Phase 9 320px accessible proposal', async ({ page, browserName }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, dispatches } = await preview(page);
  const approve = frame.getByRole('button', { name: 'Approve change' });
  await approve.focus();
  await expect(approve).toBeFocused();
  const realFrame = page
    .frames()
    .find((f) => f.url().startsWith('https://forge-edit.test'));
  expect(realFrame).toBeDefined();
  expect(
    await realFrame!.evaluate(
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
    await page.screenshot({ path: '.cache/phase9b/proposal-320.png' });
  expect(dispatches()).toBe(0);
});
test('Phase 9 320px keyboard approval', async ({ page, browserName }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, dispatches } = await preview(page);
  const cancel = frame.getByRole('button', { name: 'Cancel' });
  const approve = frame.getByRole('button', { name: 'Approve change' });
  await cancel.focus();
  await expect(cancel).toBeFocused();
  // Safari's default keyboard navigation uses Option-Tab for buttons.
  await cancel.press(browserName === 'webkit' ? 'Alt+Tab' : 'Tab');
  await expect(approve).toBeFocused();
  await approve.press('Enter');
  await expect(frame.getByText(/Change verified\./)).toBeVisible();
  expect(dispatches()).toBe(1);
});
test('Phase 9 reduced motion forced colors retains explicit values', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce', forcedColors: 'active' });
  const { frame } = await preview(page);
  await expect(frame.getByText('Active → Suppressed')).toBeVisible();
  await expect(
    frame.getByRole('button', { name: 'Approve change' }),
  ).toBeEnabled();
});
