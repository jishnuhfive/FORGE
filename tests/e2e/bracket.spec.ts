import { expect, test } from '@playwright/test';
import type { FrameLocator, Page, Request } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// Synthetic only: no live Onshape, no live Groq. The server's decisions are scripted.
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
});

const query = `documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
type Reply = { status?: number; json: unknown };
const requirement = (
  id: string,
  status: string,
  reason: string,
  finding: string,
  blocking = true,
) => ({
  requirement_id: id,
  description: 'Requirement',
  blocking,
  evidence: ['features'],
  outcome: { status, reason, finding },
});
const check = (step: string, outcome: string, results: object[]) => ({
  lesson_id: 'mounting-bracket',
  step_id: step,
  outcome,
  results,
  captured_at: '2026-01-01T12:00:00+00:00',
  consistency: 'unverified',
  evidence_token: 'synthetic-payload.synthetic-mac',
});

async function open(page: Page, replies: Reply[]) {
  const writes: string[] = [];
  const bodies: unknown[] = [];
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  let call = 0;
  await page.route('https://forge-panel.test/**', async (route) => {
    const request: Request = route.request();
    const url = new URL(request.url());
    if (
      request.method() !== 'GET' &&
      url.pathname !== '/api/learning/check-step'
    )
      writes.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/me') await route.fulfill({ json: signedIn });
    else if (url.pathname === '/api/learning/check-step') {
      bodies.push(request.postDataJSON());
      const reply = replies[Math.min(call++, replies.length - 1)]!;
      await route.fulfill({ status: reply.status ?? 200, json: reply.json });
    } else
      await route.fulfill({
        response: await page.request.get(
          `http://127.0.0.1:4173${url.pathname}${url.search}`,
        ),
      });
  });
  await page.route('https://cad.onshape.com/forge-bracket-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic Onshape parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-panel.test/extension?${query}"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-bracket-test');
  const frame = page.frameLocator('iframe');
  await frame.getByRole('tab', { name: 'Learn', exact: true }).click();
  await frame.getByRole('radio', { name: /^Beginner/ }).check();
  await frame
    .getByRole('radio', { name: 'Complete a guided project', exact: true })
    .check();
  await frame.getByRole('button', { name: /^Review/ }).click();
  await frame.getByRole('button', { name: 'Begin lesson' }).click();
  return { frame, writes, bodies, calls: () => call };
}
const press = (frame: FrameLocator) =>
  frame.getByRole('button', { name: /^Check (my step|again)$/ });

test('correct step: Forge verifies it and learner completion stays separate', async ({
  page,
}) => {
  const { frame, writes, bodies } = await open(page, [
    {
      json: check('base-sketch', 'verified', [
        requirement(
          'sketch.exists',
          'PASS',
          'met',
          'Forge sees 1 active sketch.',
        ),
        requirement(
          'sketch.profile',
          'UNVERIFIED',
          'not_observable',
          'Forge’s current evidence cannot read sketch geometry.',
          false,
        ),
      ]),
    },
  ]);
  await press(frame).click();
  await expect(
    frame.getByText('Forge verified what it can read for this step.'),
  ).toBeVisible();
  await expect(
    frame.locator('.status-badge', { hasText: 'Can’t verify' }),
  ).toBeVisible();
  await expect(frame.getByText('Steps completed: 0 of 5')).toBeVisible();
  await expect(frame.getByText('1 of 4')).toBeVisible();
  expect(bodies[0]).toEqual({
    lesson_id: 'mounting-bracket',
    step_id: 'base-sketch',
    context: {
      documentId: 'a'.repeat(24),
      workspaceId: 'b'.repeat(24),
      elementId: 'c'.repeat(24),
      revisionKind: 'workspace',
    },
  });
  expect(writes).toEqual([]);
});

test('incorrect step fails honestly, then a fix passes on re-check', async ({
  page,
}) => {
  const { frame } = await open(page, [
    {
      json: check('base-sketch', 'not_met', [
        requirement(
          'sketch.exists',
          'FAIL',
          'missing',
          'Forge sees no active sketch yet.',
        ),
      ]),
    },
    {
      json: check('base-sketch', 'verified', [
        requirement(
          'sketch.exists',
          'PASS',
          'met',
          'Forge sees 1 active sketch.',
        ),
      ]),
    },
  ]);
  await press(frame).click();
  await expect(frame.getByText('Not yet')).toBeVisible();
  // A failure never reveals any hint by itself.
  await expect(frame.getByText('Conceptual hint', { exact: true })).toHaveCount(
    0,
  );
  await press(frame).click();
  await expect(
    frame.getByText('Forge verified what it can read for this step.'),
  ).toBeVisible();
  await expect(frame.getByText('Not yet')).toHaveCount(0);
});

