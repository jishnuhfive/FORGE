import { describe, expect, it } from 'vitest';
import {
  parseCreation,
  parseCreationResult,
  type CreationResponse,
} from './api';
import { ready, verified } from './__fixtures__/plate';

describe('creation wire parsing', () => {
  it('derives readable step details from the server plan', () => {
    const r = parseCreation(ready()) as Extract<
      CreationResponse,
      { status: 'ready' }
    >;
    expect(r.steps.map((s) => s.intent)).toEqual([
      'define_base_profile',
      'form_base_body',
      'define_cut_profile',
      'remove_material',
    ]);
    expect(r.steps[0]?.detail).toContain('60 mm × 40 mm');
    expect(r.steps[1]?.detail).toContain('10 mm deep');
    expect(r.steps[3]?.detail).toContain('through all');
  });
  it('rejects explanations that grant authority or do not match the plan', () => {
    const base = ready();
    const bad = (mutate: (e: Record<string, unknown>[]) => void) => {
      const copy = structuredClone(base);
      mutate(copy.explanations as Record<string, unknown>[]);
      expect(() => parseCreation(copy)).toThrow();
    };
    bad((e) => {
      e[0]!.authority = 'execute';
    });
    bad((e) => {
      e.reverse();
    });
    bad((e) => {
      e.pop();
    });
  });
  it('rejects unknown fields, intents and provider payloads', () => {
    expect(() => parseCreation({ ...ready(), provider_id: 'x' })).toThrow();
    const r = ready();
    (r.plan.steps[0] as { intent: string }).intent = 'remove_material';
    expect(() => parseCreation(r)).toThrow();
    expect(() => parseCreation({ status: 'ok' })).toThrow();
  });
  it('never reports success unless every step is verified', () => {
    expect(parseCreationResult(verified, 4).state).toBe('verified_success');
    expect(() =>
      parseCreationResult(
        {
          state: 'verified_success',
          steps: ['verified_success', 'verified_success', 'skipped', 'skipped'],
        },
        4,
      ),
    ).toThrow();
    expect(() =>
      parseCreationResult({ state: 'write_failed', steps: verified.steps }, 4),
    ).toThrow();
    expect(() => parseCreationResult(verified, 3)).toThrow();
  });
});
