import { attachDiagnostic, bounded, fetchCad, object, parseProof } from './api';
import type { ReadProof } from './api';
import type { OnshapeClientContext } from '../onshape/model';

export type Completeness =
  'complete' | 'partial' | 'unverified' | 'unavailable';
export type Parameter = {
  label: string;
  kind:
    | 'boolean'
    | 'string'
    | 'enum'
    | 'expression'
    | 'query_count'
    | 'unsupported';
  state: 'available' | 'unavailable' | 'unsupported' | 'omitted';
  text: string | null;
  boolean: boolean | null;
  count: number | null;
};
export type Feature = {
  index: number;
  name: string;
  feature_type: 'sketch' | 'extrude' | 'fillet' | 'chamfer' | 'unknown';
  suppression: 'active' | 'suppressed' | 'unverified';
  completeness: Completeness;
  parameters: Parameter[];
  omitted_parameters: number;
};
export type Part = {
  index: number;
  name: string;
  description: string | null;
  part_number: string | null;
  body_type: string | null;
  state: string | null;
  is_mesh: boolean | null;
  mass: 'unverified';
  completeness: Completeness;
};
export type Body = {
  index: number;
  body_type: string | null;
  face_count: number | null;
  edge_count: number | null;
  vertex_count: number | null;
};
export type EvidenceList<T> = {
  items: T[];
  completeness: Completeness;
  returned_count: number;
  omitted_count: number;
};
export type Inspector = {
  schema_version: 'forge-cad-inspector-v1';
  context: {
    kind: 'workspace_part_studio';
    configuration: 'default';
    evaluation: 'end_of_list';
  };
  source: ReadProof;
  freshness: 'captured_unverified' | 'stale';
  features: EvidenceList<Feature>;
  parts: EvidenceList<Part>;
  bodies: EvidenceList<Body>;
  physical: {
    mass: 'available' | 'unavailable' | 'partial' | 'unverified';
    volume: 'reported' | 'partial' | 'unavailable' | 'unverified';
    missing_mass: boolean | null;
    units: 'provider_native_unverified';
    scope: 'aggregate';
  };
};
const complete = ['complete', 'partial', 'unverified', 'unavailable'];
function check(value: boolean): asserts value {
  if (!value) throw new Error('Invalid CAD inspector');
}
const oneOf = (value: unknown, values: readonly string[]) =>
  typeof value === 'string' && values.includes(value);
const encoder = new TextEncoder();
const text = (value: unknown) =>
  typeof value === 'string' &&
  value.length <= 256 &&
  encoder.encode(value).byteLength <= 256 &&
  [...value].every((char) => {
    const code = char.codePointAt(0)!;
    return (
      code >= 32 &&
      code !== 127 &&
      !(code >= 0xd800 && code <= 0xdfff) &&
      !(code >= 0x202a && code <= 0x202e) &&
      !(code >= 0x2066 && code <= 0x2069)
    );
  });
const nullableText = (value: unknown) => value === null || text(value);
const nullableBool = (value: unknown) =>
  value === null || typeof value === 'boolean';
