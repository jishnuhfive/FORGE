import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Learn } from '../features/Learn';
import { Workspace } from '../App';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { OnshapeContext } from '../onshape/store';
import { standaloneState } from '../onshape/model';
import type { ClientState } from '../onshape/model';
import { bracketResource } from './catalog';
import { LearningProvider } from './LearningProvider';
import { mountingBracket } from './bracket';
import { isLesson } from './lesson';
import { CheckError, parseCheck } from './check';
import { initialSession, reduceSession, sessionProgress } from './session';
import type { LearningAction, LearningSession } from './session';

const me: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Test learner',
  connection: 'connected',
  csrf_token: 'a'.repeat(64),
  verified_at: 1700000000,
};
const connected: ClientState = {
  status: 'EMBEDDED_CONNECTED',
  context: {
    documentId: 'a'.repeat(24),
    elementId: 'c'.repeat(24),
    server: 'https://cad.onshape.com',
    revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
    elementType: 'partStudio',
  },
  selection: { status: 'waiting', entities: [] },
};
const requirement = (
  id: string,
  status: string,
  reason: string,
  blocking = true,
) => ({
  requirement_id: id,
  description: 'An extrusion exists',
  blocking,
  evidence: ['features'],
  outcome: { status, reason, finding: `Finding for ${id}.` },
});
const response = (outcome: string, results: object[]) => ({
  lesson_id: 'mounting-bracket',
  step_id: 'base-sketch',
  outcome,
  results,
  captured_at: '2026-01-01T12:00:00+00:00',
  consistency: 'unverified',
});
const reply = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

