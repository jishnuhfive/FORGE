import { expect, test } from '@playwright/test';
import type { FrameLocator, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// Synthetic only: no live Onshape, no live Groq. The server's decisions are scripted.
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
});

const query = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
const req = (
  id: string,
  status: string,
  reason: string,
  finding: string,
  blocking = true,
) => ({
  requirement_id: id,
  description: 'Label',
  blocking,
  evidence: ['features'],
  outcome: { status, reason, finding },
});
const answer = (step: string, outcome: string, results: object[]) => ({
  lesson_id: 'mounting-bracket',
  step_id: step,
  outcome,
  results,
  captured_at: '2026-01-01T12:00:00+00:00',
  consistency: 'unverified',
  evidence_token: 'synthetic-payload.synthetic-mac',
});
const noExtrusion = answer('base-solid', 'not_met', [
  req(
    'extrude.exists',
    'FAIL',
    'missing',
    'Forge sees no active extrude feature yet.',
  ),
  req('body.solid', 'FAIL', 'missing', 'Forge sees no solid body yet.'),
]);
const fixed = answer('base-solid', 'verified', [
  req('extrude.exists', 'PASS', 'met', 'Forge sees an active extrude feature.'),
  req('body.solid', 'PASS', 'met', 'Forge sees a solid body.'),
  req(
    'extrude.depth',
    'UNVERIFIED',
    'not_observable',
    'Cannot read a thickness.',
    false,
  ),
]);
const fillet = answer('second-portion', 'unverified', [
  req(
    'bracket.second_portion',
    'WARNING',
    'ambiguous_signal',
    'The face count fits a second portion, but fillets or chamfers can also raise it.',
  ),
]);
const transferOk = answer('transfer-single-profile', 'verified', [
  req('transfer.sketch', 'PASS', 'met', 'Forge sees an active sketch.'),
  req(
    'transfer.one_extrusion',
    'PASS',
    'met',
    'Forge sees exactly one active extrusion.',
  ),
  req('transfer.solid_body', 'PASS', 'met', 'Forge sees a solid body.'),
  req(
    'transfer.l_profile',
    'PASS',
    'met',
    'Forge sees a body with more faces than a plain block.',
  ),
  req(
    'transfer.dimensions',
    'UNVERIFIED',
    'not_observable',
    'Cannot read dimensions.',
    false,
  ),
]);

async function open(page: Page, replies: object[]) {
  const bodies: unknown[] = [];
  const writes: string[] = [];
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  let call = 0;
  await page.route('https://forge-panel.test/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      request.method() !== 'GET' &&
      url.pathname !== '/api/learning/check-step'
    )
      writes.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/me') await route.fulfill({ json: signedIn });
    else if (url.pathname === '/api/learning/check-step') {
      bodies.push(request.postDataJSON());
      await route.fulfill({
        json: replies[Math.min(call++, replies.length - 1)]!,
      });
    } else
      await route.fulfill({
        response: await page.request.get(
          `http://127.0.0.1:4173${url.pathname}${url.search}`,
        ),
      });
  });
  await page.route(
    'https://cad.onshape.com/forge-investigation-test',
    (route) =>
      route.fulfill({
        contentType: 'text/html',
        body: `<!doctype html><html lang="en"><head><title>Synthetic Onshape parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
      }),
  );
  await page.goto('https://cad.onshape.com/forge-investigation-test');
  const frame = page.frameLocator('iframe');
  await frame.getByRole('tab', { name: 'Learn', exact: true }).click();
  await frame.getByRole('radio', { name: /^Beginner/ }).check();
  await frame
    .getByRole('radio', { name: 'Complete a guided project', exact: true })
    .check();
  await frame.getByRole('button', { name: /^Review/ }).click();
  await frame.getByRole('button', { name: 'Begin lesson' }).click();
  return { frame, bodies, writes, calls: () => call };
}
const next = async (frame: FrameLocator, last = false) => {
  await frame
    .getByRole('button', { name: 'Mark step done', exact: true })
    .click();
  await frame
    .getByRole('button', {
      name: last ? 'View completion summary' : 'Next step',
      exact: true,
    })
    .click();
};
const press = (frame: FrameLocator) =>
  frame.getByRole('button', { name: /^Check (my step|again)$/ });
const noOverflow = async (page: Page) =>
  expect(
    await page
      .frames()
      .find((f) => f.url().includes('forge-panel.test/extension'))!
      .evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBe(true);

test('step 2 failure → observed → prediction → recommendation → re-check PASS', async ({
  page,
}) => {
  const { frame, writes, calls } = await open(page, [noExtrusion, fixed]);
  await next(frame);
  await press(frame).click();
  const panel = frame.getByRole('region', { name: 'Investigate' });
  await expect(
    panel.getByText('Forge sees no active extrude feature yet.'),
  ).toBeVisible();
  // Nothing is explained before the student thinks first.
  await expect(panel.getByText('Possible explanation')).toHaveCount(0);
  await panel
    .getByRole('radio', { name: 'Turn the closed sketch into a 3D feature' })
    .check();
  await panel
    .getByRole('button', { name: 'Show a possible explanation' })
    .click();
  await expect(
    panel.getByText('This is a possibility, not something Forge has verified.'),
  ).toBeVisible();
  await panel.getByRole('button', { name: 'Show what to try next' }).click();
  await expect(panel.getByRole('heading', { name: 'Try next' })).toBeVisible();
  // Predicting and revealing never caused a check.
  expect(calls()).toBe(1);
  await press(frame).click();
  await expect(
    panel.getByText(/Resolved\. Forge sees an active extrude feature\./),
  ).toBeVisible();
  await expect(
    frame
      .getByText('Investigations resolved after re-check')
      .locator('xpath=following-sibling::dd'),
  ).toHaveText('1 of 1');
  expect(writes).toEqual([]);
});

test('"I\'m not sure yet" is accepted and still leads to the explanation', async ({
  page,
}) => {
  const { frame } = await open(page, [noExtrusion]);
  await next(frame);
  await press(frame).click();
  const panel = frame.getByRole('region', { name: 'Investigate' });
  await panel.getByRole('radio', { name: 'I’m not sure yet' }).check();
  await expect(panel.getByText(/That’s fine/)).toBeVisible();
  await panel
    .getByRole('button', { name: 'Show a possible explanation' })
    .click();
  await expect(
    panel.getByText(/One possibility is that the sketch/),
  ).toBeVisible();
  await expect(panel).not.toContainText(/Incorrect|Wrong|Try again/);
});

test('step 3 fillet warning investigates the ambiguity without claiming geometry', async ({
  page,
}) => {
  const { frame } = await open(page, [fillet]);
  await next(frame);
  await next(frame);
  await press(frame).click();
  const panel = frame.getByRole('region', { name: 'Investigate' });
  await expect(
    panel.getByText(/fillets or chamfers can also raise it/),
  ).toBeVisible();
  await panel
    .getByRole('radio', { name: 'No, a fillet or chamfer can add faces too' })
    .check();
  await panel
    .getByRole('button', { name: 'Show a possible explanation' })
    .click();
  await expect(
    panel.getByText(/cannot separate a second portion/),
  ).toBeVisible();
});

test('investigation state survives Design → Learn and is cleared by reset', async ({
  page,
}) => {
  const { frame } = await open(page, [noExtrusion]);
  await next(frame);
  await press(frame).click();
  const panel = frame.getByRole('region', { name: 'Investigate' });
  await panel.getByRole('radio', { name: 'I’m not sure yet' }).check();
  await frame.getByRole('tab', { name: 'Design', exact: true }).click();
  await frame.getByRole('tab', { name: 'Learn', exact: true }).click();
  await expect(
    panel.getByRole('radio', { name: 'I’m not sure yet' }),
  ).toBeChecked();
  await frame.getByRole('button', { name: 'Reset lesson' }).click();
  await frame.getByRole('button', { name: 'Reset lesson progress' }).click();
  await expect(
    frame.getByRole('heading', { name: 'Learn with Forge' }),
  ).toBeVisible();
  await expect(frame.getByRole('region', { name: 'Investigate' })).toHaveCount(
    0,
  );
});

test('transfer challenge: less guidance first, then a PASS and a plain summary', async ({
  page,
}) => {
  const { frame, bodies } = await open(page, [transferOk]);
  for (let i = 0; i < 4; i++) await next(frame);
  await next(frame, true);
  await frame
    .getByRole('button', { name: 'Start the transfer challenge' })
    .click();
  await expect(
    frame.getByRole('heading', {
      name: 'Transfer challenge: one profile, one extrusion',
    }),
  ).toBeVisible();
  await expect(frame.getByText(/Sketch the L with the Line tool/)).toHaveCount(
    0,
  );
  await expect(frame.getByText(/Full explanation/)).toHaveCount(0);
  await press(frame).click();
  await expect(
    frame.getByText('Forge verified what it can read for this step.'),
  ).toBeVisible();
  expect((bodies[0] as { step_id: string }).step_id).toBe(
    'transfer-single-profile',
  );
  await frame.getByRole('button', { name: 'Mark challenge done' }).click();
  await frame.getByRole('button', { name: 'Finish challenge' }).click();
  await expect(
    frame.getByText(/using one profile and one extrusion/),
  ).toBeVisible();
  await expect(
    frame.getByText(/not a grade or a measure of your skill/),
  ).toBeVisible();
  await expect(frame.locator('body')).not.toContainText(
    /mastery|proficien|score|streak/i,
  );
});

test('keyboard-only flow, 320px layout, reduced motion and accessibility', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const { frame } = await open(page, [noExtrusion]);
  await next(frame);
  const button = press(frame);
  await button.focus();
  await page.keyboard.press('Enter');
  const panel = frame.getByRole('region', { name: 'Investigate' });
  await expect(panel).toBeVisible();
  // Radios: arrow keys move the choice, Space reveals through the next button.
  const first = panel.getByRole('radio').first();
  await first.focus();
  await page.keyboard.press('Space');
  await expect(first).toBeChecked();
  await page.keyboard.press('ArrowDown');
  await expect(panel.getByRole('radio').nth(1)).toBeChecked();
  const reveal = panel.getByRole('button', {
    name: 'Show a possible explanation',
  });
  await reveal.focus();
  await page.keyboard.press('Enter');
  await expect(
    panel.getByText(/One possibility is that the sketch/),
  ).toBeVisible();
  await noOverflow(page);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
});

for (const width of [320, 360, 380, 400, 480, 640])
  test(`investigation and challenge stay usable without horizontal scroll at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 800 });
    const { frame } = await open(page, [noExtrusion]);
    await next(frame);
    await press(frame).click();
    const panel = frame.getByRole('region', { name: 'Investigate' });
    await expect(panel).toBeVisible();
    await panel.getByRole('radio', { name: 'I’m not sure yet' }).check();
    await panel
      .getByRole('button', { name: 'Show a possible explanation' })
      .click();
    await panel.getByRole('button', { name: 'Show what to try next' }).click();
    await expect(
      panel.getByRole('heading', { name: 'Try next' }),
    ).toBeVisible();
    await expect(press(frame)).toBeVisible();
    await expect(
      frame.getByRole('button', { name: 'Request a conceptual hint' }),
    ).toBeVisible();
    await noOverflow(page);
  });
