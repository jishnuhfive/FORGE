import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Learn } from '../features/Learn';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { OnshapeContext } from '../onshape/store';
import type { ClientState } from '../onshape/model';
import { mountingBracket } from './bracket';
import { bracketResource } from './catalog';
import { LearningProvider } from './LearningProvider';

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
const answer = (step: string, outcome: string, results: object[]) => ({
  lesson_id: 'mounting-bracket',
  step_id: step,
  outcome,
  results,
  captured_at: '2026-01-01T12:00:00+00:00',
  consistency: 'unverified',
  evidence_token: 'synthetic-payload.synthetic-mac',
});
const reply = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));
const noExtrusion = answer('base-solid', 'not_met', [
  item(
    'extrude.exists',
    'FAIL',
    'missing',
    'Forge sees no active extrude feature yet.',
  ),
  item('body.solid', 'FAIL', 'missing', 'Forge sees no solid body yet.'),
  item(
    'extrude.depth',
    'UNVERIFIED',
    'not_observable',
    'Cannot read a thickness.',
    false,
  ),
]);
const fixed = answer('base-solid', 'verified', [
  item(
    'extrude.exists',
    'PASS',
    'met',
    'Forge sees an active extrude feature.',
  ),
  item('body.solid', 'PASS', 'met', 'Forge sees a solid body.'),
  item(
    'extrude.depth',
    'UNVERIFIED',
    'not_observable',
    'Cannot read a thickness.',
    false,
  ),
]);
const transferOk = answer('transfer-single-profile', 'verified', [
  item('transfer.sketch', 'PASS', 'met', 'Forge sees an active sketch.'),
  item(
    'transfer.one_extrusion',
    'PASS',
    'met',
    'Forge sees exactly one active extrusion.',
  ),
  item('transfer.solid_body', 'PASS', 'met', 'Forge sees a solid body.'),
  item(
    'transfer.l_profile',
    'PASS',
    'met',
    'Forge sees a body with more faces than a plain block.',
  ),
  item(
    'transfer.dimensions',
    'UNVERIFIED',
    'not_observable',
    'Cannot read dimensions.',
    false,
  ),
]);
const transferTwo = answer('transfer-single-profile', 'not_met', [
  item('transfer.sketch', 'PASS', 'met', 'Forge sees an active sketch.'),
  item(
    'transfer.one_extrusion',
    'FAIL',
    'constraint_not_met',
    'Forge sees 2 active extrusions; this challenge asks for exactly one.',
  ),
]);

let fetcher: ReturnType<typeof vi.fn>;
beforeEach(() => {
  localStorage.clear();
  fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
});
afterEach(() => vi.unstubAllGlobals());