function open(state: ClientState = connected, auth: Me = me) {
  render(
    <AuthContext.Provider
      value={{ me: auth, reload: async () => {}, endSession: () => {} }}
    >
      <OnshapeContext.Provider value={state}>
        <LearningProvider lesson={mountingBracket}>
          <Learn resource={bracketResource} />
        </LearningProvider>
      </OnshapeContext.Provider>
    </AuthContext.Provider>,
  );
  fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
  fireEvent.click(
    screen.getByRole('radio', { name: 'Complete a guided project' }),
  );
  fireEvent.click(screen.getByRole('button', { name: /^Review/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Begin lesson' }));
}
const check = () => screen.getByRole('button', { name: 'Check my step' });
let fetcher: ReturnType<typeof vi.fn>;
beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(
    'forge.preferences.v1',
    JSON.stringify({ onboarded: true }),
  );
  window.location.hash = '';
  fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
});
afterEach(() => vi.unstubAllGlobals());

describe('mounting bracket lesson', () => {
  it('is valid authored content with server-owned checks only on step ids', () => {
    expect(isLesson(mountingBracket)).toBe(true);
    expect(mountingBracket.steps.map((s) => s.id)).toEqual([
      'base-sketch',
      'base-solid',
      'second-portion',
      'mounting-holes',
      'review',
    ]);
    // The review step is learner-reported only: nothing Forge can verify.
    expect(mountingBracket.steps.filter((s) => s.check)).toHaveLength(4);
    expect(JSON.stringify(mountingBracket)).not.toMatch(/perfect|100%|safe/i);
  });
  it('offers an explicit control and makes no request until pressed', () => {
    open();
    expect(check()).toBeEnabled();
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByText(/never changes your model/)).toBeVisible();
  });
  it('sends only the lesson, step and validated workspace context', async () => {
    fetcher.mockReturnValue(
      reply(
        response('verified', [requirement('sketch.exists', 'PASS', 'met')]),
      ),
    );
    open();
    fireEvent.click(check());
    await screen.findByText(/Forge verified what it can read/);
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/learning/check-step');
    expect(init.method).toBe('POST');
    expect(init.headers).toMatchObject({ 'X-CSRF-Token': me.csrf_token });
    expect(JSON.parse(init.body as string)).toEqual({
      lesson_id: 'mounting-bracket',
      step_id: 'base-sketch',
      context: {
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
        revisionKind: 'workspace',
      },
    });
  });
  it('PASS records Forge verification separately from learner completion', async () => {
    fetcher.mockReturnValue(
      reply(
        response('verified', [requirement('sketch.exists', 'PASS', 'met')]),
      ),
    );
    open();
    fireEvent.click(check());
    await screen.findByText(/Forge verified what it can read/);
    expect(screen.getByText('Steps completed: 0 of 5')).toBeVisible();
    expect(screen.getByText('1 of 4')).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Mark step done' }),
    ).toBeVisible();
  });
  it('FAIL explains what is missing and does not reveal any hint', async () => {
    fetcher.mockReturnValue(
      reply(
        response('not_met', [requirement('sketch.exists', 'FAIL', 'missing')]),
      ),
    );
    open();
    fireEvent.click(check());
    await screen.findByText(/something this step still needs/);
    expect(screen.getByText('Not yet')).toBeVisible();
    expect(screen.queryByText('Conceptual hint')).not.toBeInTheDocument();
    expect(screen.queryByText(/Full explanation/)).not.toBeInTheDocument();
    expect(screen.getByText('Steps Forge verified')).toBeVisible();
    expect(screen.getByText('0 of 4')).toBeVisible();
  });
  it('UNVERIFIED reads as normal and lists what cannot be checked', async () => {
    fetcher.mockReturnValue(
      reply(
        response('verified', [
          requirement('sketch.exists', 'PASS', 'met'),
          requirement('sketch.profile', 'UNVERIFIED', 'not_observable', false),
        ]),
      ),
    );
    open();
    fireEvent.click(check());
    await screen.findByText('What Forge can’t verify');
    expect(screen.getByText('Can’t verify')).toBeVisible();
    expect(screen.getByText(/Finding for sketch.profile/)).toBeVisible();
  });
  it('warning is shown as a worth-a-look item, not a pass or failure', async () => {
    fetcher.mockReturnValue(
      reply(
        response('unverified', [
          requirement('bracket.second_portion', 'WARNING', 'ambiguous_signal'),
        ]),
      ),
    );
    open();
    fireEvent.click(check());
    await screen.findByText('Worth a look');
    expect(screen.getByText(/can’t fully verify/)).toBeVisible();
  });
  it('evidence is disclosed progressively and says no AI was used', async () => {
    fetcher.mockReturnValue(
      reply(
        response('verified', [requirement('sketch.exists', 'PASS', 'met')]),
      ),
    );
    open();
    fireEvent.click(check());
    await screen.findByText(/Forge verified what it can read/);
    expect(screen.queryByText(/no AI involved/)).not.toBeInTheDocument();
    const toggle = screen.getByRole('button', {
      name: /How Forge checked this/,
    });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/no AI involved/)).toBeVisible();
    expect(screen.getByText(/Feature names are never used/)).toBeVisible();
  });
  it('coalesces a double press into one request', async () => {
    let finish: (value: Response) => void = () => {};
    fetcher.mockReturnValue(new Promise<Response>((r) => (finish = r)));
    open();
    fireEvent.click(check());
    fireEvent.click(check());
    expect(await screen.findByText('Checking current model…')).toBeVisible();
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(check()).toHaveAttribute('aria-disabled', 'true');
    await act(async () => {
      finish(
        new Response(
          JSON.stringify(
            response('verified', [requirement('sketch.exists', 'PASS', 'met')]),
          ),
        ),
      );
    });
    await screen.findByText(/Forge verified what it can read/);
  });
  it('cooldown disables the control briefly and never retries on its own', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    fetcher.mockReturnValue(
      reply({ detail: 'rate_limited', retry_after_seconds: 5 }, 429),
    );
    open();
    fireEvent.click(check());
    await screen.findByText(/can check again shortly/);
    expect(screen.getByRole('button', { name: 'Check again' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
    await act(async () => {
      vi.advanceTimersByTime(6000);
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Check again' }),
      ).toHaveAttribute('aria-disabled', 'false'),
    );
    vi.useRealTimers();
  });
  it('explains a missing Part Studio context without any request', async () => {
    open(standaloneState);
    fireEvent.click(check());
    expect(
      await screen.findByText(/Open this lesson inside a Part Studio/),
    ).toBeVisible();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('explains a signed-out session without any request', async () => {
    open(connected, { ...me, csrf_token: null });
    fireEvent.click(check());
    expect(await screen.findByText(/Sign in with Onshape/)).toBeVisible();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('a server failure is a safe message with no status code or detail', async () => {
    fetcher.mockReturnValue(reply({ detail: 'secret stack trace' }, 500));
    open();
    fireEvent.click(check());
    await screen.findByText(/couldn’t read your model right now/);
    expect(screen.queryByText(/secret|500/)).not.toBeInTheDocument();
  });
  it('a malformed response can never verify a step', async () => {
    fetcher.mockReturnValue(
      reply({ ...response('verified', []), extra: true }),
    );
    open();
    fireEvent.click(check());
    await screen.findByText(/couldn’t verify that response/);
    expect(screen.getByText('0 of 4')).toBeVisible();
  });
});

describe('check response parsing', () => {
  const good = response('verified', [requirement('a.b', 'PASS', 'met')]);
  it('accepts the exact contract', () => {
    expect(parseCheck(good).outcome).toBe('verified');
  });
  it.each([
    [
      'unknown status',
      { ...good, results: [requirement('a', 'GREAT', 'met')] },
    ],
    ['unknown reason', { ...good, results: [requirement('a', 'PASS', 'x')] }],
    ['extra field', { ...good, model_says: 'PASS' }],
    ['other lesson', { ...good, lesson_id: 'other' }],
    ['no results', { ...good, results: [] }],
    [
      'blank finding',
      {
        ...good,
        results: [
          {
            ...requirement('a', 'PASS', 'met'),
            outcome: { status: 'PASS', reason: 'met', finding: ' ' },
          },
        ],
      },
    ],
  ])('rejects %s', (_name, value) => {
    expect(() => parseCheck(value)).toThrow(CheckError);
  });
});

describe('Forge verification state', () => {
  const run = (actions: LearningAction[]): LearningSession =>
    actions.reduce<LearningSession>(
      (state, action) => reduceSession(mountingBracket, state, action),
      initialSession(),
    );
  const started: LearningAction[] = [
    { type: 'experience', value: 'beginner' },
    { type: 'goal', value: 'guided-project' },
    { type: 'review' },
    { type: 'start' },
  ];
  it('records a verified checkable step without marking it done', () => {
    const state = run([
      ...started,
      { type: 'check-verified', stepId: 'base-sketch' },
    ]);
    const progress = sessionProgress(state, mountingBracket);
    expect(progress).toMatchObject({
      forgeVerified: 1,
      checkable: 4,
      completed: 0,
    });
  });
  it('ignores stale, unknown and non-checkable step ids and duplicates', () => {
    const state = run([
      ...started,
      { type: 'check-verified', stepId: 'mounting-holes' },
      { type: 'check-verified', stepId: 'nonsense' },
      { type: 'check-verified', stepId: 'base-sketch' },
      { type: 'check-verified', stepId: 'base-sketch' },
    ]);
    expect(sessionProgress(state, mountingBracket).forgeVerified).toBe(1);
  });
  it('never verifies from learner completion alone', () => {
    const state = run([
      ...started,
      { type: 'mark-done', stepId: 'base-sketch' },
      { type: 'advance', stepId: 'base-sketch' },
    ]);
    const progress = sessionProgress(state, mountingBracket);
    expect(progress.completed).toBe(1);
    expect(progress.forgeVerified).toBe(0);
  });
});

describe('lesson selection in the workspace', () => {
  it('the guided-project goal opens the mounting bracket lesson', () => {
    render(<Workspace />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Learn' }), {
      key: 'Enter',
    });
    fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
    fireEvent.click(
      screen.getByRole('radio', { name: 'Complete a guided project' }),
    );
    fireEvent.click(screen.getByRole('button', { name: /^Review/ }));
    expect(
      screen.getByRole('heading', { name: 'Mounting bracket' }),
    ).toBeVisible();
    expect(screen.getByText(/Forge checks the parts of it/)).toBeVisible();
  });
  it('the fundamentals goal still opens the sample with no checking', () => {
    render(<Workspace />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Learn' }), {
      key: 'Enter',
    });
    fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
    fireEvent.click(
      screen.getByRole('radio', { name: 'Learn CAD fundamentals' }),
    );
    fireEvent.click(screen.getByRole('button', { name: /^Review/ }));
    expect(
      screen.getByRole('heading', { name: 'Sketch to solid' }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Begin lesson' }));
    expect(
      screen.queryByRole('button', { name: /Check my step/ }),
    ).not.toBeInTheDocument();
  });
});
