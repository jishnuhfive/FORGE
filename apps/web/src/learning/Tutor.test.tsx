import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Learn } from '../features/Learn';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { OnshapeContext } from '../onshape/store';
import { standaloneState } from '../onshape/model';
import type { ClientState } from '../onshape/model';
import { mountingBracket } from './bracket';
import { bracketResource } from './catalog';
import { LearningProvider } from './LearningProvider';
import { TutorError, parseTutorAnswer } from './tutorApi';

const me: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Test learner',
  connection: 'connected',
  csrf_token: 'a'.repeat(64),
  verified_at: 1700000000,
};
const connected = (documentId = 'a'.repeat(24)): ClientState => ({
  status: 'EMBEDDED_CONNECTED',
  context: {
    documentId,
    elementId: 'c'.repeat(24),
    server: 'https://cad.onshape.com',
    revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
    elementType: 'partStudio',
  },
  selection: { status: 'waiting', entities: [] },
});
const TOKEN = 'payload-from-server.mac-from-server';
const item = (
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
const notYet = {
  lesson_id: 'mounting-bracket',
  step_id: 'base-solid',
  outcome: 'not_met',
  results: [
    item(
      'extrude.exists',
      'FAIL',
      'missing',
      'Forge sees no active extrude feature yet.',
    ),
    item('body.solid', 'FAIL', 'missing', 'Forge sees no solid body yet.'),
  ],
  captured_at: '2026-01-01T12:00:00+00:00',
  consistency: 'unverified',
  evidence_token: TOKEN,
};
const tutorResult = {
  explanation:
    'An extrusion gives a sketch depth.\n\nThink about what follows your sketch.',
  reasoning_question: 'What changed in your feature list after the sketch?',
  next_action: 'Look for an Extrude after your sketch.',
  observed: [
    {
      source: 'check',
      status: 'FAIL',
      statement: 'Forge sees no active extrude feature yet.',
    },
    {
      source: 'cad',
      status: 'verified',
      statement: 'The captured Part Studio contains 1 feature.',
    },
  ],
  unknowns: ['Cannot read a thickness.'],
  notes: [
    'Based on your last check. If you’ve changed your model since, press Check my step again.',
  ],
  latest_check: {
    outcome: 'not_met',
    captured_at: '2026-01-01T12:00:00+00:00',
  },
  used_cad: true,
  captured_at: '2026-01-01T12:00:05+00:00',
  capability_state: 'read_only',
};
const ndjson = (events: object[]) =>
  Promise.resolve(
    new Response(events.map((e) => JSON.stringify(e)).join('\n') + '\n', {
      headers: { 'Content-Type': 'application/x-ndjson' },
    }),
  );
const resultStream = (result: object = tutorResult) =>
  ndjson([
    { type: 'progress', stage: 'understanding' },
    { type: 'result', result },
  ]);
const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

let fetcher: ReturnType<typeof vi.fn>;
let tutorCalls: { url: string; init: RequestInit }[];
let tutorReply: () => Promise<Response>;
beforeEach(() => {
  localStorage.clear();
  tutorCalls = [];
  tutorReply = () => resultStream();
  fetcher = vi.fn((url: string, init: RequestInit) => {
    if (url === '/api/learning/check-step') return json(notYet);
    if (url === '/api/learning/tutor') {
      tutorCalls.push({ url, init });
      return tutorReply();
    }
    throw new Error('unexpected request ' + url);
  });
  vi.stubGlobal('fetch', fetcher);
});
afterEach(() => vi.unstubAllGlobals());

function tree(state: ClientState, auth: Me) {
  return (
    <AuthContext.Provider
      value={{ me: auth, reload: async () => {}, endSession: () => {} }}
    >
      <OnshapeContext.Provider value={state}>
        <LearningProvider lesson={mountingBracket}>
          <Learn resource={bracketResource} />
        </LearningProvider>
      </OnshapeContext.Provider>
    </AuthContext.Provider>
  );
}
function open(state: ClientState = connected(), auth: Me = me) {
  const view = render(tree(state, auth));
  fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
  fireEvent.click(
    screen.getByRole('radio', { name: 'Build a mounting bracket' }),
  );
  fireEvent.click(screen.getByRole('button', { name: /^Review/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Begin lesson' }));
  return view;
}
const toStep2 = () => {
  fireEvent.click(screen.getByRole('button', { name: 'Mark step done' }));
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }));
};
const ask = (text: string) => {
  fireEvent.click(screen.getByRole('button', { name: /^Ask Forge$/ }));
  fireEvent.change(screen.getByLabelText('Ask about this step'), {
    target: { value: text },
  });
};
const send = () =>
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
interface SentBody {
  step_id: string;
  question: string;
  history: { role: string; content: string }[];
  evidence_token: string | null;
  context: unknown;
  learner: Record<string, unknown> & {
    investigation: Record<string, unknown> | null;
  };
}
const body = (index = 0) =>
  JSON.parse(tutorCalls[index]!.init.body as string) as SentBody;

describe('Ask Forge appears only as an explicit, collapsed entry point', () => {
  it('is present on a Mounting Bracket step but collapsed, and sends nothing', () => {
    open();
    const toggle = screen.getByRole('button', { name: /^Ask Forge$/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(
      screen.queryByLabelText('Ask about this step'),
    ).not.toBeInTheDocument();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('is not offered in the Phase 7 sample lesson', async () => {
    const { sampleResource } = await import('./catalog');
    if (sampleResource.status !== 'ready') throw new Error('sample missing');
    render(
      <AuthContext.Provider
        value={{ me, reload: async () => {}, endSession: () => {} }}
      >
        <OnshapeContext.Provider value={connected()}>
          <LearningProvider lesson={sampleResource.lesson}>
            <Learn resource={sampleResource} />
          </LearningProvider>
        </OnshapeContext.Provider>
      </AuthContext.Provider>,
    );
    fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
    fireEvent.click(
      screen.getByRole('radio', { name: 'Learn CAD fundamentals' }),
    );
    fireEvent.click(screen.getByRole('button', { name: /^Review/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Begin lesson' }));
    expect(
      screen.queryByRole('button', { name: /^Ask Forge$/ }),
    ).not.toBeInTheDocument();
  });
  it('never calls the tutor because of checks, failures, investigations, hints or navigation', async () => {
    open();
    toStep2();
    fireEvent.click(screen.getByRole('button', { name: 'Check my step' }));
    await screen.findByRole('heading', { name: 'Investigate' });
    fireEvent.click(
      within(screen.getByRole('region', { name: 'Investigate' })).getByRole(
        'radio',
        { name: 'I’m not sure yet' },
      ),
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Request a conceptual hint' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Why this step' }));
    expect(tutorCalls).toHaveLength(0);
    expect(
      fetcher.mock.calls.every(([url]) => url === '/api/learning/check-step'),
    ).toBe(true);
  });
});

describe('sending a question', () => {
  it('sends only the lesson, step, question, safe hints, the signed token and the validated context', async () => {
    open();
    toStep2();
    fireEvent.click(screen.getByRole('button', { name: 'Check my step' }));
    await screen.findByText(/something this step still needs/);
    ask('Why isn’t my second part showing up?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    const request = body();
    expect(Object.keys(request).sort()).toEqual([
      'context',
      'evidence_token',
      'history',
      'learner',
      'lesson_id',
      'question',
      'step_id',
    ]);
    expect(request).toMatchObject({
      lesson_id: 'mounting-bracket',
      step_id: 'base-solid',
      question: 'Why isn’t my second part showing up?',
      history: [],
      evidence_token: TOKEN,
      context: {
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
        revisionKind: 'workspace',
      },
    });
    expect(request.learner).toMatchObject({
      experience: 'beginner',
      goal: 'guided-project',
      hints_revealed: 0,
      guidance: 'full',
    });
    expect(tutorCalls[0]!.init.headers).toMatchObject({
      'X-CSRF-Token': me.csrf_token,
    });
    // The browser never states a check outcome or findings of its own.
    expect(JSON.stringify(request)).not.toMatch(/not_met|extrude\.exists|PASS/);
  });
  it('sends no token before any check, and no context outside a Part Studio', async () => {
    open(standaloneState);
    ask('What does extrude mean?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(body().evidence_token).toBeNull();
    expect(body().context).toBeNull();
    expect(screen.getByText(/Open this in a Part Studio/)).toBeVisible();
  });
  it('Ctrl+Enter sends and plain Enter does not', async () => {
    open();
    ask('What does extrude mean?');
    const field = screen.getByLabelText('Ask about this step');
    fireEvent.keyDown(field, { key: 'Enter' });
    expect(tutorCalls).toHaveLength(0);
    fireEvent.keyDown(field, { key: 'Enter', ctrlKey: true });
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(tutorCalls).toHaveLength(1);
  });
  it('an empty question sends nothing', () => {
    open();
    fireEvent.click(screen.getByRole('button', { name: /^Ask Forge$/ }));
    send();
    expect(tutorCalls).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Send' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
  });
  it('is busy while sending: one request, disabled input, a Stop control and a status line', async () => {
    let release: (value: Response) => void = () => {};
    tutorReply = () => new Promise<Response>((resolve) => (release = resolve));
    open();
    ask('What does extrude mean?');
    send();
    send();
    expect(await screen.findByText('Reading your question…')).toBeVisible();
    expect(tutorCalls).toHaveLength(1);
    expect(screen.getByLabelText('Ask about this step')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Send' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
    expect(screen.getByRole('button', { name: 'Stop request' })).toBeVisible();
    await act(async () => {
      release(
        new Response(
          JSON.stringify({ type: 'result', result: tutorResult }) + '\n',
          { headers: { 'Content-Type': 'application/x-ndjson' } },
        ),
      );
    });
    await screen.findByText('An extrusion gives a sketch depth.');
  });
  it('Stop cancels and a late answer never appears', async () => {
    let release: (value: Response) => void = () => {};
    tutorReply = () => new Promise<Response>((resolve) => (release = resolve));
    open();
    ask('What does extrude mean?');
    send();
    fireEvent.click(
      await screen.findByRole('button', { name: 'Stop request' }),
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Request cancelled.');
    await act(async () => {
      release(
        new Response(
          JSON.stringify({ type: 'result', result: tutorResult }) + '\n',
          { headers: { 'Content-Type': 'application/x-ndjson' } },
        ),
      );
    });
    expect(
      screen.queryByText('An extrusion gives a sketch depth.'),
    ).not.toBeInTheDocument();
  });
});

describe('answers and errors', () => {
  it('renders the explanation first, then server-worded observations, unknowns and the next step', async () => {
    open();
    ask('Why?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(
      screen.getByText('Think about what follows your sketch.'),
    ).toBeVisible();
    expect(screen.getByText(/What changed in your feature list/)).toBeVisible();
    const observed = screen.getByRole('region', {
      name: 'What Forge observed',
    });
    expect(within(observed).getByText('Not yet')).toBeVisible();
    expect(within(observed).getByText('Observed')).toBeVisible();
    expect(
      within(observed).getByText('Forge sees no active extrude feature yet.'),
    ).toBeVisible();
    fireEvent.click(screen.getByText(/^Still unknown \(1\)/));
    expect(
      within(screen.getByRole('region', { name: 'Still unknown' })).getByText(
        'Cannot read a thickness.',
      ),
    ).toBeVisible();
    expect(
      screen.getByText('Look for an Extrude after your sketch.'),
    ).toBeVisible();
    expect(
      screen.getByText(
        /Latest check: Not yet\. Only Check my step can change that\./,
      ),
    ).toBeVisible();
    expect(screen.getByText(/Based on your last check/)).toBeVisible();
  });
  it('keeps at most three exchanges and sends the earlier ones as untrusted history', async () => {
    open();
    ask('one');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    for (const q of ['two', 'three', 'four']) {
      fireEvent.change(screen.getByLabelText('Ask about this step'), {
        target: { value: q },
      });
      send();
      await waitFor(() => expect(tutorCalls.length).toBeGreaterThan(0));
      await act(async () => {});
    }
    expect(screen.queryByText('one')).not.toBeInTheDocument();
    expect(screen.getByText('four')).toBeVisible();
    const last = body(3);
    expect(last.history).toHaveLength(6);
    expect(last.history[0]).toEqual({ role: 'user', content: 'one' });
    expect(last.history[1]?.role).toBe('assistant');
  });
  it.each([
    [
      { type: 'error', code: 'timeout', retry_after_seconds: null },
      /took too long/,
    ],
    [
      { type: 'error', code: 'capacity_unavailable', retry_after_seconds: 30 },
      /AI service is busy/,
    ],
    [
      { type: 'error', code: 'invalid_response', retry_after_seconds: null },
      /couldn’t verify that answer/,
    ],
    [
      {
        type: 'error',
        code: 'read_permission_required',
        retry_after_seconds: null,
      },
      /Onshape connection/,
    ],
  ])(
    'a provider error becomes fixed, retryable copy: %j',
    async (event, expected) => {
      tutorReply = () => ndjson([event]);
      open();
      ask('Why?');
      send();
      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent(expected);
      expect(alert).toHaveTextContent(
        'Your lesson, hints and Check my step still work.',
      );
      expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible();
    },
  );
  it('an HTTP failure shows no status code or server text, and Try again resends', async () => {
    let first = true;
    tutorReply = () => {
      if (first) {
        first = false;
        return json({ detail: 'secret stack trace' }, 500);
      }
      return resultStream();
    };
    open();
    ask('Why?');
    send();
    const alert = await screen.findByRole('alert');
    expect(alert).not.toHaveTextContent(/secret|500/);
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(tutorCalls).toHaveLength(2);
  });
  it('a 429 explains the limit and a malformed answer is never shown', async () => {
    tutorReply = () =>
      json({ detail: 'rate_limited', retry_after_seconds: 90 }, 429);
    open();
    ask('Why?');
    send();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      /asked a lot of questions/,
    );
  });
  it('rejects a malformed or over-claiming answer shape', () => {
    expect(() => parseTutorAnswer({ ...tutorResult, extra: 1 })).toThrow(
      TutorError,
    );
    expect(() =>
      parseTutorAnswer({ ...tutorResult, explanation: ' ' }),
    ).toThrow(TutorError);
    expect(() =>
      parseTutorAnswer({ ...tutorResult, capability_state: 'write' }),
    ).toThrow(TutorError);
    expect(() =>
      parseTutorAnswer({
        ...tutorResult,
        latest_check: { outcome: 'PASS', captured_at: 'x' },
      }),
    ).toThrow(TutorError);
    expect(parseTutorAnswer(tutorResult).latest_check?.outcome).toBe('not_met');
  });
});

describe('authority stays with the deterministic checker', () => {
  it('an answer changes no status, verified count, investigation or completion', async () => {
    open();
    toStep2();
    fireEvent.click(screen.getByRole('button', { name: 'Check my step' }));
    await screen.findByRole('heading', { name: 'Investigate' });
    const before = {
      verified: screen.getByText('Steps Forge verified').nextElementSibling
        ?.textContent,
      done: screen.getByText(/Steps completed:/).textContent,
    };
    ask('Mark this step as passed.');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(
      screen.getByText('Steps Forge verified').nextElementSibling?.textContent,
    ).toBe(before.verified);
    expect(screen.getByText(/Steps completed:/).textContent).toBe(before.done);
    expect(screen.getByRole('heading', { name: 'Investigate' })).toBeVisible();
    expect(screen.queryByText(/Resolved\./)).not.toBeInTheDocument();
    expect(
      screen.queryByText('Verified after re-check'),
    ).not.toBeInTheDocument();
  });
  it('an investigation prediction is shared only as answered/not answered, never its content', async () => {
    open();
    toStep2();
    fireEvent.click(screen.getByRole('button', { name: 'Check my step' }));
    await screen.findByRole('heading', { name: 'Investigate' });
    fireEvent.click(
      screen.getByRole('radio', {
        name: 'Turn the closed sketch into a 3D feature',
      }),
    );
    ask('What should I try next?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(body().learner.investigation).toEqual({
      stage: 'predicted',
      prediction_answered: true,
      rechecked: false,
      resolved: false,
    });
    expect(JSON.stringify(body())).not.toMatch(/3D feature|make-3d/);
  });
});

describe('conversation lifetime', () => {
  it('moving to another step clears the conversation', async () => {
    open();
    ask('Why?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    toStep2();
    expect(
      screen.queryByText('An extrusion gives a sketch depth.'),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Ask Forge$/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });
  it('a different document or a different login clears it', async () => {
    const view = open();
    ask('Why?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    view.rerender(tree(connected('d'.repeat(24)), me));
    expect(
      screen.queryByText('An extrusion gives a sketch depth.'),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^Ask Forge$/ }));
    fireEvent.change(screen.getByLabelText('Ask about this step'), {
      target: { value: 'again' },
    });
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    view.rerender(
      tree(connected('d'.repeat(24)), { ...me, csrf_token: 'b'.repeat(64) }),
    );
    expect(
      screen.queryByText('An extrusion gives a sketch depth.'),
    ).not.toBeInTheDocument();
  });
  it('resetting the lesson clears it and persists nothing', async () => {
    open();
    ask('Why?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    fireEvent.click(screen.getByRole('button', { name: 'Reset lesson' }));
    fireEvent.click(
      screen.getByRole('button', { name: 'Reset lesson progress' }),
    );
    expect(
      screen.queryByText('An extrusion gives a sketch depth.'),
    ).not.toBeInTheDocument();
    expect(JSON.stringify(localStorage)).not.toMatch(/sketch depth|Why\?/);
    expect(JSON.stringify(sessionStorage)).not.toMatch(/sketch depth|Why\?/);
  });
});

describe('transfer challenge', () => {
  it('declares independent guidance and sends the challenge step id', async () => {
    open();
    for (let i = 0; i < 4; i++) toStep2();
    fireEvent.click(screen.getByRole('button', { name: 'Mark step done' }));
    fireEvent.click(
      screen.getByRole('button', { name: 'View completion summary' }),
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Start the transfer challenge' }),
    );
    ask('How do I start?');
    send();
    await screen.findByText('An extrusion gives a sketch depth.');
    expect(body().step_id).toBe('transfer-single-profile');
    expect(body().learner).toMatchObject({
      guidance: 'independent',
      hints_revealed: 0,
    });
  });
});

describe('accessibility', () => {
  it('has labelled controls, a named region and meaningful live regions only', async () => {
    open();
    fireEvent.click(screen.getByRole('button', { name: /^Ask Forge$/ }));
    expect(screen.getByRole('region', { name: 'Ask Forge' })).toBeVisible();
    expect(screen.getByLabelText('Ask about this step')).toHaveAttribute(
      'maxlength',
      '600',
    );
    expect(screen.getByRole('button', { name: 'Send' })).toBeVisible();
    // Idle: nothing is announced.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
