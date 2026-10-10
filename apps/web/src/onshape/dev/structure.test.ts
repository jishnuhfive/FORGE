import { afterEach, describe, expect, it, vi } from 'vitest';
import { sanitizedSelectionStructure, STRUCTURE_LIMITS } from './structure';
import {
  captureSelectionStructure,
  clearDiagnostics,
  diagnosticSnapshot,
  enableDiagnostics,
  resetDiagnostics,
} from './diagnostics';

afterEach(() => {
  resetDiagnostics();
  vi.unstubAllEnvs();
});
// These inputs intentionally probe sanitization, not a claimed Onshape schema.
const sample = (data: unknown) => ({ messageName: 'SELECTION', data });
describe('sanitized structure is independent of private values', () => {
  it('shows structure, capped counts and fixed category labels only', () => {
    const output = sanitizedSelectionStructure(
      sample({
        entities: [{ entityType: 'FACE', entityId: 'private-face-id' }],
        count: 91828,
        isSelected: true,
      }),
    );
    expect(output).toContain('"messageName": "SELECTION"');
    expect(output).toContain('"name": "entityId"');
    expect(output).toContain('"category": "FACE"');
    expect(output).toContain('"length": 1');
    expect(output).toContain('"kind": "number"');
    expect(output).toContain('"kind": "boolean"');
    expect(output).not.toContain('private-face-id');
    expect(output).not.toContain('91828');
  });
  it.each([
    'a'.repeat(24),
    'JHO',
    'h:000100',
    'QWxhZGRpbjpvcGVuIHNlc2FtZQ==',
    'sk-synthetic-secret',
    'Bearer synthetic-token',
    'Private motor name',
    'https://example.test?token=private',
    '123456789',
    '<script>private</script>',
  ])('never copies an arbitrary string value', (value) => {
    const output = sanitizedSelectionStructure(
      sample({
        id: value,
        name: value,
        type: value,
        unknown: [value, { documentId: value }],
      }),
    );
    expect(output).not.toContain(value);
  });
  it('redacts unknown property names, ID keys, private names, nested secrets and unsafe prototypes', () => {
    const output = sanitizedSelectionStructure(
      sample({
        abcdef123456abcdef123456: { entityId: 'FACE' },
        'Customer confidential design': ['private'],
        access_token: { name: 'credential-contents' },
        __proto__: null,
      }),
    );
    expect(output).toContain('<redacted-key-1>');
    expect(output).toContain('access_token');
    for (const value of [
      'abcdef123456abcdef123456',
      'Customer confidential design',
      'credential-contents',
      '"category": "FACE"',
    ])
      expect(output).not.toContain(value);
  });
  it('produces identical results for different private values and unknown keys', () => {
    const one = sample({
      'secret-private-key-a': {
        items: ['private-a'],
        count: 17,
        name: 'Part A',
      },
    });
    const two = sample({
      'secret-private-key-b': {
        items: ['private-b'],
        count: 29,
        name: 'Part B',
      },
    });
    expect(sanitizedSelectionStructure(one)).toBe(
      sanitizedSelectionStructure(two),
    );
  });
  it('does not invoke getters, toJSON, stringify callbacks or interpolate exceptions', () => {
    const getter = vi.fn(() => {
      throw new Error('private-error');
    });
    const data = { toJSON: getter };
    Object.defineProperty(data, 'name', { enumerable: true, get: getter });
    const output = sanitizedSelectionStructure(sample(data));
    expect(getter).not.toHaveBeenCalled();
    expect(output).toContain('accessor-omitted');
    expect(output).not.toContain('private-error');
    expect(
      sanitizedSelectionStructure(
        new Proxy({}, { getOwnPropertyDescriptor: getter }),
      ),
    ).toBeNull();
  });
  it('safely handles cycles, maps, dates, buffers, blobs and bigint without data extraction', () => {
    const data: Record<string, unknown> = {
      items: [
        new Map([['private', 'value']]),
        new Date(),
        new Uint8Array([42]),
      ],
      result: new Blob(['private']),
      id: 424242n,
    };
    data.data = data;
    const output = sanitizedSelectionStructure(sample(data));
    expect(output).toContain('opaque-object');
    expect(output).toContain('reference');
    expect(output).toContain('bigint');
    expect(output).not.toContain('private');
    expect(output).not.toContain('424242');
  });
  it('bounds very wide/deep/long payloads without retaining raw strings', () => {
    let data: unknown = 'private-leaf';
    for (let index = 0; index < 1000; ++index) data = { data };
    const wide = Object.fromEntries(
      Array.from({ length: 50_000 }, (_, i) => [
        `private-key-${i}`,
        { name: 'private-value' },
      ]),
    );
    const output = sanitizedSelectionStructure(
      sample({
        data,
        entities: Array(100_000).fill({ id: 'private-id' }),
        items: wide,
        name: 'x'.repeat(1_000_000),
      }),
    );
    expect(output?.length).toBeLessThanOrEqual(
      STRUCTURE_LIMITS.outputCharacters,
    );
    expect(output).toContain('"truncated": true');
    expect(output).toContain('"lengthCapped": true');
    expect(output).not.toContain('private');
    expect(output).not.toContain('xxxx');
  });
  it.each([
    null,
    [],
    {},
    'SELECTION',
    { messageName: 'show' },
    { messageName: 1 },
  ])('does not diagnose non-SELECTION envelopes', (value) =>
    expect(sanitizedSelectionStructure(value)).toBeNull(),
  );
});
describe('explicit opt-in and ephemeral diagnostic store', () => {
  it('captures only after enabling, keeps only sanitized output and clears/disables', () => {
    captureSelectionStructure(sample({ id: 'private' }));
    expect(diagnosticSnapshot().structure).toBeNull();
    enableDiagnostics();
    captureSelectionStructure(sample({ id: 'private' }));
    expect(diagnosticSnapshot().structure).toContain('<redacted>');
    expect(JSON.stringify(diagnosticSnapshot())).not.toContain('private');
    clearDiagnostics();
    expect(diagnosticSnapshot()).toEqual({ enabled: true, structure: null });
    resetDiagnostics();
    captureSelectionStructure(sample({}));
    expect(diagnosticSnapshot()).toEqual({ enabled: false, structure: null });
  });
  it('replaces the last structure and rate-limits bursts before walking data', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1000);
    enableDiagnostics();
    captureSelectionStructure(sample({ entityType: 'FACE' }));
    const first = diagnosticSnapshot();
    captureSelectionStructure(sample({ entityType: 'EDGE' }));
    expect(diagnosticSnapshot()).toBe(first);
    vi.spyOn(Date, 'now').mockReturnValue(1100);
    captureSelectionStructure(sample({ entityType: 'EDGE' }));
    expect(diagnosticSnapshot().structure).toContain('EDGE');
    expect(diagnosticSnapshot().structure).not.toContain('FACE');
  });
  it('cannot enable or capture when DEV is false', () => {
    vi.stubEnv('DEV', false);
    enableDiagnostics();
    captureSelectionStructure(sample({}));
    expect(diagnosticSnapshot()).toEqual({ enabled: false, structure: null });
  });
});
