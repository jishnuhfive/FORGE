import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ErrorState, TooltipProvider } from '@forge/design-system';
import { PromptComposer } from '../components/PromptComposer';
import { EngineeringBrief } from './EngineeringBrief';
import { DesignPlan } from './DesignPlan';
import { AgentProgress } from './AgentProgress';
import { ValidationReport } from './ValidationReport';
import { Modify } from './Modify';
import { Settings } from './Settings';
import { History } from './History';
import { errors } from '../lib/errors';
import {
  sampleBrief,
  sampleHistory,
  sampleSteps,
  sampleValidation,
} from '../preview/data';

const wrapper = TooltipProvider;
describe('Prompt composer', () => {
  it('suggestions populate and focus the input without submitting', () => {
    const submit = vi.fn();
    render(
      <PromptComposer
        label="Prompt"
        placeholder="Describe a mechanism"
        showSuggestions
        onSubmit={submit}
      />,
    );
    expect(screen.getByRole('button', { name: 'Send prompt' })).toBeDisabled();
    fireEvent.click(
      screen.getByRole('button', { name: 'Design a NEMA 17 motor mount.' }),
    );
    expect(screen.getByLabelText('Prompt')).toHaveValue(
      'Design a NEMA 17 motor mount.',
    );
    expect(screen.getByLabelText('Prompt')).toHaveFocus();
    expect(submit).not.toHaveBeenCalled();
  });
  it('allows multiline Enter and trims submissions with Ctrl+Enter', () => {
    const submit = vi.fn();
    render(
      <PromptComposer
        label="Prompt"
        placeholder="Describe"
        onSubmit={submit}
      />,
    );
    fireEvent.change(screen.getByLabelText('Prompt'), {
      target: { value: '  A mount\nwith slots  ' },
    });
    fireEvent.keyDown(screen.getByLabelText('Prompt'), { key: 'Enter' });
    expect(submit).not.toHaveBeenCalled();
    fireEvent.keyDown(screen.getByLabelText('Prompt'), {
      key: 'Enter',
      ctrlKey: true,
    });
    expect(submit).toHaveBeenCalledWith('A mount\nwith slots');
  });
  it('does not submit an input method composition or empty prompt', () => {
    const submit = vi.fn();
    render(
      <PromptComposer
        label="Prompt"
        placeholder="Describe"
        onSubmit={submit}
      />,
    );
    fireEvent.change(screen.getByLabelText('Prompt'), {
      target: { value: ' ' },
    });
    fireEvent.keyDown(screen.getByLabelText('Prompt'), {
      key: 'Enter',
      metaKey: true,
    });
    expect(submit).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('Prompt'), {
      target: { value: 'mount' },
    });
    fireEvent.keyDown(screen.getByLabelText('Prompt'), {
      key: 'Enter',
      ctrlKey: true,
      isComposing: true,
    });
    expect(submit).not.toHaveBeenCalled();
  });
  it('supports disabled and cancellable busy states', () => {
    const cancel = vi.fn();
    const submit = vi.fn();
    const { rerender } = render(
      <PromptComposer
        label="Prompt"
        placeholder="Describe"
        disabled
        onSubmit={submit}
      />,
    );
    expect(screen.getByLabelText('Prompt')).toBeDisabled();
    rerender(
      <PromptComposer
        label="Prompt"
        placeholder="Describe"
        busy
        onCancel={cancel}
        onSubmit={submit}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Stop preview' }));
    expect(cancel).toHaveBeenCalledOnce();
    expect(submit).not.toHaveBeenCalled();
  });
});

