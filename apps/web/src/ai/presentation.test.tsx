import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AnswerContent } from './Analysis';
import { modelSummary } from './presentation';
import {
  syntheticOverview,
  syntheticSelectionAnswer,
} from './__fixtures__/response';

describe('grounded display summary', () => {
  it('formats canonical evidence without turning missing topology into zero', () => {
    const summary = modelSummary(syntheticOverview)!;
    expect(summary.features).toEqual(['Sketch 1', 'Extrude 1']);
    expect(summary.counts).toContainEqual({
      value: '6',
      label: 'returned faces',
    });
    expect(summary.unknowns).toEqual(['Edges unknown', 'Vertices unknown']);
    expect(
      summary.counts.some(
        (item) => item.label.includes('edge') || item.label.includes('vert'),
      ),
    ).toBe(false);
    expect(summary.mass).toContain('may be missing');
  });
  for (const change of [
    'unknown',
    'duplicate',
    'malformed',
    'specific',
    'suppressed',
    'missing_body',
    'qualified_inventory',
  ] as const) {
    it(`keeps prose for ${change} evidence instead of guessing a summary`, () => {
      const result = structuredClone(syntheticOverview);
      if (change === 'unknown')
        result.evidence.find((item) => item.id === 'parts')!.status = 'unknown';
      if (change === 'duplicate') result.evidence.push(result.evidence[0]!);
      if (change === 'malformed')
        result.evidence.find((item) => item.id === 'parts')!.statement =
          'The captured Part Studio contains unknown parts.';
      if (change === 'specific')
        result.answer = 'The width-driving dimension is unknown.';
      if (change === 'suppressed')
        result.evidence.find((item) => item.id === 'feature_2')!.statement =
          result.evidence
            .find((item) => item.id === 'feature_2')!
            .statement.replace('active', 'suppressed');
      if (change === 'missing_body')
        result.evidence = result.evidence.filter(
          (item) => item.id !== 'body_1',
        );
      if (change === 'qualified_inventory')
        result.answer = result.answer.replace(
          '1 solid part is reported',
          'The material is unverified. 1 solid part is reported',
        );
      expect(modelSummary(result)).toBeNull();
    });
  }
  it('does not infer selection ownership from singleton inventory', () => {
    const result = syntheticSelectionAnswer('FACE');
    result.evidence.push(...syntheticOverview.evidence);
    expect(modelSummary(result)).toBeNull();
  });
  it('retains the exact full answer and all evidence on demand', () => {
    render(<AnswerContent result={syntheticOverview} />);
    expect(
      screen.getByRole('heading', { name: 'Current model' }),
    ).toBeVisible();
    expect(screen.queryByText(syntheticOverview.answer)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(screen.getByRole('heading', { name: 'Full answer' })).toBeVisible();
    expect(document.querySelector('.evidence-original p')).toHaveTextContent(
      syntheticOverview.answer.replace(/\s+/g, ' '),
    );
    expect(
      screen.getByRole('list', { name: 'Evidence' }).children,
    ).toHaveLength(syntheticOverview.evidence.length);
  });
  it('keeps hostile quoted feature names as DOM text', () => {
    const result = structuredClone(syntheticOverview);
    const name = '<img src=x onerror=alert(1)>';
    result.evidence.find((item) => item.id === 'feature_1')!.statement =
      `The first captured feature is named ${JSON.stringify(name)} (sketch; active).`;
    result.answer = result.answer.replace('"Sketch 1"', JSON.stringify(name));
    render(<AnswerContent result={result} />);
    expect(screen.getByText(name)).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
  });
  it('retains the full uncertainty text inside the collapsed evidence disclosure', () => {
    render(<AnswerContent result={syntheticOverview} />);
    expect(
      screen.queryByRole('heading', { name: 'Technical limits' }),
    ).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    const details = screen.getByRole('heading', {
      name: 'Technical limits',
    }).parentElement!;
    expect(details).toHaveTextContent(syntheticOverview.uncertainties[0]!);
  });
});
