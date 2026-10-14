import type { OnshapeClientContext } from '../onshape/model';

export const sectionNames = ['features', 'parts', 'bodies', 'mass'] as const;
export type SectionName = (typeof sectionNames)[number];
export const codes = [
  'ok',
  'connection_required',
  'read_permission_required',
  'permission_or_access_required',
  'document_forbidden',
  'not_found',
  'rate_limited',
  'quota_exceeded',
  'provider_unavailable',
  'invalid_response',
  'response_too_large',
  'redirect_rejected',
  'unsupported_provider',
  'request_in_progress',
  'provider_timeout',
] as const;
export type ReadCode = (typeof codes)[number];
export type Section = {
  status:
    | 'success'
    | 'unavailable'
    | 'unauthorized'
    | 'forbidden'
    | 'not_found'
    | 'rate_limited'
    | 'provider_failure';
  code: ReadCode;
  count: number | null;
  retry_after_seconds: number | null;
};
export type ReadProof = {
  schema_version: 'forge-cad-read-v1';
  request_id: string;
  captured_at: string;
  consistency: 'unverified' | 'mismatch';
  has_mass: boolean | null;
  // Local DEV metadata from a separate strictly validated response header.
  massStructure?: string;
  bodyStructure?: string;
} & Record<SectionName, Section>;

export function object(
  value: unknown,
  keys: readonly string[],
): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Invalid CAD read');
  const result = value as Record<string, unknown>;
  if (
    Object.keys(result).length !== keys.length ||
    keys.some((key) => !(key in result))
  )
    throw new Error('Invalid CAD read');
  return result;
}
export function bounded(value: unknown, min: number, max: number) {
  return (
    typeof value === 'number' &&
    Number.isSafeInteger(value) &&
    value >= min &&
    value <= max
  );
}
export function parseProof(value: unknown): ReadProof {
  const data = object(value, [
    'schema_version',
    'request_id',
    'captured_at',
    'consistency',
    'has_mass',
    ...sectionNames,
  ]);
  if (
    data.schema_version !== 'forge-cad-read-v1' ||
    typeof data.request_id !== 'string' ||
    !/^[a-f0-9]{32}$/.test(data.request_id) ||
    typeof data.captured_at !== 'string' ||
    data.captured_at.length > 40 ||
    !/^\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|\+00:00)$/.test(data.captured_at) ||
    !Number.isFinite(Date.parse(data.captured_at)) ||
    !['unverified', 'mismatch'].includes(data.consistency as string) ||
    !(data.has_mass === null || typeof data.has_mass === 'boolean')
  )
    throw new Error('Invalid CAD read');
  for (const name of sectionNames) {
    const section = object(data[name], [
      'status',
      'code',
      'count',
      'retry_after_seconds',
    ]);
    if (
      ![
        'success',
        'unavailable',
        'unauthorized',
        'forbidden',
        'not_found',
        'rate_limited',
        'provider_failure',
      ].includes(section.status as string) ||
      !codes.includes(section.code as ReadCode) ||
      (section.status === 'success') !== (section.code === 'ok') ||
      !(section.count === null || bounded(section.count, 0, 2000)) ||
      (section.status !== 'success' && section.count !== null) ||
      !(
        section.retry_after_seconds === null ||
        bounded(section.retry_after_seconds, 1, 86400)
      )
    )
      throw new Error('Invalid CAD read');
  }
  return data as ReadProof;
}
export class CadReadError extends Error {
  constructor(
    public readonly code:
      | 'connection_required'
      | 'session_check_required'
      | 'unsupported_context'
      | 'provider_unavailable',
  ) {
    super(code);
  }
}
export async function fetchCad(
  context: OnshapeClientContext,
  csrf: string,
  signal: AbortSignal,
  projection: 'snapshot' | 'inspector',
): Promise<Response> {
  if (
    context.revision.kind !== 'workspace' ||
    context.server !== 'https://cad.onshape.com' ||
    (context.elementType && context.elementType !== 'partStudio')
  )
    throw new CadReadError('unsupported_context');
  const params = new URLSearchParams({
    documentId: context.documentId,
    workspaceId: context.revision.workspaceId,
    elementId: context.elementId,
    revisionKind: 'workspace',
  });
  const response = await fetch(
    `/api/onshape/part-studio/${projection}?${params}`,
    {
      credentials: 'same-origin',
      cache: 'no-store',
      signal,
      headers: { 'X-CSRF-Token': csrf },
    },
  );
  if (!response.ok)
    throw new CadReadError(
      response.status === 401
        ? 'connection_required'
        : response.status === 403
          ? 'session_check_required'
          : response.status === 422 || response.status === 400
            ? 'unsupported_context'
            : 'provider_unavailable',
    );
  return response;
}
export async function attachDiagnostic(response: Response, result: ReadProof) {
  if (import.meta.env.DEV) {
    const header = response.headers.get('X-Forge-Mass-Structure');
    if (header && result.mass.code === 'invalid_response') {
      const { parseMassStructure } = await import('./dev/massStructure');
      const structure = parseMassStructure(header);
      if (structure) result.massStructure = structure;
    }
    const bodyHeader = response.headers.get('X-Forge-Body-Structure');
    if (bodyHeader && result.bodies.status === 'success') {
      const { parseBodyStructure } = await import('./dev/bodyStructure');
      const structure = parseBodyStructure(bodyHeader);
      if (structure) result.bodyStructure = structure;
    }
  }
  return result;
}

export async function readCad(
  context: OnshapeClientContext,
  csrf: string,
  signal: AbortSignal,
): Promise<ReadProof> {
  const response = await fetchCad(context, csrf, signal, 'snapshot');
  const text = await response.text();
  if (text.length > 8192) throw new CadReadError('provider_unavailable');
  return attachDiagnostic(response, parseProof(JSON.parse(text)));
}