describe('Engineering review', () => {
  it('renders all nine brief sections with explicit sources and local editing', () => {
    render(<EngineeringBrief sections={sampleBrief} onContinue={vi.fn()} />);
    for (const section of sampleBrief)
      expect(
        screen.getByRole('heading', { name: section.title }),
      ).toBeVisible();
    expect(screen.getAllByText('Confirmed in sample').length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText('Assumption · review needed')).toHaveLength(2);
    fireEvent.click(screen.getByRole('button', { name: 'Edit locally' }));
    fireEvent.change(screen.getByLabelText('Edit Payload'), {
      target: { value: '0.50 kg' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Done editing' }));
    expect(screen.getByText('0.50 kg')).toBeVisible();
    expect(sampleBrief[3]?.values[0]?.value).toBe('0.30 kg');
  });
  it('presents parts, checks and risks, and forwards explicit preview actions', () => {
    const approve = vi.fn();
    const revise = vi.fn();
    const cancel = vi.fn();
    render(
      <DesignPlan onApprove={approve} onRevise={revise} onCancel={cancel} />,
    );
    expect(screen.getByText('Carriage')).toBeVisible();
    expect(screen.getByText('Travel ≥ 400 mm')).toBeVisible();
    expect(
      screen.getByText(/Strength, dynamics and load safety are unverified/),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: /Approve and Build/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Revise' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(approve).toHaveBeenCalledOnce();
    expect(revise).toHaveBeenCalledOnce();
    expect(cancel).toHaveBeenCalledOnce();
  });
  for (const state of [
    'pending',
    'active',
    'complete',
    'warning',
    'failed',
    'cancelled',
  ] as const) {
    it(`represents ${state} progress without executing a run`, () => {
      render(
        <AgentProgress
          steps={sampleSteps}
          initial={state}
          onReport={vi.fn()}
        />,
      );
      expect(screen.getByLabelText('Preview run state')).toHaveValue(state);
      expect(screen.getAllByText(state.toUpperCase()).length).toBeGreaterThan(
        0,
      );
      expect(screen.getByText('No agent executing')).toBeVisible();
      if (state === 'failed')
        expect(screen.getByRole('alert')).toHaveTextContent(
          'No CAD operation was attempted',
        );
    });
  }
  it('cancels active progress and leaves sample validation separately selectable', () => {
    const report = vi.fn();
    render(<AgentProgress steps={sampleSteps} onReport={report} />);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel preview' }));
    expect(
      screen.getByText('Preview cancelled. No CAD was changed.'),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Open sample report' }));
    expect(report).toHaveBeenCalledOnce();
  });
  it('reports counts and keeps UNVERIFIED distinct from PASS', () => {
    render(<ValidationReport checks={sampleValidation} />);
    expect(screen.getByText('6 Pass')).toBeVisible();
    expect(screen.getByText('1 Warning')).toBeVisible();
    expect(screen.getByText('1 Unverified')).toBeVisible();
    const mass = screen
      .getByRole('heading', { name: 'Mass' })
      .closest('article');
    expect(mass).not.toBeNull();
    if (!mass) return;
    expect(within(mass).getByText('UNVERIFIED')).toBeVisible();
    expect(within(mass).queryByText('PASS')).not.toBeInTheDocument();
    expect(within(mass).getByText('Not available')).toBeVisible();
  });
  it('represents a failed constraint and missing results', () => {
    const { rerender } = render(
      <ValidationReport
        checks={[
          {
            id: 'fail',
            category: 'Dimensions',
            title: 'Travel',
            required: '≥ 400 mm',
            measured: '380 mm',
            status: 'fail',
          },
        ]}
      />,
    );
    expect(screen.getByText('FAIL')).toBeVisible();
    expect(screen.getByText('1 Fail')).toBeVisible();
    rerender(<ValidationReport checks={[]} />);
    expect(screen.getByText('No validation results')).toBeVisible();
  });
});

describe('Modify selections', () => {
  for (const state of ['none', 'edges', 'ambiguous', 'unsupported', 'stale']) {
    it(`blocks a modification for ${state} selection`, () => {
      render(<Modify preview />);
      fireEvent.change(screen.getByLabelText('Preview selection'), {
        target: { value: state },
      });
      expect(screen.getByLabelText('Modification prompt')).toBeDisabled();
      expect(
        screen.queryByRole('button', { name: /Apply/ }),
      ).not.toBeInTheDocument();
    });
  }
  it('accepts only a local sample and discards a proposal when selection changes', () => {
    render(<Modify preview />);
    fireEvent.change(screen.getByLabelText('Preview selection'), {
      target: { value: 'face' },
    });
    fireEvent.change(screen.getByLabelText('Modification prompt'), {
      target: { value: 'Make this 5 mm thicker.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send prompt' }));
    expect(screen.getByText('9 mm · sample')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: /Apply/ }));
    expect(screen.getByRole('status')).toHaveTextContent('No CAD was modified');
    fireEvent.change(screen.getByLabelText('Preview selection'), {
      target: { value: 'stale' },
    });
    expect(screen.queryByText('Modification preview')).not.toBeInTheDocument();
  });
});

describe('Learn and history', () => {
  it('shows all mock history categories with usable tabs', () => {
    render(<History entries={sampleHistory} />, { wrapper });
    expect(
      screen.getByRole('heading', { name: 'Camera Slider' }),
    ).toBeVisible();
    for (const name of [
      'Conversations',
      'Agent runs',
      'CAD operations',
      'Reports',
      'Activity',
    ])
      fireEvent.keyDown(screen.getByRole('tab', { name }), { key: 'Enter' });
    expect(screen.getByText('Requirements reviewed')).toBeVisible();
  });
});

for (const [code, error] of Object.entries(errors)) {
  it(`renders a sanitized ${code} error`, () => {
    render(<ErrorState {...error} />);
    expect(screen.getByRole('alert')).toHaveTextContent(error.title);
    expect(screen.getByRole('alert')).not.toHaveTextContent(/stack|traceback/i);
  });
}
it('saves the manufacturing profile locally with bounded numeric fields', () => {
  const change = vi.fn();
  render(
    <Settings
      preferences={{
        theme: 'system',
        units: 'metric',
        onboarded: true,
        printer: 'FDM printer',
        width: 220,
        depth: 220,
        height: 250,
        materials: 'PETG',
      }}
      onChange={change}
      storageAvailable
    />,
  );
  fireEvent.change(screen.getByLabelText('Bed width (mm)'), {
    target: { value: '250' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Save local profile' }));
  expect(change).toHaveBeenCalledWith(expect.objectContaining({ width: 250 }));
  fireEvent.change(screen.getByLabelText('Bed width (mm)'), {
    target: { value: '-4' },
  });
  fireEvent.submit(
    screen.getByRole('button', { name: 'Save local profile' }).closest('form')!,
  );
  expect(change).toHaveBeenCalledTimes(1);
});
