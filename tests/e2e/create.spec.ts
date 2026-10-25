import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// All creation outcomes are synthetic; no Onshape REST is contacted.
test.afterEach(async ({ page }) => page.unrouteAll({ behavior: 'wait' }));

const intents = [
  'define_base_profile',
  'form_base_body',
  'define_cut_profile',
  'remove_material',
];
const text: Record<string, string> = {
  define_base_profile:
    'Sketch the outline that gives the part its basic shape.',
  form_base_body:
    'Extrude the outline into a solid so there is material to cut.',
  define_cut_profile:
    'Sketch the shape of material to remove on an existing face.',
  remove_material: 'Cut the sketched shape out of the solid.',
};
const ops = [
  {
    operation: 'CREATE_SKETCH_RECT',
    target: { kind: 'base_plane', plane: 'TOP' },
    center_x_um: 0,
    center_y_um: 0,
    width_um: 60000,
    height_um: 40000,
  },
  {
    operation: 'EXTRUDE_NEW',
    profile: 's01',
    extent: { kind: 'blind', depth_um: 10000 },
  },
  {
    operation: 'CREATE_SKETCH_CIRCLE',
    target: { kind: 'step_face', step: 's02', face: 'end_cap' },
    center_x_um: 0,
    center_y_um: 0,
    diameter_um: 8000,
  },
  {
    operation: 'EXTRUDE_REMOVE',
    profile: 's03',
    target_body: 's02',
    extent: { kind: 'through_all' },
  },
];
const deps = [[], ['s01'], ['s02'], ['s02', 's03']];
const id = 'p'.repeat(43);
const ready = () => ({
  status: 'ready',
  proposal_id: id,
  expires_at: Math.floor(Date.now() / 1000) + 600,
  brief: {
    kind: 'rect_plate_with_through_holes',
    width: { value: 60, unit: 'mm' },
    length: { value: 40, unit: 'mm' },
    thickness: { value: 10, unit: 'mm' },
    holes: [
      {
        diameter: { value: 8, unit: 'mm' },
        center_x: { value: 0, unit: 'mm' },
        center_y: { value: 0, unit: 'mm' },
      },
    ],
  },
  plan: {
    capability: 'rect_plate_with_through_holes',
    digest: 'a'.repeat(64),
    steps: intents.map((intent, i) => ({
      id: `s0${i + 1}`,
      intent,
      depends_on: deps[i],
      op: ops[i],
    })),
  },
  explanations: intents.map((intent, i) => ({
    step_id: `s0${i + 1}`,
    intent,
    rationale_key: `creation.rationale.${intent}`,
    text: text[intent],
    authority: 'none',
  })),
});

async function open(page: Page, mode: 'success' | 'clarify' = 'success') {
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
    if (url.pathname === '/api/create/plan')
      return route.fulfill({
        json:
          mode === 'clarify'
            ? {
                status: 'needs_clarification',
                reason: 'missing_dimension',
                fields: ['thickness'],
                questions: ['What is the thickness?'],
              }
            : ready(),
      });
    if (url.pathname === `/api/create/plans/${id}/approve`) {
      approvals++;
      expect(request.postDataJSON()).toEqual({
        digest: 'a'.repeat(64),
        brief_confirmed: true,
      });
      return route.fulfill({
        json: {
          state: 'verified_success',
          steps: Array(4).fill('verified_success'),
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

const request =
  'Make a 60 by 40 by 10 mm plate with an 8 mm centered through-hole.';

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
