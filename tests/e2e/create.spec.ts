import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// All creation outcomes are synthetic; no Onshape REST is contacted.
test.afterEach(async ({ page }) => page.unrouteAll({ behavior: 'wait' }));

const id = 'p'.repeat(43);
const brief = {
  kind: 'rect_plate_with_through_holes',
  width: { value: 60, unit: 'mm' },
  length: { value: 40, unit: 'mm' },
  thickness: { value: 10, unit: 'mm' },
  holes: [],
};
// Shaped like cad_create's prepared proposal: the supported rectangle + Extrude.
const ready = () => ({
  proposal_id: id,
  digest: 'a'.repeat(64),
  expires_at: Math.floor(Date.now() / 1000) + 600,
  brief,
  plan: {
    schema_version: 1,
    capability: 'rect_plate_with_through_holes',
    units: 'um',
    digest: 'c'.repeat(64),
    steps: [
      {
        id: 's01',
        intent: 'define_base_profile',
        depends_on: [],
        op: {
          operation: 'CREATE_SKETCH_RECT',
          target: { kind: 'base_plane', plane: 'TOP' },
          center_x_um: 0,
          center_y_um: 0,
          width_um: 60000,
          height_um: 40000,
        },
      },
      {
        id: 's02',
        intent: 'form_base_body',
        depends_on: ['s01'],
        op: {
          operation: 'EXTRUDE_NEW',
          profile: 's01',
          extent: { kind: 'blind', depth_um: 10000 },
        },
      },
    ],
  },
  explanations: [
    {
      step_id: 's01',
      intent: 'define_base_profile',
      rationale_key: 'creation.rationale.define_base_profile',
      text: 'Sketch the outline that gives the part its basic shape.',
      authority: 'none',
    },
    {
      step_id: 's02',
      intent: 'form_base_body',
      rationale_key: 'creation.rationale.form_base_body',
      text: 'Extrude the outline into a solid so there is material to cut.',
      authority: 'none',
    },
  ],
  limitations: [
    'Sketch coordinates are editable; constraints are not created.',
  ],
});

type Mode = 'success' | 'clarify' | 'unsupported' | 'uncertain';
async function open(page: Page, mode: Mode = 'success') {
  let approvals = 0;
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.route('https://forge-create.test/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === '/api/me') return route.fulfill({ json: signedIn });
    if (url.pathname === '/api/create/interpret')
      return route.fulfill({
        json:
          mode === 'clarify'
            ? {
                status: 'needs_clarification',
                reason: 'missing_dimension',
                fields: ['thickness'],
                questions: ['What is the thickness?'],
              }
            : { status: 'ready', brief, plan: ready().plan },
      });
    if (url.pathname === '/api/create/plan')
      return route.fulfill(
        mode === 'unsupported'
          ? { status: 422, json: { detail: 'unsupported_geometry' } }
          : { json: ready() },
      );
    if (url.pathname === `/api/create/plans/${id}/approve`) {
      approvals++;
      expect(request.postDataJSON()).toEqual({
        digest: 'a'.repeat(64),
        brief_confirmed: true,
      });
      return route.fulfill({
        json:
          mode === 'uncertain'
            ? {
                state: 'execution_uncertain',
                steps: ['verified_success', 'execution_uncertain'],
              }
            : {
                state: 'verified_success',
                steps: ['verified_success', 'verified_success'],
              },
      });
    }
    if (url.pathname.startsWith('/api/create/'))
      throw new Error('Unexpected creation path');
    return route.fulfill({
      response: await page.request.get(
        'http://127.0.0.1:4173' + url.pathname + url.search,
      ),
    });
  });
  await page.route('https://cad.onshape.com/forge-create-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-create.test/extension?documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-create-test');
  const frame = page.frameLocator('iframe');
  await frame.getByRole('button', { name: 'Create', exact: true }).click();
  return { frame, approvals: () => approvals };
}

const request = 'Make a 60 by 40 by 10 mm plate.';

test('request → brief → confirmation → verified build → Learn at 320px', async ({
  page,
  browserName,
}) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, approvals } = await open(page);
  await frame.getByLabel('Part request').fill(request);
  await frame.getByRole('button', { name: 'Prepare brief' }).click();
  await expect(
    frame.getByRole('heading', { name: 'Engineering brief' }),
  ).toBeVisible();
  const approve = frame.getByRole('button', { name: /Approve and build/ });
  await expect(approve).toBeDisabled();
  const actual = page
    .frames()
    .find((f) => f.url().startsWith('https://forge-create.test'))!;
  expect(
    await actual.evaluate(
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
    await page.screenshot({ path: '.cache/create/review-320.png' });
  await frame
    .getByRole('checkbox', { name: /checked these dimensions/ })
    .check();
  await expect(approve).toBeEnabled();
  await approve.focus();
  await page.keyboard.press('Enter');
  await expect(
    frame
      .getByRole('region', { name: 'Result' })
      .getByRole('heading', { name: 'Verified' }),
  ).toBeVisible();
  await expect(
    frame.getByRole('heading', { name: 'Learn how FORGE built this' }),
  ).toBeVisible();
  expect(approvals()).toBe(1);
  expect(
    await actual.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  if (browserName === 'chromium')
    await page.screenshot({
      path: '.cache/create/verified-320.png',
      fullPage: true,
    });
});

test('clarification builds nothing and offers no approval', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, approvals } = await open(page, 'clarify');
  await frame.getByLabel('Part request').fill('Make a plate');
  await frame.getByRole('button', { name: 'Prepare brief' }).click();
  await expect(frame.getByText('Forge needs a bit more')).toBeVisible();
  await expect(frame.getByRole('button', { name: /Approve/ })).toHaveCount(0);
  expect(approvals()).toBe(0);
});

test('a request needing holes is refused before approval with zero writes', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, approvals } = await open(page, 'unsupported');
  await frame
    .getByLabel('Part request')
    .fill('Make a 60 by 40 by 10 mm plate with an 8 mm hole.');
  await frame.getByRole('button', { name: 'Prepare brief' }).click();
  await expect(frame.getByText(/nothing was built/i).first()).toBeVisible();
  await expect(frame.getByRole('button', { name: /Approve/ })).toHaveCount(0);
  expect(approvals()).toBe(0);
});

test('an uncertain result is never shown as verified and is not retried', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 850 });
  const { frame, approvals } = await open(page, 'uncertain');
  await frame.getByLabel('Part request').fill(request);
  await frame.getByRole('button', { name: 'Prepare brief' }).click();
  await frame
    .getByRole('checkbox', { name: /checked these dimensions/ })
    .check();
  await frame.getByRole('button', { name: /Approve and build/ }).click();
  await expect(
    frame.getByText('Forge could not confirm the result'),
  ).toBeVisible();
  await expect(frame.getByRole('heading', { name: 'Verified' })).toHaveCount(0);
  await expect(
    frame.getByRole('button', { name: /Approve and build/ }),
  ).toHaveCount(0);
  expect(approvals()).toBe(1);
});
