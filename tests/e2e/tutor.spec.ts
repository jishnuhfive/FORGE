import { expect, test } from '@playwright/test';
import type { FrameLocator, Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { signedIn } from './auth-fixtures';

// Synthetic only: no live Onshape, no live AI provider. Every server decision is
// scripted; the point is what the browser does with it.
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'wait' });
});

const query = (document: string) =>
  `documentId=${document.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
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
const check = (step: string, outcome: string, results: object[]) => ({
  lesson_id: 'mounting-bracket',
  step_id: step,
  outcome,
  results,
  captured_at: '2026-01-01T12:00:00+00:00',
  consistency: 'unverified',
  evidence_token: 'synthetic-payload.synthetic-mac',
});
const notYet = check('base-solid', 'not_met', [
  req(
    'extrude.exists',
    'FAIL',
    'missing',
    'Forge sees no active extrude feature yet.',
  ),
  req('body.solid', 'FAIL', 'missing', 'Forge sees no solid body yet.'),
]);
const fixed = check('base-solid', 'verified', [
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
const transferOk = check('transfer-single-profile', 'verified', [
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
]);
const answer = {
  explanation:
    'One extrusion may not be enough for this step. Think about how the second portion could exist.',
  reasoning_question: 'Could one closed L-shaped profile make both portions?',
  next_action:
    'Check whether the second portion is another extrusion or part of one profile.',
  observed: [
    {
      source: 'check',
      status: 'FAIL',
      statement: 'Forge sees no active extrude feature yet.',
    },
  ],
  unknowns: [
    'Forge’s current evidence cannot read the profile’s exact shape or dimensions.',
  ],
  notes: [
    'Based on your last check. If you’ve changed your model since, press Check my step again.',
  ],
  latest_check: {
    outcome: 'not_met',
    captured_at: '2026-01-01T12:00:00+00:00',
  },
  used_cad: false,
  captured_at: null,
  capability_state: 'read_only',
};
interface Sent {
  step_id: string;
  evidence_token: string | null;
  learner: {
    guidance: string;
    hints_revealed: number;
    investigation: object | null;
  };
}
type Tutor = (n: number, body: Sent) => string;
const ok: Tutor = () =>
  [
    { type: 'progress', stage: 'understanding' },
    { type: 'result', result: answer },
  ]
    .map((e) => JSON.stringify(e))
    .join('\n') + '\n';

async function open(
  page: Page,
  checks: object[],
  tutor: Tutor = ok,
  document = 'a',
  hold: Promise<void> | null = null,
) {
  const tutorBodies: Sent[] = [];
  const writes: string[] = [];
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  let checkCalls = 0;
  await page.route('https://forge-panel.test/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const mutating = request.method() !== 'GET';
    if (
      mutating &&
      url.pathname !== '/api/learning/check-step' &&
      url.pathname !== '/api/learning/tutor'
    )
      writes.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/api/me') await route.fulfill({ json: signedIn });
    else if (url.pathname === '/api/learning/check-step')
      await route.fulfill({
        json: checks[Math.min(checkCalls++, checks.length - 1)]!,
      });
    else if (url.pathname === '/api/learning/tutor') {
      const body = request.postDataJSON() as Sent;
      tutorBodies.push(body);
      if (hold) await hold;
      await route
        .fulfill({
          contentType: 'application/x-ndjson',
          body: tutor(tutorBodies.length, body),
        })
        .catch(() => undefined);
    } else
      await route.fulfill({
        response: await page.request.get(
          `http://127.0.0.1:4173${url.pathname}${url.search}`,
        ),
      });
  });
  await page.route('https://cad.onshape.com/forge-tutor-test', (route) =>
    route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><html lang="en"><head><title>Synthetic Onshape parent</title></head><body style="margin:0"><iframe title="Forge extension" style="width:100vw;height:100vh;border:0" src="https://forge-panel.test/extension?${query(document)}"></iframe></body></html>`,
    }),
  );
  await page.goto('https://cad.onshape.com/forge-tutor-test');
  const frame = page.frameLocator('iframe');
  await frame.getByRole('tab', { name: 'Learn', exact: true }).click();
  await frame.getByRole('radio', { name: /^Beginner/ }).check();
  await frame
    .getByRole('radio', { name: 'Build a mounting bracket', exact: true })
    .check();
  await frame.getByRole('button', { name: /^Review/ }).click();
  await frame.getByRole('button', { name: 'Begin lesson' }).click();
  return { frame, tutorBodies, writes };
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
const ask = async (frame: FrameLocator, text: string, first = true) => {
  if (first) await frame.getByRole('button', { name: /^Ask Forge$/ }).click();
  await frame.getByLabel('Ask about this step').fill(text);
  await frame.getByLabel('Ask about this step').press('Control+Enter');
};
const noOverflow = async (page: Page) =>
  expect(
    await page
      .frames()
      .find((f) => f.url().includes('forge-panel.test/extension'))!
      .evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBe(true);

test('A: a failing check, then Ask Forge explains without changing anything', async ({
  page,
}) => {
  const { frame, tutorBodies, writes } = await open(page, [notYet]);
  await next(frame);
  await press(frame).click();
  await expect(
    frame.getByText(/something this step still needs/),
  ).toBeVisible();
  await ask(frame, 'Why isn’t my second part showing up?');
  await expect(
    frame.getByText(/One extrusion may not be enough/),
  ).toBeVisible();
  const observed = frame.getByRole('region', { name: 'What Forge observed' });
  await expect(
    observed.getByText('Forge sees no active extrude feature yet.'),
  ).toBeVisible();
  await frame.getByText(/^Still unknown \(\d+\)/).click();
  await expect(
    frame.getByRole('region', { name: 'Still unknown' }),
  ).toBeVisible();
  // The deterministic result and everything around it are untouched.
  await expect(
    frame.getByText(/something this step still needs/),
  ).toBeVisible();
  await expect(frame.getByText('Steps completed: 1 of 5')).toBeVisible();
  await expect(frame.getByText('Conceptual hint', { exact: true })).toHaveCount(
    0,
  );
  expect(tutorBodies).toHaveLength(1);
  expect(tutorBodies[0]).toMatchObject({
    step_id: 'base-solid',
    evidence_token: 'synthetic-payload.synthetic-mac',
  });
  expect(writes).toEqual([]);
});

test('B: investigation stays authored; the tutor stays neutral and cannot resolve it', async ({
  page,
}) => {
  const { frame, tutorBodies } = await open(page, [notYet, fixed]);
  await next(frame);
  await press(frame).click();
  const investigate = frame.getByRole('region', { name: 'Investigate' });
  await investigate
    .getByRole('radio', { name: 'Turn the closed sketch into a 3D feature' })
    .check();
  await ask(frame, 'What should I try next?');
  await expect(
    frame.getByText(/One extrusion may not be enough/),
  ).toBeVisible();
  // Only whether a prediction was given is shared, never which one.
  expect(tutorBodies[0]!.learner.investigation).toMatchObject({
    prediction_answered: true,
    resolved: false,
  });
  expect(JSON.stringify(tutorBodies[0])).not.toMatch(/3D feature|make-3d/);
  // The authored explanation flow still works, and the tutor resolved nothing.
  await expect(investigate.getByText(/Resolved\./)).toHaveCount(0);
  await investigate
    .getByRole('button', { name: 'Show a possible explanation' })
    .click();
  await expect(
    investigate.getByText(/One possibility is that the sketch/),
  ).toBeVisible();
  // Only an explicit re-check resolves it.
  await press(frame).click();
  await expect(
    investigate.getByText(/Resolved\. Forge sees an active extrude feature\./),
  ).toBeVisible();
});

test('C: in the transfer challenge help is lighter and declared independent', async ({
  page,
}) => {
  const { frame, tutorBodies } = await open(page, [transferOk]);
  for (let i = 0; i < 4; i++) await next(frame);
  await next(frame, true);
  await frame
    .getByRole('button', { name: 'Start the transfer challenge' })
    .click();
  await ask(frame, 'How should I start?');
  await expect(
    frame.getByText(/One extrusion may not be enough/),
  ).toBeVisible();
  expect(tutorBodies[0]).toMatchObject({ step_id: 'transfer-single-profile' });
  expect(tutorBodies[0]!.learner).toMatchObject({
    guidance: 'independent',
    hints_revealed: 0,
  });
  // No guided walkthrough is replayed and there is no grading vocabulary.
  await expect(frame.getByText(/Sketch the L with the Line tool/)).toHaveCount(
    0,
  );
  await expect(frame.locator('body')).not.toContainText(
    /mastery|proficien|score|grade|streak/i,
  );
});

test('D: when the AI is unavailable the lesson stays fully usable', async ({
  page,
}) => {
  const failing: Tutor = () =>
    JSON.stringify({
      type: 'error',
      code: 'timeout',
      retry_after_seconds: null,
    }) + '\n';
  const { frame } = await open(page, [fixed], failing);
  await next(frame);
  await ask(frame, 'What does extrude mean?');
  const alert = frame.getByRole('alert');
  await expect(alert).toContainText('Ask Forge took too long. Try again.');
  await expect(alert).toContainText(
    'Your lesson, hints and Check my step still work.',
  );
  await expect(frame.getByRole('button', { name: 'Try again' })).toBeVisible();
  // Authored help and the deterministic check keep working.
  await frame.getByRole('button', { name: 'Why this step' }).click();
  await expect(frame.getByText(/keeps the same cross-section/)).toBeVisible();
  await frame
    .getByRole('button', { name: 'Request a conceptual hint' })
    .click();
  await expect(
    frame.getByText('Conceptual hint', { exact: true }),
  ).toBeVisible();
  await press(frame).click();
  await expect(
    frame.getByText(/Forge verified what it can read/),
  ).toBeVisible();
});

test('E: the conversation is cleared when the context changes', async ({
  page,
}) => {
  const { frame } = await open(page, [fixed]);
  await next(frame);
  await ask(frame, 'What does extrude mean?');
  await expect(
    frame.getByText(/One extrusion may not be enough/),
  ).toBeVisible();
  // A different step is a different conversation.
  await next(frame);
  await expect(frame.getByText(/One extrusion may not be enough/)).toHaveCount(
    0,
  );
  await expect(
    frame.getByRole('button', { name: /^Ask Forge$/ }),
  ).toHaveAttribute('aria-expanded', 'false');
  // A different document starts completely fresh.
  await page.evaluate(() => {
    const frameEl = document.querySelector('iframe')!;
    frameEl.src = frameEl.src.replace(
      /documentId=a+/,
      'documentId=' + 'd'.repeat(24),
    );
  });
  await frame.getByRole('tab', { name: 'Learn', exact: true }).click();
  await expect(
    frame.getByRole('heading', { name: 'Learn with Forge' }),
  ).toBeVisible();
  await expect(frame.getByText(/One extrusion may not be enough/)).toHaveCount(
    0,
  );
});

test('keyboard operation and the cancel control', async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => (release = resolve));
  const { frame } = await open(page, [fixed], ok, 'a', gate);
  await next(frame);
  const toggle = frame.getByRole('button', { name: /^Ask Forge$/ });
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(
    frame.getByRole('dialog', { name: 'Ask Forge chat' }),
  ).toBeVisible();
  const field = frame.getByLabel('Ask about this step');
  await expect(field).toBeFocused();
  await page.keyboard.type('What does extrude mean?');
  await page.keyboard.press('Control+Enter');
  await expect(frame.getByText('Reading your question…')).toBeVisible();
  await expect(field).toBeDisabled();
  await frame.getByRole('button', { name: 'Stop request' }).click();
  await expect(frame.getByRole('alert')).toContainText('Request cancelled.');
  release();
  await expect(frame.getByText(/One extrusion may not be enough/)).toHaveCount(
    0,
  );
});

test('F: the tutor is usable at 320px with reduced motion, no overflow and no axe violations', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const { frame } = await open(page, [notYet]);
  await next(frame);
  await press(frame).click();
  await ask(frame, 'Why isn’t my second part showing up?');
  await expect(
    frame.getByText(/One extrusion may not be enough/),
  ).toBeVisible();
  await expect(
    frame.getByRole('region', { name: 'What Forge observed' }),
  ).toBeVisible();
  await frame.getByText(/^Still unknown \(\d+\)/).click();
  await expect(
    frame.getByRole('region', { name: 'Still unknown' }),
  ).toBeVisible();
  await expect(frame.getByRole('button', { name: 'Send' })).toBeVisible();
  await frame.getByRole('button', { name: 'Send' }).scrollIntoViewIfNeeded();
  await noOverflow(page);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
});

for (const scheme of ['dark', 'light'] as const)
  test(`the Send control is legible in ${scheme} mode`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    const { frame } = await open(page, [fixed]);
    await next(frame);
    await frame.getByRole('button', { name: /^Ask Forge$/ }).click();
    await frame.getByLabel('Ask about this step').fill('Why?');
    const ratio = await frame
      .getByRole('button', { name: 'Send' })
      .evaluate(async (el) => {
        await Promise.all(el.getAnimations().map((a) => a.finished));
        const parse = (v: string) =>
          (v.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number);
        const lum = ([r, g, b]: number[]) => {
          const f = (c: number) => {
            const s = c / 255;
            return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
          };
          return 0.2126 * f(r!) + 0.7152 * f(g!) + 0.0722 * f(b!);
        };
        const s = getComputedStyle(el);
        const a = lum(parse(s.color));
        const b = lum(parse(s.backgroundColor));
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      });
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });
