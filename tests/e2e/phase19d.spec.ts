import { expect, test } from '@playwright/test';
import type { Frame, FrameLocator, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';
import {
  resultStream,
  syntheticAnswer,
  syntheticGuideAnswer,
} from '../../apps/web/src/ai/__fixtures__/response';

// Synthetic only: no live Onshape, AI provider or CAD write. Screenshots land in
// .cache/phase19d for visual review.
test.afterEach(async ({ page }) => page.unrouteAll({ behavior: 'wait' }));

const query = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
const shot = (page: Page, name: string, fullPage = false) =>
  page.screenshot({ path: `.cache/phase19d/${name}.png`, fullPage });

const plateGuide = {
  ...syntheticGuideAnswer,
  guide: {
    kind: 'guide' as const,
    safety: 'safe' as const,
    title: 'Mounting plate, 60 × 40 × 10 mm',
    summary:
      'Sketch the outline, extrude it, cut two holes, then round the top edges.',
    key_dimensions: [
      '60 × 40 × 10 mm',
      '2 × Ø8 mm through holes',
      'Holes 10 mm from each short end',
      '2 mm top-edge fillet',
    ],
    assumptions: ['Holes sit on the centerline across the 40 mm width.'],
    questions: [],
    explanation: '',
    steps: [
      [
        'Sketch the outline',
        'Select the Top plane and start a sketch. Draw a corner rectangle, then dimension it 60 × 40 mm.',
        ['Sketch', 'Top plane', 'Corner rectangle', 'Dimension'],
        ['60 mm', '40 mm'],
        'The sketch shows two dimensions and is fully blue or black.',
      ],
      [
        'Extrude the plate',
        'Finish the sketch and Extrude the rectangle region 10 mm.',
        ['Extrude', 'End type: Blind', 'Operation: New'],
        ['10 mm'],
        'A single solid part appears in the Parts list.',
      ],
      [
        'Sketch the holes',
        'Sketch on the top face. Place two circles on the centerline, 10 mm from each short end.',
        ['Sketch', 'Top face', 'Circle', 'Dimension'],
        ['Ø8 mm', '10 mm'],
        'Both circles are fully dimensioned.',
      ],
      [
        'Cut the holes',
        'Extrude both circles with Operation set to Remove and End type Through all.',
        ['Extrude', 'Operation: Remove', 'Through all'],
        [],
        'You can see through both holes.',
      ],
      [
        'Fillet the top edges',
        'Select the four outer top edges and add a Fillet.',
        ['Fillet', 'Select edges'],
        ['2 mm'],
        'The top rim is rounded and the holes are untouched.',
      ],
      [
        'Review the feature tree',
        'Check the feature list reads Sketch, Extrude, Sketch, Extrude, Fillet.',
        ['Feature list'],
        [],
        'Five features, in order, none failed.',
      ],
    ].map(([title, action, controls, parameters, check]) => ({
      title,
      action,
      controls,
      parameters,
      check,
      why: 'Building in this order keeps each later edit predictable.',
    })),
    mistakes: [
      'Sketching holes before the plate exists.',
      'Leaving the hole centers undimensioned.',
    ],
    checklist: ['60 × 40 × 10 mm', 'Two Ø8 holes', '2 mm fillet'],
    follow_ups: [
      'Why dimension from the short end?',
      'How do I make the holes countersunk?',
    ],
  },
};
const chat = {
  ...syntheticAnswer,
  answer:
    'An Extrude gives a flat sketch real thickness. Think of pushing the outline up into a solid block.',
  evidence: [],
  uncertainties: [],
  follow_up_questions: ['What does Operation: Remove do?'],
};
const tutorAnswer = {
  explanation:
    'A sketch is flat, so it has no thickness. Extrude pushes it up into a solid.',
  reasoning_question: null,
  next_action: 'Try extruding your rectangle 10 mm.',
  observed: [],
  unknowns: [],
  notes: [],
  latest_check: null,
  used_cad: false,
  captured_at: null,
  capability_state: 'read_only',
};
const operation = {
  type: 'SET_SUPPRESSED',
  label: 'Edge fillet',
  feature_type: 'fillet',
  position: 3,
  field: 'Suppression',
  current: 'Active',
  proposed: 'Suppressed',
};
const plan = {
  proposal_id: 'p'.repeat(43),
  digest: 'd'.repeat(64),
  expires_at: 2000000000,
  operations: [operation],
};

async function panel(
  page: Page,
  { ask = chat, modify = 'verified' }: { ask?: unknown; modify?: string } = {},
) {
  const calls: string[] = [];
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.route('https://forge-panel.test/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/') && request.method() !== 'GET')
      calls.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/me') return route.fulfill({ json: signedIn });
    if (url.pathname === '/api/ai/ask')
      return route.fulfill({
        contentType: 'application/x-ndjson',
        body: resultStream(ask as typeof syntheticAnswer),
      });
    if (url.pathname === '/api/learning/tutor')
      return route.fulfill({
        contentType: 'application/x-ndjson',
        body:
          [
            { type: 'progress', stage: 'understanding' },
            { type: 'result', result: tutorAnswer },
          ]
            .map((event) => JSON.stringify(event))
            .join('\n') + '\n',
      });
    if (url.pathname === '/api/modify/capabilities')
      return route.fulfill({ json: { state: 'available' } });
    if (url.pathname === '/api/modify/recovery')
      return route.fulfill({ json: { state: 'none' } });
    if (url.pathname === '/api/modify/plan')
      return route.fulfill({
        json: {
          outcome: 'plan',
          preview: { ...plan, expires_at: Math.floor(Date.now() / 1000) + 120 },
        },
      });
    if (url.pathname.endsWith('/approve')) {
      const state =
        modify === 'uncertain'
          ? 'execution_uncertain'
          : modify === 'stale'
            ? 'rejected_stale'
            : 'verified_success';
      const events = [
        ...(modify === 'verified'
          ? [
              { type: 'progress', operation: 1, total: 1, stage: 'executing' },
              {
                type: 'operation_result',
                operation: 1,
                total: 1,
                state: 'verified_success',
              },
            ]
          : []),
        { type: 'result', state, operations: [state] },
      ];
      return route.fulfill({
        contentType: 'application/x-ndjson',
        body: events.map((event) => JSON.stringify(event) + '\n').join(''),
      });
    }
    return route.fulfill({
      response: await page.request.get(
        `http://127.0.0.1:4173${url.pathname}${url.search}`,
      ),
    });
  });
  await page.route('https://cad.onshape.com/forge-19d', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic Onshape parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-19d');
  const frame = page.frameLocator('iframe');
  await expect(frame.getByLabel('Design prompt')).toBeVisible();
  const child = page
    .frames()
    .find((candidate) => candidate.url().includes('forge-panel.test'))!;
  return { frame, child, calls };
}
const fits = (child: Frame) =>
  child.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