function parameter(value: unknown) {
  const p = object(value, [
    'label',
    'kind',
    'state',
    'text',
    'boolean',
    'count',
  ]);
  check(
    text(p.label) &&
      oneOf(p.kind, [
        'boolean',
        'string',
        'enum',
        'expression',
        'query_count',
        'unsupported',
      ]) &&
      oneOf(p.state, ['available', 'unavailable', 'unsupported', 'omitted']),
  );
  check(
    nullableText(p.text) &&
      nullableBool(p.boolean) &&
      (p.count === null || bounded(p.count, 0, 2000)),
  );
  if (p.state === 'available') {
    check(
      p.kind === 'boolean'
        ? typeof p.boolean === 'boolean' && p.text === null && p.count === null
        : p.kind === 'query_count'
          ? p.count !== null && p.text === null && p.boolean === null
          : oneOf(p.kind, ['string', 'enum', 'expression']) &&
            p.text !== null &&
            p.boolean === null &&
            p.count === null,
    );
  } else check(p.text === null && p.boolean === null && p.count === null);
  check((p.kind === 'unsupported') === (p.state === 'unsupported'));
}
function feature(value: unknown, index: number) {
  const f = object(value, [
    'index',
    'name',
    'feature_type',
    'suppression',
    'completeness',
    'parameters',
    'omitted_parameters',
  ]);
  check(
    f.index === index &&
      text(f.name) &&
      oneOf(f.feature_type, [
        'sketch',
        'extrude',
        'fillet',
        'chamfer',
        'unknown',
      ]) &&
      oneOf(f.suppression, ['active', 'suppressed', 'unverified']) &&
      oneOf(f.completeness, complete),
  );
  check(
    Array.isArray(f.parameters) &&
      f.parameters.length <= 16 &&
      bounded(f.omitted_parameters, 0, 512),
  );
  f.parameters.forEach(parameter);
}
function part(value: unknown, index: number) {
  const p = object(value, [
    'index',
    'name',
    'description',
    'part_number',
    'body_type',
    'state',
    'is_mesh',
    'mass',
    'completeness',
  ]);
  check(
    p.index === index &&
      text(p.name) &&
      ['description', 'part_number', 'body_type', 'state'].every((k) =>
        nullableText(p[k]),
      ) &&
      nullableBool(p.is_mesh) &&
      p.mass === 'unverified' &&
      oneOf(p.completeness, complete),
  );
}
function body(value: unknown, index: number) {
  const b = object(value, [
    'index',
    'body_type',
    'face_count',
    'edge_count',
    'vertex_count',
  ]);
  check(
    b.index === index &&
      nullableText(b.body_type) &&
      ['face_count', 'edge_count', 'vertex_count'].every(
        (k) => b[k] === null || bounded(b[k], 0, 20000),
      ),
  );
}
export function parseInspector(value: unknown): Inspector {
  const data = object(value, [
    'schema_version',
    'context',
    'source',
    'freshness',
    'features',
    'parts',
    'bodies',
    'physical',
  ]);
  check(data.schema_version === 'forge-cad-inspector-v1');
  const context = object(data.context, ['kind', 'configuration', 'evaluation']);
  check(
    context.kind === 'workspace_part_studio' &&
      context.configuration === 'default' &&
      context.evaluation === 'end_of_list',
  );
  const source = parseProof(data.source);
  check(
    data.freshness ===
      (source.consistency === 'mismatch' ? 'stale' : 'captured_unverified'),
  );
  for (const [name, limit, validate] of [
    ['features', 100, feature],
    ['parts', 200, part],
    ['bodies', 200, body],
  ] as const) {
    const section = object(data[name], [
      'items',
      'completeness',
      'returned_count',
      'omitted_count',
    ]);
    check(
      Array.isArray(section.items) &&
        section.items.length <= limit &&
        oneOf(section.completeness, complete) &&
        bounded(section.returned_count, 0, 2000) &&
        bounded(section.omitted_count, 0, 2000),
    );
    check(
      section.returned_count ===
        section.items.length + Number(section.omitted_count),
    );
    check(
      (source[name].status !== 'success') ===
        (section.completeness === 'unavailable'),
    );
    if (source[name].status !== 'success') check(section.returned_count === 0);
    if (source[name].count !== null)
      check(source[name].count === section.returned_count);
    if (Number(section.omitted_count) > 0)
      check(section.completeness === 'partial');
    section.items.forEach((item, index) => validate(item, index + 1));
  }
  const p = object(data.physical, [
    'mass',
    'volume',
    'missing_mass',
    'units',
    'scope',
  ]);
  check(
    oneOf(p.mass, ['available', 'unavailable', 'partial', 'unverified']) &&
      oneOf(p.volume, ['reported', 'partial', 'unavailable', 'unverified']) &&
      nullableBool(p.missing_mass) &&
      p.units === 'provider_native_unverified' &&
      p.scope === 'aggregate',
  );
  if (source.mass.status !== 'success')
    check(
      p.mass === 'unverified' &&
        p.volume === 'unverified' &&
        p.missing_mass === null,
    );
  if (p.mass === 'available') check(p.missing_mass !== true);
  return data as Inspector;
}
export async function inspectCad(
  context: OnshapeClientContext,
  csrf: string,
  signal: AbortSignal,
): Promise<Inspector> {
  const response = await fetchCad(context, csrf, signal, 'inspector');
  // Bound response bytes before parsing or allocating the typed model.
  const reader = response.body?.getReader();
  if (!reader) throw new Error('Invalid CAD inspector');
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2 * 1024 * 1024) throw new Error('Invalid CAD inspector');
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const result = parseInspector(
    JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)),
  );
  await attachDiagnostic(response, result.source);
  return result;
}
