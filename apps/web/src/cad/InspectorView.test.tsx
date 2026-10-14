import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { InspectorView } from './InspectorView';
import { inspectorFixture } from './__fixtures__/inspector';
import { syntheticProof } from './__fixtures__/proof';
const open = (text: string) => {
  const summary = screen.getByText(text).closest('summary')!;
  summary.closest('details')!.open = true;
  return summary;
};
it('shows ordered features and literal parameter details, parts and topology', () => {
  render(<InspectorView result={inspectorFixture()} />);
  expect(
    screen.getByRole('heading', { name: 'Part Studio overview' }),
  ).toBeVisible();
  const list = screen.getByRole('list', { name: 'Feature order' });
  expect(
    [...list.querySelectorAll('li strong')].map((node) => node.textContent),
  ).toEqual(['Sketch 1', 'Extrude 1']);
  open('Extrude 1');
  expect(screen.getByText(/12 mm/)).toBeVisible();
  expect(screen.getByText('False')).toBeVisible();
  open('Part 1');
  expect(screen.getByText('DEMO-001')).toBeVisible();
  expect(screen.getByText('Synthetic preview part')).toBeVisible();
  open('Body 1 · SOLID');
  expect(screen.getByText('Faces')).toBeVisible();
  expect(screen.getByText('6')).toBeVisible();
});
it('filters only safe fetched models and preserves original feature order', () => {
  render(<InspectorView result={inspectorFixture()} />);
  fireEvent.change(screen.getByLabelText('Search features'), {
    target: { value: 'extrude' },
  });
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
  expect(screen.getByText('Extrude 1').closest('li')).toHaveAttribute(
    'value',
    '2',
  );
  fireEvent.change(screen.getByLabelText('Search parts'), {
    target: { value: 'absent' },
  });
  expect(screen.getByText('No matching parts.')).toBeVisible();
});
it('renders suppression, unknown types, unknown parameters and omitted evidence', () => {
  const result = inspectorFixture();
  result.features.completeness = 'partial';
  const feature = result.features.items[0]!;
  feature.feature_type = 'unknown';
  feature.suppression = 'suppressed';
  feature.completeness = 'partial';
  feature.omitted_parameters = 3;
  feature.parameters = [
    {
      label: 'Option',
      kind: 'unsupported',
      state: 'unsupported',
      text: null,
      boolean: null,
      count: null,
    },
  ];
  render(<InspectorView result={result} />);
  open('Sketch 1');
  expect(
    screen.getByText(/Custom or unknown feature · Suppressed/),
  ).toBeVisible();
  expect(screen.getByText('Type not yet interpreted by Forge.')).toBeVisible();
  expect(screen.getByText('Unsupported parameter type')).toBeVisible();
  expect(
    screen.getByText('3 parameters omitted by the display limit.'),
  ).toBeVisible();
});
it('empty sections do not reuse old lists', () => {
  const { rerender } = render(<InspectorView result={inspectorFixture()} />);
  const source = structuredClone(syntheticProof);
  for (const name of ['features', 'parts', 'bodies', 'mass'] as const)
    source[name].count = 0;
  rerender(<InspectorView result={inspectorFixture(source)} />);
  expect(screen.getByText('No features returned.')).toBeVisible();
  expect(screen.getByText('No parts returned.')).toBeVisible();
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
  expect(screen.getByText('No mass-property bodies returned')).toBeVisible();
});
it('does not treat markup-like names or expressions as HTML', () => {
  const result = inspectorFixture();
  result.features.items[0]!.name = '<img src=x onerror=alert(1)>';
  render(<InspectorView result={result} />);
  expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible();
  expect(document.querySelector('img')).toBeNull();
});
it('shows partial physical evidence and missing topology without fabricating a zero', () => {
  const result = inspectorFixture();
  result.physical.mass = 'partial';
  result.physical.missing_mass = true;
  result.bodies.items[0]!.face_count = null;
  render(<InspectorView result={result} />);
  expect(screen.getByText(/Mass partially available/)).toBeVisible();
  open('Body 1 · SOLID');
  expect(screen.getByText('Unknown')).toBeVisible();
  open('Physical properties');
  expect(
    screen.getByText(/Numeric mass and volume are withheld/),
  ).toBeVisible();
});

it.each(['face_count', 'edge_count', 'vertex_count'] as const)(
  'keeps unavailable %s unknown while retaining supplied counts',
  (key) => {
    const result = inspectorFixture();
    result.bodies.items[0]![key] = null;
    render(<InspectorView result={result} />);
    open('Body 1 · SOLID');
    const details = screen.getByText('Body 1 · SOLID').closest('details')!;
    expect(details.querySelectorAll('dd')).toHaveLength(3);
    expect(
      [...details.querySelectorAll('dd')].map((node) => node.textContent),
    ).toEqual(
      (['face_count', 'edge_count', 'vertex_count'] as const).map((field, i) =>
        field === key ? 'Unknown' : String([6, 12, 8][i]),
      ),
    );
    expect(details.textContent).not.toMatch(/\b0\b/);
  },
);
