import { expect, it, vi } from 'vitest';
import { syntheticMassStructure } from '../__fixtures__/massStructure';
import { parseMassStructure } from './massStructure';

const previousStructure = {
  diagnostic: syntheticMassStructure.diagnostic,
  reason: syntheticMassStructure.reason,
  recordKind: syntheticMassStructure.recordKind,
  fields: syntheticMassStructure.fields,
  validation: syntheticMassStructure.validation,
};

it('validates and formats known structure metadata only', () => {
  const text = parseMassStructure(JSON.stringify(syntheticMassStructure));
  expect(text).toBe(JSON.stringify(syntheticMassStructure, null, 2));
  expect(text!.length).toBeLessThanOrEqual(8192);
});

it.each([
  { field: 'mass', reason: 'invalid_bounds' },
  {
    field: 'mass',
    reason: 'invalid_bounds',
    failedPredicates: ['bounds_order'],
  },
  {
    field: 'volume',
    reason: 'invalid_bounds',
    failedPredicates: ['negative_nominal'],
  },
  {
    ...syntheticMassStructure.validation[0],
    failedPredicates: ['negative_nominal'],
    comparisons: {
      position0_vs_position1: 'greater',
      position0_vs_position2: 'equal',
      position1_vs_position2: 'less',
    },
  },
])(
  'accepts only fixed optional predicate and comparison metadata %#',
  (failure) => {
    const report = { ...previousStructure, validation: [failure] };
    expect(parseMassStructure(JSON.stringify(report))).toBe(
      JSON.stringify(report, null, 2),
    );
  },
);

it('accepts previous diagnostic reports without new mass facts', () => {
  expect(parseMassStructure(JSON.stringify(previousStructure))).toBe(
    JSON.stringify(previousStructure, null, 2),
  );
});

it.each([true, false])(
  'accepts the authorized hasMass boolean %s',
  (hasMass) => {
    const report = { ...syntheticMassStructure, hasMass };
    expect(parseMassStructure(JSON.stringify(report))).toBe(
      JSON.stringify(report, null, 2),
    );
  },
);

it.each(['zero', 'positive'])(
  'accepts missing count category %s',
  (category) => {
    const report = {
      ...syntheticMassStructure,
      massMissingCountCategory: category,
    };
    expect(parseMassStructure(JSON.stringify(report))).toBe(
      JSON.stringify(report, null, 2),
    );
  },
);

it.each([
  { massSigns: null },
  { massSigns: ['zero', 'negative', 'positive'] },
  { massSigns: { position0: 'zero', position1: 'negative' } },
  { massSigns: { ...syntheticMassStructure.massSigns, position3: 'positive' } },
  { massSigns: { ...syntheticMassStructure.massSigns, position1: -12345 } },
  {
    massSigns: {
      ...syntheticMassStructure.massSigns,
      position1: 'private-value',
    },
  },
  {
    massSigns: { ...syntheticMassStructure.massSigns, raw: 'synthetic-token' },
  },
  { hasMass: 'false' },
  { hasMass: 0 },
  { hasMass: null },
  { massMissingCountCategory: 12345 },
  { massMissingCountCategory: 'negative' },
  { massMissingCountCategory: 'https://private.invalid/?token=secret' },
  { massMissingCount: 12345 },
  { validation: [{ field: 'volume', reason: 'invalid_bounds' }] },
  { validation: [{ field: 'mass', reason: 'type_mismatch' }] },
])('rejects numeric/private/malformed or misplaced mass facts %#', (extra) => {
  expect(
    parseMassStructure(JSON.stringify({ ...syntheticMassStructure, ...extra })),
  ).toBeNull();
});

it.each([
  { failedPredicates: [] },
  { failedPredicates: ['private-provider-message'] },
  { failedPredicates: ['bounds_order', 'bounds_order'] },
  {
    failedPredicates: ['bounds_order', 'negative_nominal', 'unexpected_length'],
  },
  { failedPredicates: ['unexpected_length'] },
  { failedPredicates: null },
  { comparisons: { position0_vs_position1: 'less' } },
  {
    comparisons: {
      ...syntheticMassStructure.validation[0]!.comparisons,
      raw: 12345,
    },
  },
  {
    comparisons: {
      ...syntheticMassStructure.validation[0]!.comparisons,
      position0_vs_position1: 12345,
    },
  },
  {
    comparisons: {
      ...syntheticMassStructure.validation[0]!.comparisons,
      position0_vs_position1: 'https://private.invalid/?token=secret',
    },
  },
  { comparisons: null },
  { field: 'principalInertia' },
  { reason: 'type_mismatch' },
  { values: [12345, 12344, 12346] },
])(
  'rejects private, numeric or malformed comparison and predicate metadata %#',
  (extra) => {
    const report = {
      ...syntheticMassStructure,
      validation: [{ ...syntheticMassStructure.validation[0], ...extra }],
    };
    expect(parseMassStructure(JSON.stringify(report))).toBeNull();
  },
);

it.each([
  null,
  [],
  {},
  { ...syntheticMassStructure, raw: 'private-provider-body' },
  { ...syntheticMassStructure, reason: 'private-provider-error' },
  { ...syntheticMassStructure, recordKind: 'private-body-id' },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'private-key', type: 'string' }],
  },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'mass', type: 'number', value: 12345 }],
  },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'mass', type: 'private-value' }],
  },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'mass', type: 'array', length: -1, items: [] }],
  },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'mass', type: 'array', length: 100001, items: [] }],
  },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'mass', type: 'array', length: 1.5, items: [] }],
  },
  {
    ...syntheticMassStructure,
    fields: [
      { field: 'mass', type: 'array', length: 1, items: ['private-value'] },
    ],
  },
  {
    ...syntheticMassStructure,
    fields: [{ field: 'bodies', type: 'object', length: 1 }],
  },
  {
    ...syntheticMassStructure,
    fields: Array(19).fill({ field: 'mass', type: 'absent' }),
  },
  {
    ...syntheticMassStructure,
    validation: [{ field: 'private-body', reason: 'type_mismatch' }],
  },
  {
    ...syntheticMassStructure,
    validation: [{ field: 'mass', reason: 'private-error' }],
  },
  {
    ...syntheticMassStructure,
    validation: [{ field: 'mass', reason: 'type_mismatch', input: 'secret' }],
  },
  {
    ...syntheticMassStructure,
    validation: Array(9).fill({ field: 'mass', reason: 'type_mismatch' }),
  },
])('rejects unexpected fields, values and unbounded structure %#', (value) => {
  expect(parseMassStructure(JSON.stringify(value))).toBeNull();
});

it('rejects malformed and oversized JSON', () => {
  expect(parseMassStructure('private-provider-response')).toBeNull();
  expect(parseMassStructure(' '.repeat(4097))).toBeNull();
});

it('rejects all structure metadata outside development', () => {
  vi.stubEnv('DEV', false);
  try {
    expect(
      parseMassStructure(JSON.stringify(syntheticMassStructure)),
    ).toBeNull();
  } finally {
    vi.unstubAllEnvs();
  }
});
