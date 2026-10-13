import { expect, it, vi } from 'vitest';
import { parseProof, readCad } from './api';
import { syntheticProof } from './__fixtures__/proof';
import { syntheticMassStructure } from './__fixtures__/massStructure';

it.each([
  null,
  [],
  {},
  { ...syntheticProof, has_mass: 'true' },
  { ...syntheticProof, request_id: 'private-provider-id' },
  { ...syntheticProof, captured_at: 'arbitrary text' },
  { ...syntheticProof, features: { ...syntheticProof.features, count: -1 } },
  { ...syntheticProof, features: { ...syntheticProof.features, count: 2001 } },
  {
    ...syntheticProof,
    features: { ...syntheticProof.features, retry_after_seconds: -5 },
  },
  { ...syntheticProof, features: { ...syntheticProof.features, raw: {} } },
  {
    ...syntheticProof,
    features: { ...syntheticProof.features, code: 'private text' },
  },
  {
    ...syntheticProof,
    features: { ...syntheticProof.features, status: 'forbidden' },
  },
])('rejects malformed API response %#', (value) => {
  expect(() => parseProof(value)).toThrow('Invalid CAD read');
});

it.each(['valid', 'unsafe', 'production', 'success'])(
  'handles a %s development structure header without changing the proof contract',
  async (mode) => {
    const header =
      mode === 'unsafe'
        ? JSON.stringify({
            ...syntheticMassStructure,
            raw: 'private-provider-body',
          })
        : JSON.stringify(syntheticMassStructure);
    const response =
      mode === 'success'
        ? syntheticProof
        : {
            ...syntheticProof,
            has_mass: null,
            mass: {
              status: 'provider_failure',
              code: 'invalid_response',
              count: null,
              retry_after_seconds: null,
            },
          };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(response), {
          headers: { 'X-Forge-Mass-Structure': header },
        }),
      ),
    );
    if (mode === 'production') vi.stubEnv('DEV', false);
    try {
      const result = await readCad(
        {
          documentId: 'a'.repeat(24),
          elementId: 'b'.repeat(24),
          server: 'https://cad.onshape.com',
          revision: { kind: 'workspace', workspaceId: 'c'.repeat(24) },
        },
        'f'.repeat(64),
        new AbortController().signal,
      );
      expect(result.massStructure).toBe(
        mode === 'valid'
          ? JSON.stringify(syntheticMassStructure, null, 2)
          : undefined,
      );
      expect(result.mass).toEqual(response.mass);
      expect(JSON.stringify(result)).not.toContain('private-provider-body');
    } finally {
      vi.unstubAllEnvs();
    }
  },
);
it('sends only exact references and Forge session CSRF; no provider routing or credential data', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(syntheticProof)));
  vi.stubGlobal('fetch', fetch);
  await readCad(
    {
      documentId: 'a'.repeat(24),
      elementId: 'b'.repeat(24),
      server: 'https://cad.onshape.com',
      revision: { kind: 'workspace', workspaceId: 'c'.repeat(24) },
      microversionId: 'd'.repeat(24),
    },
    'f'.repeat(64),
    new AbortController().signal,
  );
  const [url, options] = fetch.mock.calls[0] as [string, RequestInit];
  expect(
    [...new URL(url, 'https://forge.test').searchParams.keys()].sort(),
  ).toEqual(['documentId', 'elementId', 'revisionKind', 'workspaceId']);
  expect(options.headers).toEqual({ 'X-CSRF-Token': 'f'.repeat(64) });
  expect(options.credentials).toBe('same-origin');
  expect(options.cache).toBe('no-store');
  expect(options.method).toBeUndefined();
});