function open() {
  render(
    <AuthContext.Provider
      value={{ me, reload: async () => {}, endSession: () => {} }}
    >
      <OnshapeContext.Provider value={connected}>
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
const done = (last = false) => {
  fireEvent.click(screen.getByRole('button', { name: 'Mark step done' }));
  fireEvent.click(
    screen.getByRole('button', {
      name: last ? 'View completion summary' : 'Next step',
    }),
  );
};
const toStep2 = () => {
  open();
  done();
};
const check = () =>
  screen.getByRole('button', { name: /^Check (my step|again)$/ });

describe('step 2 mistake investigation', () => {
  it('asks what you expect before you try the change, without grading', () => {
    toStep2();
    const group = screen.getByRole('group', {
      name: /what should Forge be able to see afterward/,
    });
    fireEvent.click(
      within(group).getByRole('radio', {
        name: 'An active extrude feature and a solid body',
      }),
    );
    expect(screen.getByText(/That is one possibility/)).toBeVisible();
    expect(
      within(group).getByRole('radio', { name: 'I’m not sure yet' }),
    ).toBeVisible();
    expect(
      screen.queryByText(/Incorrect|Wrong|Try again|Correct!/),
    ).not.toBeInTheDocument();
  });
  it('shows observed evidence first and keeps the explanation hidden', async () => {
    fetcher.mockReturnValue(reply(noExtrusion));
    toStep2();
    fireEvent.click(check());
    expect(
      await screen.findByRole('heading', { name: 'Investigate' }),
    ).toBeVisible();
    expect(
      screen.getByRole('heading', { name: 'What Forge observed' }),
    ).toBeVisible();
    const investigation = screen.getByRole('region', { name: 'Investigate' });
    expect(
      within(investigation).getByText(
        'Forge sees no active extrude feature yet.',
      ),
    ).toBeVisible();
    expect(
      within(investigation).getByRole('group', {
        name: 'What do you think the next feature should do?',
      }),
    ).toBeVisible();
    // Think first: nothing is explained or recommended yet, and no verdict wording.
    expect(screen.queryByText('Possible explanation')).not.toBeInTheDocument();
    expect(screen.queryByText('Try next')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Verified after re-check'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /possible explanation/ }),
    ).not.toBeInTheDocument();
    expect(investigation).not.toHaveTextContent(
      /forgot|definitely|root cause|diagnosis/i,
    );
  });
  it('walks prediction → possibility → try next, labelled honestly, with no extra requests', async () => {
    fetcher.mockReturnValue(reply(noExtrusion));
    toStep2();
    fireEvent.click(check());
    await screen.findByRole('heading', { name: 'Investigate' });
    const panel = screen.getByRole('region', { name: 'Investigate' });
    fireEvent.click(
      within(panel).getByRole('radio', { name: 'I’m not sure yet' }),
    );
    expect(within(panel).getByText(/That’s fine/)).toBeVisible();
    fireEvent.click(
      within(panel).getByRole('button', {
        name: 'Show a possible explanation',
      }),
    );
    expect(
      within(panel).getByText(/One possibility is that the sketch/),
    ).toBeVisible();
    expect(
      within(panel).getByText(
        'This is a possibility, not something Forge has verified.',
      ),
    ).toBeVisible();
    fireEvent.click(
      within(panel).getByRole('button', { name: 'Show what to try next' }),
    );
    expect(
      within(panel).getByRole('heading', { name: 'Try next' }),
    ).toBeVisible();
    expect(
      within(panel).getByText(/suggestion, not a guarantee/),
    ).toBeVisible();
    expect(
      within(panel).getByText(/Forge doesn’t re-check on its own/),
    ).toBeVisible();
    // Answering and revealing never trigger a check or any other request.
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('a re-check that passes resolves it with a fresh Verified result and updates progress', async () => {
    fetcher
      .mockReturnValueOnce(reply(noExtrusion))
      .mockReturnValueOnce(reply(fixed));
    toStep2();
    fireEvent.click(check());
    await screen.findByRole('heading', { name: 'Investigate' });
    fireEvent.click(
      screen.getByRole('radio', {
        name: 'Turn the closed sketch into a 3D feature',
      }),
    );
    fireEvent.click(check());
    const verified = await screen.findByText(
      /Resolved\. Forge sees an active extrude feature\./,
    );
    expect(verified).toBeVisible();
    expect(
      screen.getByRole('heading', { name: 'Verified after re-check' }),
    ).toBeVisible();
    expect(
      screen.getByText('Investigations resolved after re-check')
        .nextElementSibling,
    ).toHaveTextContent('1 of 1');
    expect(
      screen.getByText('Prediction questions answered').nextElementSibling,
    ).toHaveTextContent('1');
    expect(
      screen.getByText('Steps Forge verified').nextElementSibling,
    ).toHaveTextContent('1 of 4');
  });
  it('a re-check that still fails says it is not resolved yet', async () => {
    fetcher.mockImplementation(() => reply(noExtrusion));
    toStep2();
    fireEvent.click(check());
    await screen.findByRole('heading', { name: 'Investigate' });
    fireEvent.click(check());
    expect(await screen.findByText(/Not resolved yet\./)).toBeVisible();
  });
  it('a later failing check revokes a resolved investigation', async () => {
    fetcher
      .mockReturnValueOnce(reply(noExtrusion))
      .mockReturnValueOnce(reply(fixed))
      .mockReturnValueOnce(reply(noExtrusion));
    toStep2();
    fireEvent.click(check());
    await screen.findByRole('heading', { name: 'Investigate' });
    fireEvent.click(check());
    await screen.findByText(/Resolved\./);
    fireEvent.click(check());
    expect(await screen.findByText(/Not resolved yet\./)).toBeVisible();
    expect(
      screen.getByText('Investigations resolved after re-check')
        .nextElementSibling,
    ).toHaveTextContent('0 of 1');
  });
  it('does not open an investigation for a passing step', async () => {
    fetcher.mockReturnValue(reply(fixed));
    toStep2();
    fireEvent.click(check());
    await screen.findByText(/Forge verified what it can read/);
    expect(
      screen.queryByRole('heading', { name: 'Investigate' }),
    ).not.toBeInTheDocument();
  });
  it('a request error never opens or changes an investigation', async () => {
    fetcher.mockReturnValue(reply({ detail: 'x' }, 500));
    toStep2();
    fireEvent.click(check());
    await screen.findByText(/couldn’t read your model right now/);
    expect(
      screen.queryByRole('heading', { name: 'Investigate' }),
    ).not.toBeInTheDocument();
  });
  it('uses the single Phase 7 hint ladder instead of a second one', async () => {
    fetcher.mockReturnValue(reply(noExtrusion));
    toStep2();
    fireEvent.click(check());
    await screen.findByRole('heading', { name: 'Investigate' });
    expect(
      screen.getAllByRole('button', { name: 'Request a conceptual hint' }),
    ).toHaveLength(1);
    expect(screen.queryByText('Conceptual hint')).not.toBeInTheDocument();
  });
});

describe('step 3 fillet ambiguity', () => {
  it('explains the evidence limit instead of claiming anything about the geometry', async () => {
    fetcher.mockReturnValue(
      reply(
        answer('second-portion', 'unverified', [
          item(
            'bracket.second_portion',
            'WARNING',
            'ambiguous_signal',
            'The face count fits a second portion, but fillets or chamfers can also raise it.',
          ),
        ]),
      ),
    );
    open();
    done();
    done();
    fireEvent.click(check());
    const panel = await screen.findByRole('region', { name: 'Investigate' });
    expect(
      within(panel).getByText(/fillets or chamfers can also raise it/),
    ).toBeVisible();
    fireEvent.click(
      within(panel).getByRole('radio', {
        name: 'No, a fillet or chamfer can add faces too',
      }),
    );
    fireEvent.click(
      within(panel).getByRole('button', {
        name: 'Show a possible explanation',
      }),
    );
    expect(
      within(panel).getByText(/cannot separate a second portion/),
    ).toBeVisible();
    expect(panel).not.toHaveTextContent(/not L-shaped|your bracket is wrong/i);
  });
});

describe('transfer challenge', () => {
  const finishGuided = () => {
    open();
    done();
    done();
    done();
    done();
    done(true);
  };
  it('is offered after the guided lesson, optional, with its own progress', () => {
    finishGuided();
    expect(
      screen.getByRole('heading', { name: 'Lesson complete' }),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Start the transfer challenge' }),
    ).toBeVisible();
    expect(
      screen.getByText(/Optional\. It has its own progress/),
    ).toBeVisible();
  });
  it('starts with constraints and conceptual help only, not the walkthrough', () => {
    finishGuided();
    fireEvent.click(
      screen.getByRole('button', { name: 'Start the transfer challenge' }),
    );
    expect(
      screen.getByRole('heading', {
        name: 'Transfer challenge: one profile, one extrusion',
      }),
    ).toBeVisible();
    expect(
      screen.getByText('Use exactly one extrusion to turn it into a solid.'),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Request a conceptual hint' }),
    ).toBeVisible();
    expect(screen.queryByText(/Tool-specific hint/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Full explanation/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Sketch the L with the Line tool/),
    ).not.toBeInTheDocument();
  });
  it('a passing check verifies it, and a summary reports facts without any score', async () => {
    fetcher.mockReturnValue(reply(transferOk));
    finishGuided();
    fireEvent.click(
      screen.getByRole('button', { name: 'Start the transfer challenge' }),
    );
    fireEvent.click(check());
    await screen.findByText(/Forge verified what it can read/);
    expect(
      screen.getByText('Challenge steps Forge verified').nextElementSibling,
    ).toHaveTextContent('1 of 1');
    fireEvent.click(
      screen.getByRole('button', { name: 'Mark challenge done' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Finish challenge' }));
    expect(
      screen.getByText(/using one profile and one extrusion/),
    ).toBeVisible();
    expect(
      screen.getByText('Completed without hints').nextElementSibling,
    ).toHaveTextContent('Yes');
    expect(
      screen.getByText('Full explanation used').nextElementSibling,
    ).toHaveTextContent('No');
    expect(
      screen.getByText(/not a grade or a measure of your skill/),
    ).toBeVisible();
    expect(document.body).not.toHaveTextContent(
      /mastery|proficien|score|rank|streak|safe to print/i,
    );
  });
  it('an extra extrusion opens an independent investigation and a fix resolves it', async () => {
    fetcher
      .mockReturnValueOnce(reply(transferTwo))
      .mockReturnValueOnce(reply(transferOk));
    finishGuided();
    fireEvent.click(
      screen.getByRole('button', { name: 'Start the transfer challenge' }),
    );
    fireEvent.click(check());
    const panel = await screen.findByRole('region', { name: 'Investigate' });
    expect(within(panel).getByText(/Independent challenge/)).toBeVisible();
    expect(within(panel).getByText(/asks for exactly one/)).toBeVisible();
    fireEvent.click(check());
    expect(await screen.findByText(/Resolved\./)).toBeVisible();
  });
  it('restarting the challenge needs confirmation and keeps guided progress', async () => {
    fetcher.mockReturnValue(reply(transferOk));
    finishGuided();
    fireEvent.click(
      screen.getByRole('button', { name: 'Start the transfer challenge' }),
    );
    fireEvent.click(check());
    await screen.findByText(/Forge verified what it can read/);
    fireEvent.click(screen.getByRole('button', { name: 'Restart challenge' }));
    expect(screen.getByText(/Your guided lesson progress stays/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Keep going' }));
    expect(
      screen.getByText('Challenge steps Forge verified').nextElementSibling,
    ).toHaveTextContent('1 of 1');
    fireEvent.click(screen.getByRole('button', { name: 'Restart challenge' }));
    fireEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', {
        name: 'Restart challenge',
      }),
    );
    expect(
      await screen.findByText('Challenge steps Forge verified'),
    ).toBeVisible();
    expect(
      screen.getByText('Challenge steps Forge verified').nextElementSibling,
    ).toHaveTextContent('0 of 1');
  });
  it('the Reset lesson dialog says it clears the challenge and predictions too', () => {
    finishGuided();
    fireEvent.click(screen.getByRole('button', { name: 'Reset lesson' }));
    expect(
      screen.getByText(/predictions, investigations, challenge progress/),
    ).toBeVisible();
  });
});
