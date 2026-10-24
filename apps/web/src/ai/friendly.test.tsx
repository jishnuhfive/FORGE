import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AnswerContent } from './Analysis';
import { contextualLimits, friendlyAnswer, technicalLimits } from './friendly';
import {
  canonicalAnswer,
  capturedFeatures,
  fullLimits,
  orderFacts,
  polishCases,
} from './__fixtures__/phase14';

describe('Phase 14 deterministic friendly answers', () => {
  for (const [name, value] of Object.entries(polishCases)) {
    it(`renders ${name} from canonical facts and preserves the entire result`, () => {
      const original = structuredClone(value.result);
      expect(friendlyAnswer(value.result, value.prompt)?.paragraphs).toEqual(
        value.paragraphs,
      );
      render(<AnswerContent result={value.result} prompt={value.prompt} />);
      for (const text of value.paragraphs)
        expect(screen.getByText(text)).toBeVisible();
      expect(
        screen.queryByRole('heading', { name: 'Technical limits' }),
      ).toBeNull();
      fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
      const evidence = screen.getByRole('list', { name: 'Evidence' });
      expect(within(evidence).getAllByRole('listitem')).toHaveLength(
        value.result.evidence.length,
      );
      for (const item of value.result.evidence)
        expect(within(evidence).getByText(item.statement)).toBeVisible();
      const details = screen.getByRole('heading', {
        name: 'Technical limits',
      }).parentElement!;
      expect(
        within(details)
          .getAllByRole('listitem')
          .map((item) => item.textContent),
      ).toEqual(fullLimits);
      expect(
        screen.getByRole('heading', { name: 'Full answer' }).nextElementSibling
          ?.textContent,
      ).toBe(value.result.answer);
      expect(
        screen.getByText(/Evidence captured/).querySelector('time'),
      ).toHaveAttribute('dateTime', value.result.captured_at);
      expect(value.result).toEqual(original);
    });
  }

  it('shows the complete inventory in order without inventing dependencies', () => {
    const { result, prompt } = polishCases.inventory;
    expect(friendlyAnswer(result, prompt)?.sequence).toEqual([
      'Sketch Gate',
      'Extrude 1',
      'Fillet 1',
    ]);
    expect(contextualLimits(result, prompt)).toEqual([
      'Feature order does not prove dependency.',
    ]);
    expect(contextualLimits(result, prompt)).not.toContain(
      technicalLimits.units,
    );
  });

  it('reports suppression without converting it into activity or engineering validity', () => {
    const result = canonicalAnswer([
      {
        ...capturedFeatures[2]!,
        statement: capturedFeatures[2]!.statement.replace(
          'active',
          'suppressed',
        ),
      },
    ]);
    expect(
      friendlyAnswer(result, polishCases.state.prompt)?.paragraphs,
    ).toEqual(['Fillet 1 is suppressed.']);
  });

  it('does not infer a terminal from a last visible feature', () => {
    expect(
      friendlyAnswer(polishCases.inventory.result, polishCases.terminal.prompt),
    ).toBeNull();
  });

  it('accepts the exact existing server overview for a legitimate empty model', () => {
    const result = {
      ...polishCases.empty.result,
      answer:
        'This Part Studio contains 0 captured features.\n\n0 parts are reported. 0 bodies are reported.',
    };
    expect(
      friendlyAnswer(result, 'What is in this model?')?.paragraphs,
    ).toEqual(['This Part Studio has no modeled features.']);
  });

  it('falls back for conflicting selection statuses or a different selected kind', () => {
    const result = structuredClone(polishCases.selection.result);
    result.evidence.find((item) => item.id === 'selection_body')!.status =
      'verified';
    expect(friendlyAnswer(result, polishCases.selection.prompt)).toBeNull();
    expect(
      friendlyAnswer(
        polishCases.selection.result,
        'What feature owns this edge?',
      ),
    ).toBeNull();
  });

  it('does not manufacture dependency limits or order evidence from absence', () => {
    const result = { ...polishCases.dependency.result, uncertainties: [] };
    expect(friendlyAnswer(result, polishCases.dependency.prompt)).toBeNull();
    expect(contextualLimits(result, polishCases.dependency.prompt)).toEqual([]);
  });

  it('does not map a different prompt target onto a named state or relationship', () => {
    expect(
      friendlyAnswer(polishCases.state.result, 'Is Extrude 1 active?'),
    ).toBeNull();
    expect(
      friendlyAnswer(
        polishCases.dependency.result,
        'Does Fillet 1 depend on Sketch Gate?',
      ),
    ).toBeNull();
  });

  for (const issue of [
    'duplicate_id',
    'duplicate_names',
    'wrong_status',
    'wrong_index',
    'malformed',
    'qualified_answer',
    'model_prose',
    'conflicting_order',
    'conflicting_count',
  ] as const) {
    it(`falls back without guessing when evidence has ${issue}`, () => {
      let result = structuredClone(polishCases.inventory.result);
      if (issue === 'duplicate_id') result.evidence.push(result.evidence[0]!);
      if (issue === 'duplicate_names')
        result.evidence.find((item) => item.id === 'feature_1')!.statement =
          capturedFeatures[0]!.statement.replace('Sketch Gate', 'Fillet 1');
      if (issue === 'wrong_status')
        result.evidence.find((item) => item.id === 'feature_3')!.status =
          'unknown';
      if (issue === 'wrong_index')
        result.evidence.find((item) => item.id === 'feature_3')!.id =
          'feature_2';
      if (issue === 'malformed')
        result.evidence.find((item) => item.id === 'feature_3')!.statement +=
          ' It owns the selected face.';
      if (issue === 'conflicting_order')
        result.evidence.push({
          ...orderFacts[0]!,
          statement: orderFacts[0]!.statement.replace(
            'Sketch Gate',
            'Different sketch',
          ),
        });
      if (issue === 'conflicting_count')
        result.evidence.find((item) => item.id === 'features')!.statement =
          'The captured Part Studio contains 0 features.';
      result = canonicalAnswer(result.evidence);
      if (issue === 'qualified_answer')
        result.answer += '\n\nThis inventory is disputed.';
      if (issue === 'model_prose')
        result.answer =
          'This design is safe and every feature depends on the sketch.';
      expect(friendlyAnswer(result, polishCases.inventory.prompt)).toBeNull();
      render(
        <AnswerContent result={result} prompt={polishCases.inventory.prompt} />,
      );
      expect(document.querySelector('.answer-text')?.textContent).toBe(
        result.answer.replace(/\n\n/g, ''),
      );
    });
  }

  it('never joins duplicate names to a selected face, state or terminal', () => {
    const duplicate = {
      ...capturedFeatures[0]!,
      statement: capturedFeatures[0]!.statement.replace(
        'Sketch Gate',
        'Fillet 1',
      ),
    };
    for (const key of ['state', 'terminal', 'selection'] as const) {
      const result = structuredClone(polishCases[key].result);
      result.evidence.push(duplicate, capturedFeatures[2]!);
      expect(friendlyAnswer(result, polishCases[key].prompt)).toBeNull();
    }
  });

  it('keeps malicious quoted names as text, including in friendly output', () => {
    const name = '<img src=x onerror=alert(1)>';
    const result = canonicalAnswer([
      {
        ...capturedFeatures[2]!,
        statement: `The third captured feature is named ${JSON.stringify(name)} (fillet; active).`,
      },
    ]);
    render(<AnswerContent result={result} prompt={`Is ${name} active?`} />);
    expect(screen.getByText(`${name} is active.`)).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
  });

  it('keeps empty inventory simple and retains optional guidance only in details', () => {
    render(<AnswerContent {...polishCases.empty} />);
    expect(
      screen.getByText('This Part Studio has no modeled features.'),
    ).toBeVisible();
    expect(screen.queryByText(/0 entries omitted/)).toBeNull();
    expect(screen.queryByText(/Compare proposed dimensions/)).toBeNull();
    expect(screen.queryByText(/static loading/)).toBeNull();
    expect(screen.queryByText(/loads and clearances/)).toBeNull();
    expect(screen.queryByRole('region', { name: 'Limits' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(screen.getByText(/Compare proposed dimensions/)).toBeVisible();
    expect(screen.getByText(/static loading/)).toBeVisible();
    expect(screen.getByText(/loads and clearances/)).toBeVisible();
  });
});

describe('Phase 14 contextual limits and disclosure', () => {
  for (const [key, expected] of [
    ['dependency', 'Dependency has not been established.'],
    ['order', 'Feature order does not prove dependency.'],
    ['selection', 'Owning feature is not available from the current evidence.'],
  ] as const) {
    it(`shows only the relevant ${key} limit before expansion`, () => {
      render(<AnswerContent {...polishCases[key]} />);
      const limits = screen.getByRole('region', { name: 'Limits' });
      expect(limits).toHaveTextContent(expected);
      expect(within(limits).getAllByRole('listitem')).toHaveLength(1);
      expect(screen.queryByText(technicalLimits.units)).toBeNull();
      expect(screen.queryByText(technicalLimits.validation)).toBeNull();
    });
  }
  it('does not add generic warnings to a simple state answer', () => {
    render(<AnswerContent {...polishCases.state} />);
    expect(screen.queryByRole('region', { name: 'Limits' })).toBeNull();
    expect(polishCases.state.result.uncertainties).toEqual(fullLimits);
  });
  it('retains engineering validation for safety questions and units for dimensions', () => {
    expect(
      contextualLimits(
        polishCases.state.result,
        'Is this design safe under load?',
      ),
    ).toEqual(['Engineering validation has not been run.']);
    expect(
      contextualLimits(
        polishCases.state.result,
        'What is the width dimension?',
      ),
    ).toEqual([technicalLimits.units]);
  });
  it('keeps new or unrecognized limitations visible', () => {
    const result = {
      ...polishCases.state.result,
      uncertainties: [
        ...fullLimits,
        'Some captured feature details are incomplete.',
      ],
    };
    expect(contextualLimits(result, polishCases.state.prompt)).toEqual([
      'Some captured feature details are incomplete.',
    ]);
  });
  it('omits a blank disclosure but exposes a limits-only response', () => {
    const empty = canonicalAnswer([], {
      answer: 'Hello.',
      uncertainties: [],
      captured_at: null,
    });
    const view = render(<AnswerContent result={empty} />);
    expect(screen.queryByRole('button', { name: 'Evidence' })).toBeNull();
    view.rerender(
      <AnswerContent
        result={{ ...empty, uncertainties: [technicalLimits.validation] }}
        prompt="Is this safe?"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(
      screen.getByRole('heading', { name: 'Technical limits' }),
    ).toBeVisible();
    expect(screen.queryByRole('list', { name: 'Evidence' })).toBeNull();
    expect(document.querySelectorAll('li:empty')).toHaveLength(0);
  });
});
