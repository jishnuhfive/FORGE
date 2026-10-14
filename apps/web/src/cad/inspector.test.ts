import { expect, it, vi } from 'vitest';
import { inspectorFixture } from './__fixtures__/inspector';
import { inspectCad, parseInspector } from './inspector';
import type { Inspector } from './inspector';
import { syntheticBodyStructure } from './__fixtures__/bodyStructure';

it('accepts a bounded model and literal expressions without interpreting them', () => {
  const result = parseInspector(inspectorFixture());
  expect(result.features.items.map((f) => f.feature_type)).toEqual([
    'sketch',
    'extrude',
  ]);
  expect(result.features.items[1]?.parameters[0]?.text).toBe('12 mm');
});

it.each(['face_count', 'edge_count', 'vertex_count'] as const)(
  'preserves null %s and rejects geometry and excessive counts',
  (key) => {
    const value = inspectorFixture();
    value.bodies.items[0]![key] = null;
    expect(parseInspector(value).bodies.items[0]![key]).toBeNull();
    expect(() =>
      parseInspector({
        ...value,
        bodies: {
          ...value.bodies,
          items: [{ ...value.bodies.items[0], geometry: { private: true } }],
        },
      }),
    ).toThrow();
    value.bodies.items[0]![key] = 20001;
    expect(() => parseInspector(value)).toThrow();
  },
);

it.each(['valid', 'unsafe', 'production', 'failed-body'])(
  'handles the %s body diagnostic only through the validated DEV header',
  async (mode) => {
    const value = inspectorFixture();
    if (mode === 'failed-body') {
      value.source.bodies = {
        status: 'provider_failure',
        code: 'invalid_response',
        count: null,
        retry_after_seconds: null,
      };
      value.bodies = {
        items: [],
        returned_count: 0,
        omitted_count: 0,
        completeness: 'unavailable',
      };
    }
    const report =
      mode === 'unsafe'
        ? { ...syntheticBodyStructure, raw: 'private-provider-body' }
        : syntheticBodyStructure;
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(value), {
          headers: { 'X-Forge-Body-Structure': JSON.stringify(report) },
        }),
      ),
    );
    if (mode === 'production') vi.stubEnv('DEV', false);
    try {
      const result = await inspectCad(
        {
          documentId: 'a'.repeat(24),
          elementId: 'c'.repeat(24),
          server: 'https://cad.onshape.com',
          revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
        },
        'f'.repeat(64),
        new AbortController().signal,
      );
      expect(result.source.bodyStructure).toBe(
        mode === 'valid'
          ? JSON.stringify(syntheticBodyStructure, null, 2)
          : undefined,
      );
      expect(JSON.stringify(result)).not.toContain('private-provider-body');
    } finally {
      vi.unstubAllEnvs();
    }
  },
);
it.each([
  (v: Inspector) => ({ ...v, raw: { private: 'data' } }),
  (v: Inspector) => ({ ...v, schema_version: 'future' }),
  (v: Inspector) => ({ ...v, freshness: 'fresh' }),
  (v: Inspector) => ({
    ...v,
    context: { ...v.context, documentId: 'private-id' },
  }),
  (v: Inspector) => ({
    ...v,
    source: { ...v.source, access_token: 'private' },
  }),
  (v: Inspector) => ({ ...v, physical: { ...v.physical, units: 'kg' } }),
  (v: Inspector) => ({
    ...v,
    physical: { ...v.physical, mass: 'available', missing_mass: true },
  }),
  (v: Inspector) => ({
    ...v,
    parts: {
      ...v.parts,
      items: [{ ...v.parts.items[0], name: 'x'.repeat(257) }],
    },
  }),
  (v: Inspector) => ({
    ...v,
    bodies: { ...v.bodies, items: [{ ...v.bodies.items[0], face_count: -1 }] },
  }),
  (v: Inspector) => ({ ...v, features: { ...v.features, returned_count: 42 } }),
  (v: Inspector) => ({
    ...v,
    features: {
      ...v.features,
      items: [{ ...v.features.items[0], index: 2 }, v.features.items[1]],
    },
  }),
  (v: Inspector) => ({
    ...v,
    features: {
      ...v.features,
      items: [
        { ...v.features.items[0], feature_id: 'secret' },
        v.features.items[1],
      ],
    },
  }),
  (v: Inspector) => ({
    ...v,
    features: {
      ...v.features,
      items: [
        {
          ...v.features.items[0],
          parameters: [
            {
              label: 'x',
              kind: 'expression',
              state: 'available',
              text: '2 mm',
              boolean: false,
              count: null,
            },
          ],
        },
        v.features.items[1],
      ],
    },
  }),
])('rejects incompatible or private fields %#', (mutate) => {
  expect(() => parseInspector(mutate(inspectorFixture()))).toThrow();
});
it('enforces the stream byte bound before parsing', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response('x'.repeat(2 * 1024 * 1024 + 1))),
  );
  await expect(
    inspectCad(
      {
        documentId: 'a'.repeat(24),
        elementId: 'c'.repeat(24),
        revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
        server: 'https://cad.onshape.com',
      },
      'f'.repeat(64),
      new AbortController().signal,
    ),
  ).rejects.toThrow('Invalid CAD inspector');
});
it.each(['assembly', 'drawing'] as const)(
  'rejects unsupported %s without fetching',
  async (elementType) => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    await expect(
      inspectCad(
        {
          documentId: 'a'.repeat(24),
          elementId: 'c'.repeat(24),
          revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
          server: 'https://cad.onshape.com',
          elementType,
        },
        'f'.repeat(64),
        new AbortController().signal,
      ),
    ).rejects.toThrow('unsupported_context');
    expect(fetch).not.toHaveBeenCalled();
  },
);

it.each(['\ud800', '😀'.repeat(65)])(
  'rejects text outside the UTF-8 display contract %#',
  (name) => {
    const value = inspectorFixture();
    value.features.items[0]!.name = name;
    expect(() => parseInspector(value)).toThrow();
  },
);
