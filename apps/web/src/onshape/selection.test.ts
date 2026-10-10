import { describe, expect, it, vi } from 'vitest';
import { parseSelection } from './selection';
import {
  clearedSelection,
  edgeSelection,
  faceSelection,
} from './__fixtures__/selection';

describe('bounded Part Studio selection adapter', () => {
  it.each([
    [edgeSelection, 'edge', 'synthetic-edge-reference'],
    [faceSelection, 'face', 'synthetic-face-reference'],
  ] as const)(
    'normalizes a single entity without retaining unknown fields',
    (payload, type, reference) => {
      expect(parseSelection(payload)).toEqual([{ type, reference }]);
    },
  );
  it('an explicit empty array means no selection', () => {
    expect(parseSelection(clearedSelection)).toEqual([]);
  });
  it.each([
    null,
    [],
    'SELECTION',
    {},
    { selections: [] },
    { messageName: 'other', selections: [] },
    { messageName: 'SELECTION' },
    ...[null, {}, '', 1].map((selections) => ({
      messageName: 'SELECTION',
      selections,
    })),
    ...[null, [], {}, 1, 'entity'].map((entity) => ({
      messageName: 'SELECTION',
      selections: [entity],
    })),
    ...[
      { selectionType: 'PART' },
      { selectionType: undefined },
      { entityType: 'VERTEX' },
      { entityType: 'face' },
      { entityType: undefined },
      { selectionId: '' },
      { selectionId: undefined },
      { selectionId: 1 },
      { selectionId: 'x'.repeat(1025) },
      { selectionId: 'synthetic\nreference' },
      { occurrencePath: [] },
      { occurrencePath: 'unverified' },
      { occurrencePath: null },
    ].map((change) => ({
      messageName: 'SELECTION',
      selections: [{ ...edgeSelection.selections[0], ...change }],
    })),
    {
      messageName: 'SELECTION',
      selections: [...edgeSelection.selections, ...faceSelection.selections],
    },
    { messageName: 'SELECTION', selections: new Array(1) },
  ])('rejects malformed or unsupported input %#', (payload) => {
    expect(parseSelection(payload)).toBeNull();
  });
  it('does not assume a topology ID syntax or retain unknown metadata', () => {
    const reference = 'synthetic opaque:ref/with punctuation';
    expect(
      parseSelection({
        messageName: 'SELECTION',
        selections: [
          { ...edgeSelection.selections[0], selectionId: reference },
        ],
      }),
    ).toEqual([{ type: 'edge', reference }]);
  });
  it('ignores unknown fields without reading accessors and rejects accessors on known fields', () => {
    const getter = vi.fn(() => 'never read');
    const entity = { ...edgeSelection.selections[0] };
    Object.defineProperty(entity, 'unknown', { get: getter });
    expect(
      parseSelection({ messageName: 'SELECTION', selections: [entity] }),
    ).toEqual([{ type: 'edge', reference: 'synthetic-edge-reference' }]);
    Object.defineProperty(entity, 'selectionId', { get: getter });
    expect(
      parseSelection({ messageName: 'SELECTION', selections: [entity] }),
    ).toBeNull();
    expect(getter).not.toHaveBeenCalled();
  });
  it('accepts an absent occurrence path, without accepting inherited required fields', () => {
    const entity = {
      selectionType: 'ENTITY',
      entityType: 'EDGE',
      selectionId: 'synthetic-ref',
    };
    expect(
      parseSelection({ messageName: 'SELECTION', selections: [entity] }),
    ).not.toBeNull();
    expect(
      parseSelection({
        messageName: 'SELECTION',
        selections: [Object.create(entity) as object],
      }),
    ).toBeNull();
  });
});
