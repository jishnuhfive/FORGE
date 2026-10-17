import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Learn } from '../features/Learn';
import { Workspace } from '../App';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { sketchToSolid } from './sample';

function choose() {
  fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
  fireEvent.click(
    screen.getByRole('radio', { name: 'Learn CAD fundamentals' }),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Review sample lesson' }));
}
function start() {
  choose();
  fireEvent.click(screen.getByRole('button', { name: 'Begin lesson' }));
}
function done() {
  fireEvent.click(screen.getByRole('button', { name: 'Mark step done' }));
}
function mode(name: string) {
  fireEvent.keyDown(screen.getByRole('tab', { name }), { key: 'Enter' });
}
function route(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
}
const authenticated: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Test learner',
  connection: 'connected',
  csrf_token: 'a'.repeat(64),
  verified_at: 1700000000,
};

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(
    'forge.preferences.v1',
    JSON.stringify({ onboarded: true }),
  );
  window.location.hash = '';
});
describe('learning workspace', () => {
  it('first opens with concise experience choices and no selected profile', () => {
    render(<Learn />);
    expect(
      screen.getByRole('heading', { name: 'Learn with Forge' }),
    ).toBeVisible();
    expect(screen.getAllByRole('radio')).toHaveLength(3);
    expect(
      screen.getByRole('button', { name: 'Review sample lesson' }),
    ).toBeDisabled();
    expect(
      screen.queryByText('What would you like to work toward?'),
    ).not.toBeInTheDocument();
  });
  it('collects experience and goal, then introduces objectives and prerequisites', () => {
    render(<Learn />);
    choose();
    expect(
      screen.getByRole('heading', { name: 'Sketch to solid' }),
    ).toHaveFocus();
    for (const objective of sketchToSolid.learningObjectives)
      expect(screen.getByText(objective)).toBeVisible();
    expect(screen.getByText(/No model is required/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Change setup' }));
    expect(screen.getByRole('radio', { name: /^Beginner/ })).toBeChecked();
    expect(
      screen.getByRole('radio', { name: 'Learn CAD fundamentals' }),
    ).toBeChecked();
  });
  it('uses the experience and goal to frame the same sample honestly', () => {
    render(<Learn />);
    fireEvent.click(screen.getByRole('radio', { name: /^Comfortable/ }));
    fireEvent.click(
      screen.getByRole('radio', { name: 'Complete a guided project' }),
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Review sample lesson' }),
    );
    expect(screen.getByText(/Focus on the reasoning/)).toBeVisible();
    expect(
      screen.getByText(/prepares you for future guided projects/),
    ).toBeVisible();
  });
  it('shows a single active step with How, Why access, help and zero completed progress', () => {
    render(<Learn />);
    start();
    expect(
      screen.getByRole('heading', { name: 'Begin with a profile' }),
    ).toHaveFocus();
    expect(screen.getByRole('heading', { name: 'What to do' })).toBeVisible();
    expect(screen.getByText('Steps completed: 0 of 3')).toBeVisible();
    expect(
      screen.getByRole('progressbar', { name: 'Steps marked done by you' }),
    ).toHaveAttribute('value', '0');
    expect(
      screen.queryByText(sketchToSolid.steps[1]!.instruction),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Forge isn’t checking the model/)).toBeVisible();
    expect(
      screen.queryByRole('button', { name: /Check my/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/PASS|FAIL|WARNING|UNVERIFIED|mastery|grade:/),
    ).not.toBeInTheDocument();
  });
  it('opens Why and vocabulary contextually without leaving the step or moving focus', () => {
    render(<Learn />);
    start();
    const why = screen.getByRole('button', { name: 'Why this step' });
    why.focus();
    fireEvent.click(why);
    expect(why).toHaveAttribute('aria-expanded', 'true');
    expect(why).toHaveFocus();
    expect(screen.getByText(sketchToSolid.steps[0]!.why)).toBeVisible();
    fireEvent.click(why);
    expect(
      screen.queryByText(sketchToSolid.steps[0]!.why),
    ).not.toBeInTheDocument();
    const term = screen.getByRole('button', { name: 'Sketch' });
    for (let i = 0; i < 3; i++) fireEvent.click(term);
    expect(term).toHaveAttribute('aria-expanded', 'true');
    expect(
      screen.getByText('A 2D profile used as the basis for many 3D features.'),
    ).toBeVisible();
    expect(
      screen.getByText('Vocabulary terms opened').nextElementSibling,
    ).toHaveTextContent('1');
  });
  it('reveals precisely one hint level per deliberate request with neutral counters', () => {
    render(<Learn />);
    start();
    expect(
      screen.queryByRole('heading', { name: 'Conceptual hint' }),
    ).not.toBeInTheDocument();
    const hint = screen.getByRole('button', {
      name: 'Request a conceptual hint',
    });
    hint.focus();
    fireEvent.click(hint);
    expect(
      screen.getByRole('heading', { name: 'Conceptual hint' }),
    ).toBeVisible();
    expect(hint).toHaveFocus();
    fireEvent.click(
      screen.getByRole('button', { name: 'More help: tool-specific hint' }),
    );
    expect(
      screen.getByRole('heading', { name: 'Tool-specific hint' }),
    ).toBeVisible();
    expect(
      screen.queryByRole('heading', { name: 'Conceptual hint' }),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: 'Request full explanation' }),
    );
    expect(
      screen.getByRole('heading', { name: 'Full explanation' }),
    ).toBeVisible();
    expect(
      screen.queryByRole('heading', { name: 'Tool-specific hint' }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText('Hints requested').nextElementSibling,
    ).toHaveTextContent('3');
  });
  it('marks self-reported completion before advancing and completes the whole lesson', () => {
    render(<Learn />);
    start();
    done();
    expect(screen.getByRole('status')).toHaveTextContent(
      'Step marked done by you.',
    );
    expect(screen.getByText('Steps completed: 1 of 3')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Next step' }));
    expect(
      screen.getByRole('heading', { name: 'Turn the profile into depth' }),
    ).toHaveFocus();
    done();
    fireEvent.click(screen.getByRole('button', { name: 'Next step' }));
    done();
    fireEvent.click(
      screen.getByRole('button', { name: 'View completion summary' }),
    );
    expect(
      screen.getByRole('heading', { name: 'Lesson complete' }),
    ).toHaveFocus();
    expect(screen.getByText('Steps completed: 3 of 3')).toBeVisible();
    expect(
      screen.getByText('Steps completed without hints').nextElementSibling,
    ).toHaveTextContent('3');
    expect(
      screen.getByText(/did not inspect or check your CAD model/),
    ).toBeVisible();
  });
  it('confirms reset, supports cancellation, then clears all lesson choices and progress', () => {
    render(<Learn />);
    start();
    fireEvent.click(
      screen.getByRole('button', { name: 'Request a conceptual hint' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reset lesson' }));
    const dialog = screen.getByRole('dialog', { name: 'Reset this lesson?' });
    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Keep learning' }),
    );
    expect(
      screen.getByRole('heading', { name: 'Conceptual hint' }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Reset lesson' }));
    fireEvent.click(
      screen.getByRole('button', { name: 'Reset lesson progress' }),
    );
    expect(
      screen.getByRole('heading', { name: 'Learn with Forge' }),
    ).toBeVisible();
    expect(screen.getByRole('radio', { name: /^Beginner/ })).not.toBeChecked();
  });
  for (const status of [
    'empty',
    'unavailable',
    'load-error',
    'invalid',
  ] as const)
    it(`shows a safe ${status} state and a usable recovery`, () => {
      render(<Learn resource={{ status }} />);
      expect(screen.getByRole('alert')).not.toHaveTextContent(
        /stack|schema|trace/i,
      );
      fireEvent.click(
        screen.getByRole('button', { name: 'Open sample lesson' }),
      );
      expect(
        screen.getByRole('heading', { name: 'Learn with Forge' }),
      ).toBeVisible();
    });
});
describe('workspace learning lifecycle and product boundaries', () => {
  it('preserves active step, hints, disclosures and profile across modes, settings, history and rerenders', async () => {
    const view = render(<Workspace />);
    mode('Learn');
    start();
    fireEvent.click(
      screen.getByRole('button', { name: 'Request a conceptual hint' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Why this step' }));
    done();
    fireEvent.click(screen.getByRole('button', { name: 'Next step' }));
    mode('Design');
    mode('Modify');
    mode('Learn');
    view.rerender(<Workspace />);
    route('/settings');
    route('/history');
    route('/');
    expect(
      await screen.findByRole('heading', {
        name: 'Turn the profile into depth',
      }),
    ).toBeVisible();
    expect(
      screen.getByText('Hints requested').nextElementSibling,
    ).toHaveTextContent('1');
    expect(screen.getByText('Steps completed: 1 of 3')).toBeVisible();
  });
  it('makes no network calls, writes no learning storage and starts fresh after panel destruction', () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    const storageBefore = localStorage.getItem('forge.preferences.v1');
    const view = render(<Workspace />);
    mode('Learn');
    start();
    fireEvent.click(
      screen.getByRole('button', { name: 'Request a conceptual hint' }),
    );
    done();
    mode('Design');
    mode('Learn');
    expect(fetch).not.toHaveBeenCalled();
    expect(localStorage.getItem('forge.preferences.v1')).toBe(storageBefore);
    expect(localStorage.length).toBe(1);
    expect(sessionStorage.length).toBe(0);
    view.unmount();
    render(<Workspace />);
    mode('Learn');
    expect(
      screen.getByRole('heading', { name: 'Learn with Forge' }),
    ).toBeVisible();
  });
  for (const change of ['rotation', 'disconnect'] as const)
    it(`clears learning on genuine ${change} while unchanged status refresh preserves it`, () => {
      const reload = vi.fn();
      const endSession = vi.fn();
      const tree = (me: Me) => (
        <AuthContext.Provider value={{ me, reload, endSession }}>
          <Workspace />
        </AuthContext.Provider>
      );
      const view = render(tree(authenticated));
      mode('Learn');
      start();
      view.rerender(tree({ ...authenticated, verified_at: 1700000001 }));
      expect(
        screen.getByRole('heading', { name: 'Begin with a profile' }),
      ).toBeVisible();
      view.rerender(
        tree({
          ...authenticated,
          ...(change === 'rotation'
            ? { csrf_token: 'b'.repeat(64) }
            : { connection: 'disconnected' }),
        }),
      );
      mode('Learn');
      expect(
        screen.getByRole('heading', { name: 'Learn with Forge' }),
      ).toBeVisible();
    });
});