const tab = (frame: FrameLocator, name: string) =>
  frame.getByRole('tab', { name, exact: true });

for (const width of [320, 375, 1100])
  test(`switcher, brand and no Create entry at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 800 });
    const h = await panel(page);
    await expect(h.frame.getByRole('tablist')).toBeVisible();
    for (const name of ['Design', 'Modify', 'Learn'])
      await expect(tab(h.frame, name)).toBeVisible();
    // Create is gone from every role it could occupy.
    await expect(
      h.frame.getByRole('button', { name: /^create$/i }),
    ).toHaveCount(0);
    await expect(h.frame.getByRole('tab', { name: /create/i })).toHaveCount(0);
    await expect(h.frame.getByText(/^Create$/)).toHaveCount(0);
    await expect(h.frame.getByLabel('Design mode')).toHaveCount(0);
    await shot(page, `nav-design-${width}`);
    // Rapid switching never loses the final selection and the pill lands on it.
    for (let round = 0; round < 4; round++)
      for (const name of ['Modify', 'Learn', 'Design'])
        await tab(h.frame, name).click({ delay: 0 });
    await tab(h.frame, 'Learn').click();
    await tab(h.frame, 'Modify').click();
    await expect(tab(h.frame, 'Modify')).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await page.waitForTimeout(900);
    const aligned = await h.child.evaluate(() => {
      const selected = document.querySelector<HTMLElement>(
        '[role=tab][data-state=active]',
      )!;
      const pill = document.querySelector<HTMLElement>('.tabs-indicator')!;
      const a = selected.getBoundingClientRect();
      const b = pill.getBoundingClientRect();
      return {
        left: Math.abs(a.left - b.left),
        width: Math.abs(a.width - b.width),
      };
    });
    expect(aligned.left).toBeLessThan(1.5);
    expect(aligned.width).toBeLessThan(1.5);
    await shot(page, `nav-modify-${width}`);
    expect(await fits(h.child)).toBe(true);
    // Keyboard semantics survive: arrows move and activate.
    await tab(h.frame, 'Modify').focus();
    await page.keyboard.press('ArrowRight');
    await expect(tab(h.frame, 'Learn')).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

test('reduced motion snaps the pill without animation', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 360, height: 800 });
  const h = await panel(page);
  await tab(h.frame, 'Learn').click();
  const gap = await h.child.evaluate(
    () =>
      new Promise<number>((resolve) =>
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            const a = document
              .querySelector<HTMLElement>('[role=tab][data-state=active]')!
              .getBoundingClientRect();
            const b = document
              .querySelector<HTMLElement>('.tabs-indicator')!
              .getBoundingClientRect();
            resolve(Math.abs(a.left - b.left));
          }),
        ),
      ),
  );
  expect(gap).toBeLessThan(1.5);
});

for (const width of [320, 1100])
  test(`Design answers: conversation and compact guide at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const h = await panel(page, { ask: chat });
    await shot(page, `design-empty-${width}`);
    await h.frame.getByLabel('Design prompt').fill('What does Extrude do?');
    await h.frame.getByLabel('Design prompt').press('Control+Enter');
    await expect(h.frame.getByText(/real thickness/)).toBeVisible();
    await shot(page, `design-chat-${width}`);
    expect(await fits(h.child)).toBe(true);
  });

