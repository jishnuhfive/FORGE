import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { authenticatedFixture, signedIn, signedOut } from './auth-fixtures';

async function openLearn(page: Page) {
  await authenticatedFixture(page);
  await page.addInitScript(() =>
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({ onboarded: true }),
    ),
  );
  await page.goto('/');
  await page.getByRole('tab', { name: 'Learn', exact: true }).click();
}
async function setup(page: Page) {
  await page.getByRole('radio', { name: /^Beginner/ }).check();
  await page
    .getByRole('radio', { name: 'Learn CAD fundamentals', exact: true })
    .check();
  await page.getByRole('button', { name: 'Review sample lesson' }).click();
}
async function begin(page: Page) {
  await setup(page);
  await page.getByRole('button', { name: 'Begin lesson' }).click();
}
async function markAndAdvance(page: Page, last = false) {
  await page
    .getByRole('button', { name: 'Mark step done', exact: true })
    .click();
  await expect(page.getByRole('status')).toHaveText('Step marked done by you.');
  await page
    .getByRole('button', {
      name: last ? 'View completion summary' : 'Next step',
      exact: true,
    })
    .click();
}
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    await page
      .locator('.learning-workspace')
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
}
async function accessibility(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          document.getAnimations().filter((a) => a.playState === 'running')
            .length,
      ),
    )
    .toBe(0);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
}
for (const width of [320, 360, 380, 400, 480, 640]) {
  test(`Phase 7 Learn complete journey and layout at ${width}px`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width, height: 950 });
    const requests: string[] = [];
    page.on('request', (request) => {
      if (
        ['fetch', 'xhr'].includes(request.resourceType()) &&
        !new URL(request.url()).pathname.endsWith('/api/me')
      )
        requests.push(request.url());
    });
    const capture = async (state: string) => {
      await noOverflow(page);
      if (browserName === 'chromium' && [320, 380, 480, 640].includes(width))
        await page
          .locator('.app-shell')
          .screenshot({ path: `.cache/phase7/${width}-${state}.png` });
    };
    await openLearn(page);
    await expect(
      page.getByRole('tab', { name: 'Learn', exact: true }),
    ).toHaveAttribute('aria-selected', 'true');
    await capture('A-first-open');
    await page.getByRole('radio', { name: /^Beginner/ }).check();
    await capture('B-experience');
    await page
      .getByRole('radio', { name: 'Learn CAD fundamentals', exact: true })
      .check();
    await page.getByRole('button', { name: 'Review sample lesson' }).click();
    await capture('C-introduction');
    await page.getByRole('button', { name: 'Begin lesson' }).click();
    await capture('D-active');
    await accessibility(page);
    const why = page.getByRole('button', { name: 'Why this step' });
    await why.press('Enter');
    await expect(why).toBeFocused();
    await expect(why).toHaveAttribute('aria-expanded', 'true');
    await capture('E-why');
    const term = page.getByRole('button', { name: 'Sketch', exact: true });
    await term.press('Space');
    await expect(
      page.getByText('A 2D profile used as the basis for many 3D features.'),
    ).toBeVisible();
    await capture('F-vocabulary');
    await page
      .getByRole('button', { name: 'Request a conceptual hint' })
      .press('Enter');
    await expect(
      page.getByRole('heading', { name: 'Conceptual hint' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Tool-specific hint' }),
    ).toHaveCount(0);
    await capture('G-conceptual');
    await page
      .getByRole('button', { name: 'More help: tool-specific hint' })
      .press('Enter');
    await expect(
      page.getByRole('heading', { name: 'Tool-specific hint' }),
    ).toBeVisible();
    await capture('H-tool');
    await page
      .getByRole('button', { name: 'Request full explanation' })
      .press('Enter');
    await expect(
      page.getByRole('heading', { name: 'Full explanation' }),
    ).toBeVisible();
    await capture('I-explanation');
    await expect(
      page.getByText(/Forge isn’t checking the model/),
    ).toBeVisible();
    await expect(
      page.getByText(/PASS|FAIL|WARNING|UNVERIFIED|mastery|grade:/),
    ).toHaveCount(0);
    await markAndAdvance(page);
    await capture('J-progress');
    await page.getByRole('tab', { name: 'Design', exact: true }).click();
    await page.getByRole('tab', { name: 'Learn', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'Turn the profile into depth' }),
    ).toBeVisible();
    await expect(page.getByText('Steps completed: 1 of 3')).toBeVisible();
    await expect(
      page.getByText('Hints requested').locator('..').getByRole('definition'),
    ).toHaveText('3');
    await markAndAdvance(page);
    await markAndAdvance(page, true);
    await expect(
      page.getByRole('heading', { name: 'Lesson complete' }),
    ).toBeFocused();
    await expect(page.getByText('Steps completed: 3 of 3')).toBeVisible();
    await expect(
      page
        .getByText('Steps completed without hints')
        .locator('..')
        .getByRole('definition'),
    ).toHaveText('2');
    await expect(
      page.getByText(/did not inspect or check your CAD model/),
    ).toBeVisible();
    await capture('K-completion');
    await accessibility(page);
    await page
      .getByRole('button', { name: 'Reset lesson', exact: true })
      .click();
    await page.getByRole('button', { name: 'Keep learning' }).click();
    await expect(
      page.getByRole('heading', { name: 'Lesson complete' }),
    ).toBeVisible();
    await page
      .getByRole('button', { name: 'Reset lesson', exact: true })
      .click();
    await page.getByRole('button', { name: 'Reset lesson progress' }).click();
    await expect(
      page.getByRole('heading', { name: 'Learn with Forge' }),
    ).toBeVisible();
    await expect(
      page.getByRole('radio', { name: /^Beginner/ }),
    ).not.toBeChecked();
    expect(requests).toEqual([]);
    expect(
      await page.evaluate(() => ({
        local: Object.keys(localStorage),
        session: Object.keys(sessionStorage),
      })),
    ).toEqual({ local: ['forge.preferences.v1'], session: [] });
  });
}
test('Phase 7 keyboard-only setup, hints, navigation and reset focus', async ({
  page,
}) => {
  await openLearn(page);
  const beginner = page.getByRole('radio', { name: /^Beginner/ });
  await beginner.focus();
  await page.keyboard.press('Space');
  // Native radio groups retain arrow-key behavior and a single tab stop.
  await page.keyboard.press('ArrowDown');
  await expect(
    page.getByRole('radio', { name: /^Some experience/ }),
  ).toBeChecked();
  await page.keyboard.press('Tab');
  await page.keyboard.press('Space');
  await expect(
    page.getByRole('radio', { name: 'Learn CAD fundamentals', exact: true }),
  ).toBeChecked();
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await expect(
    page.getByRole('heading', { name: 'Sketch to solid' }),
  ).toBeFocused();
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await expect(
    page.getByRole('heading', { name: 'Begin with a profile' }),
  ).toBeFocused();
  const reset = page.getByRole('button', { name: 'Reset lesson', exact: true });
  await reset.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: 'Reset this lesson?' });
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Tab');
    expect(
      await dialog.evaluate((node) => node.contains(document.activeElement)),
    ).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(reset).toBeFocused();
});
test('Phase 7 reduced motion, opaque controls and forced colors retain lesson semantics', async ({
  page,
  browserName,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await openLearn(page);
  await begin(page);
  await page.getByRole('button', { name: 'Request a conceptual hint' }).click();
  expect(
    await page
      .locator('.learning-reveal')
      .first()
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe('none');
  await page.getByRole('button', { name: 'Workspace menu' }).click();
  await page.getByRole('menuitem', { name: 'Appearance & settings' }).click();
  await page.getByLabel('Reduce transparency').check();
  await page.getByRole('button', { name: /Back to workspace/ }).click();
  await expect(
    page.getByRole('heading', { name: 'Conceptual hint' }),
  ).toBeVisible();
  expect(
    await page
      .locator('.tabs-list')
      .evaluate((el) => getComputedStyle(el, '::before').backdropFilter),
  ).toBe('none');
  await accessibility(page);
  if (browserName === 'chromium') {
    await page.emulateMedia({ forcedColors: 'active' });
    await accessibility(page);
  }
});
test('Phase 7 reload and expired account teardown clear learning; ordinary focus preserves it', async ({
  page,
}) => {
  await openLearn(page);
  await begin(page);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(
    page.getByRole('heading', { name: 'Begin with a profile' }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole('tab', { name: 'Learn', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Learn with Forge' }),
  ).toBeVisible();
  await begin(page);
  let expired = true;
  await page.route('**/api/me', (route) =>
    route.fulfill({ json: expired ? signedOut : signedIn }),
  );
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(
    page.getByText('Connect securely with your Onshape account'),
  ).toBeVisible();
  expired = false;
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await page.getByRole('tab', { name: 'Learn', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Learn with Forge' }),
  ).toBeVisible();
});
test('Phase 7 UI Lab exposes safe authored states and unavailable/error recovery', async ({
  page,
}) => {
  await page.goto('http://127.0.0.1:4174/#/lab');
  await page.getByLabel('Preview state').selectOption('Learn mode');
  for (const state of [
    'Setup',
    'Experience selected',
    'Introduction',
    'Active step',
    'Why open',
    'Vocabulary open',
    'Conceptual hint',
    'Tool-specific hint',
    'Full explanation',
    'Mid-lesson',
    'Completion',
    'No lesson selected',
    'Lesson unavailable',
    'Loading failure',
    'Invalid definition',
  ]) {
    await page.getByLabel('Learning preview state').selectOption(state);
    await noOverflow(page);
  }
  await page.getByRole('button', { name: 'Open sample lesson' }).click();
  await expect(
    page.getByRole('heading', { name: 'Learn with Forge' }),
  ).toBeVisible();
});