test('an accepted alternative approach is reported as such', async ({
  page,
}) => {
  const { frame } = await open(page, [
    {
      json: check('base-sketch', 'verified', [
        requirement(
          'bracket.second_portion',
          'PASS',
          'met_by_alternative',
          'Forge sees a single body with more faces than a plain block.',
        ),
      ]),
    },
  ]);
  await press(frame).click();
  await expect(frame.getByText(/single body with more faces/)).toBeVisible();
});

test('a malformed or failing server response can never verify a step', async ({
  page,
}) => {
  const { frame } = await open(page, [
    { json: { ...check('base-sketch', 'verified', []), extra: 1 } },
  ]);
  await press(frame).click();
  await expect(frame.getByText(/couldn’t verify that response/)).toBeVisible();
  await expect(frame.getByText('0 of 4')).toBeVisible();
});

test('cooldown is explained, throttles the control and never auto-retries', async ({
  page,
}) => {
  const { frame, calls } = await open(page, [
    { status: 429, json: { detail: 'rate_limited', retry_after_seconds: 5 } },
  ]);
  await press(frame).click();
  await expect(frame.getByText(/can check again shortly/)).toBeVisible();
  await expect(press(frame)).toHaveAttribute('aria-disabled', 'true');
  await page.waitForTimeout(6500);
  await expect(press(frame)).toHaveAttribute('aria-disabled', 'false');
  expect(calls()).toBe(1);
});

test('keyboard operation, 320px layout, reduced motion and accessibility', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const { frame } = await open(page, [
    {
      json: check('base-sketch', 'verified', [
        requirement(
          'sketch.exists',
          'PASS',
          'met',
          'Forge sees 1 active sketch.',
        ),
      ]),
    },
  ]);
  const button = frame.getByRole('button', { name: 'Check my step' });
  await button.focus();
  await page.keyboard.press('Enter');
  await expect(
    frame.getByText('Forge verified what it can read for this step.'),
  ).toBeVisible();
  const toggle = frame.getByRole('button', { name: /How Forge checked this/ });
  await toggle.focus();
  await page.keyboard.press('Space');
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(frame.getByText(/no AI involved/)).toBeVisible();
  const overflow = await page
    .frames()
    .find((f) => f.url().includes('forge-panel.test/extension'))!
    .evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  expect(overflow).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
});

// WCAG contrast of the control's label against its own fill, measured in the
// browser from computed styles, so a layered-material regression is caught.
const contrast = async (button: import('@playwright/test').Locator) =>
  button.evaluate(async (el) => {
    // Measure the settled colors, not a hover/state transition in progress.
    await Promise.all(el.getAnimations().map((a) => a.finished));
    const parse = (value: string) =>
      (value.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number);
    const lum = ([r, g, b]: number[]) => {
      const f = (c: number) => {
        const s = c / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * f(r!) + 0.7152 * f(g!) + 0.0722 * f(b!);
    };
    const style = getComputedStyle(el);
    const a = lum(parse(style.color));
    const b = lum(parse(style.backgroundColor));
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  });

for (const scheme of ['dark', 'light'] as const)
  test(`Check my step is legible when enabled and when cooling down (${scheme})`, async ({
    page,
  }) => {
    await page.emulateMedia({ colorScheme: scheme });
    const { frame } = await open(page, [
      {
        status: 429,
        json: { detail: 'rate_limited', retry_after_seconds: 20 },
      },
    ]);
    const enabled = frame.getByRole('button', { name: 'Check my step' });
    expect(await contrast(enabled)).toBeGreaterThanOrEqual(4.5);
    await enabled.click();
    const cooling = frame.getByRole('button', { name: 'Check again' });
    await expect(cooling).toHaveAttribute('aria-disabled', 'true');
    expect(await contrast(cooling)).toBeGreaterThanOrEqual(4.5);
  });