test('modeling guide opens one step, advances on demand and keeps every step', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  const h = await panel(page, { ask: plateGuide });
  await h.frame.getByLabel('Design prompt').fill('Walk me through a plate');
  await h.frame.getByLabel('Design prompt').press('Control+Enter');
  const steps = h.frame.getByRole('list', { name: 'Modeling steps' });
  await expect(steps).toBeVisible();
  await expect(steps.locator(':scope > li')).toHaveCount(6);
  const headers = steps.getByRole('button', { expanded: true });
  await expect(headers).toHaveCount(1);
  await expect(
    h.frame.getByText('Select the Top plane and start a sketch', {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    h.frame.getByText('Finish the sketch and Extrude', { exact: false }),
  ).toBeHidden();
  await shot(page, 'guide-collapsed-320', true);
  await h.frame
    .getByRole('button', { name: /Done, next step/ })
    .first()
    .click();
  await expect(h.frame.getByText('0 of 6 done')).toHaveCount(0);
  await expect(h.frame.getByText('1 of 6 done')).toBeVisible();
  await expect(
    h.frame.getByText('Finish the sketch and Extrude', { exact: false }),
  ).toBeVisible();
  await h.frame.getByRole('button', { name: 'Show all steps' }).click();
  await expect(steps.getByRole('button', { expanded: true })).toHaveCount(6);
  await shot(page, 'guide-expanded-320', true);
  // Progress is the reader's own; the guide never claims CAD verification.
  await expect(h.frame.getByText(/verified/i)).toHaveCount(0);
  await h.frame
    .getByRole('button', { name: 'Why dimension from the short end?' })
    .click();
  expect(h.calls.filter((call) => call.endsWith('/api/ai/ask'))).toHaveLength(
    2,
  );
  expect(await fits(h.child)).toBe(true);
  // The mode switcher tucks away while scrolling; return it before auditing.
  await h.child.evaluate(() => {
    document.querySelector('.workspace-pane')!.scrollTop = 0;
  });
  await page.waitForTimeout(400);
  const violations = (
    await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
  ).violations;
  expect(violations).toEqual([]);
});

for (const width of [320, 375])
  test(`Learn plate lesson and Ask Forge chat at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 760 });
    const h = await panel(page);
    await tab(h.frame, 'Learn').click();
    await h.frame.getByRole('radio', { name: /^Beginner/ }).check();
    await h.frame
      .getByRole('radio', {
        name: 'Follow a mounting plate from sketch to fillet',
        exact: true,
      })
      .check();
    await h.frame.getByRole('button', { name: 'Review lesson' }).click();
    await h.frame.getByRole('button', { name: 'Begin lesson' }).click();
    await h.frame.getByRole('radio', { name: /still a flat outline/ }).check();
    await shot(page, `learn-step-${width}`);
    const launcher = h.frame.getByRole('button', {
      name: 'Ask Forge',
      exact: true,
    });
    await expect(launcher).toHaveAttribute('aria-expanded', 'false');
    await expect(h.frame.getByRole('dialog')).toHaveCount(0);
    await launcher.click();
    const sheet = h.frame.getByRole('dialog', { name: 'Ask Forge chat' });
    await expect(sheet).toBeVisible();
    await expect(h.frame.getByLabel('Ask about this step')).toBeFocused();
    await page.waitForTimeout(700);
    await shot(page, `learn-ask-open-${width}`);
    const box = await sheet.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width + 0.5);
    await h.frame.getByLabel('Ask about this step').fill('Why extrude?');
    await h.frame.getByRole('button', { name: 'Send', exact: true }).click();
    await expect(h.frame.getByText(/solid/).first()).toBeVisible();
    await shot(page, `learn-ask-answer-${width}`);
    // Minimizing keeps the conversation; Escape works; focus returns.
    await page.keyboard.press('Escape');
    await expect(sheet).toHaveCount(0);
    await expect(launcher).toBeFocused();
    await launcher.click();
    await expect(h.frame.getByText('Why extrude?')).toBeVisible();
    await h.frame.getByRole('button', { name: 'Minimize Ask Forge' }).click();
    await expect(sheet).toHaveCount(0);
    await shot(page, `learn-ask-collapsed-${width}`);
    expect(await fits(h.child)).toBe(true);
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()
      ).violations,
    ).toEqual([]);
  });

for (const mode of ['verified', 'uncertain', 'stale'])
  test(`Modify suppress-fillet review and ${mode} outcome`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    const h = await panel(page, { modify: mode });
    await tab(h.frame, 'Modify').click();
    await shot(page, 'modify-request');
    await h.frame
      .getByLabel('Modification request')
      .fill('Suppress the final fillet.');
    await h.frame.getByRole('button', { name: 'Prepare plan' }).click();
    await expect(
      h.frame.getByText('Suppressed', { exact: true }),
    ).toBeVisible();
    await expect(h.frame.getByText('Active', { exact: true })).toBeVisible();
    await shot(page, 'modify-plan', true);
    await h.frame.getByRole('button', { name: /^Approve/ }).click();
    if (mode === 'verified')
      await expect(h.frame.getByText('Plan verified')).toBeVisible();
    if (mode === 'uncertain')
      await expect(
        h.frame.getByText(/could not confirm the final result/),
      ).toBeVisible();
    if (mode === 'stale')
      await expect(
        h.frame.getByRole('heading', { name: 'Model changed' }),
      ).toBeVisible();
    // One approval, one dispatch, whatever the outcome looks like.
    expect(h.calls.filter((call) => call.endsWith('/approve'))).toHaveLength(1);
    await shot(page, `modify-${mode}`, true);
    expect(await fits(h.child)).toBe(true);
  });
