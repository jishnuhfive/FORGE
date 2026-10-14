import { expect, it, vi } from 'vitest';
import { syntheticBodyStructure } from '../__fixtures__/bodyStructure';
import { parseBodyStructure } from './bodyStructure';

it('preserves only fixed presence/type/length facts, including an empty array', () => {
  expect(parseBodyStructure(JSON.stringify(syntheticBodyStructure))).toBe(
    JSON.stringify(syntheticBodyStructure, null, 2),
  );
});
it.each([
  null,
  [],
  {},
  { ...syntheticBodyStructure, raw: 'private' },
  { bodyDetails: { ...syntheticBodyStructure.bodyDetails, id: 'private' } },
  ...[
    { present: true, type: 'array', length: 20001 },
    { present: true, type: 'array', length: -1 },
    { present: true, type: 'array', length: 1.5 },
    { present: true, type: 'array', length: null },
    { present: false, type: 'array', length: 0 },
    { present: 'yes', type: 'array', length: 1 },
    { present: true, type: 'missing', length: 0 },
    { present: true, type: 'private', length: null },
    { present: true, type: 'array', length: 1, geometry: {} },
  ].map((faces) => ({
    bodyDetails: { ...syntheticBodyStructure.bodyDetails, faces },
  })),
])('rejects unknown properties, types and inconsistent bounds %#', (value) => {
  expect(parseBodyStructure(JSON.stringify(value))).toBeNull();
});
it('rejects malformed or oversized data and disables production parsing', () => {
  expect(parseBodyStructure('{')).toBeNull();
  expect(parseBodyStructure(' '.repeat(513))).toBeNull();
  vi.stubEnv('DEV', false);
  try {
    expect(
      parseBodyStructure(JSON.stringify(syntheticBodyStructure)),
    ).toBeNull();
  } finally {
    vi.unstubAllEnvs();
  }
});
