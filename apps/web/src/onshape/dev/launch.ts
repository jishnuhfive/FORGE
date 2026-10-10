import {
  approvedOrigin,
  parseLaunch,
  OPAQUE_LAUNCH_METADATA,
  validOpaqueLaunchMetadata,
} from '../context';

// Read-only explanation of the existing parser. Does not grant trust or change
// parsing rules. Parity tests tie this diagnostic to the production boundary.
const knownNames = [
  'documentId',
  'workspaceId',
  'elementId',
  'server',
  'versionId',
  'workspaceOrVersion',
  'workspaceOrVersionId',
  'microversionId',
  'companyId',
  'userId',
  'locale',
  ...OPAQUE_LAUNCH_METADATA,
] as const;
const idNames = new Set<string>([
  'documentId',
  'workspaceId',
  'elementId',
  'versionId',
  'workspaceOrVersionId',
  'microversionId',
  'userId',
]);
const idFormat = /^[a-f0-9]{24}$/;
const hasControl = (value: string) =>
  Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127;
  });

type Field = {
  name: string;
  expected: boolean;
  required: boolean;
  present: boolean;
  occurrences: number;
  type: 'string' | 'missing';
  length: number | null;
  lengths: number[];
  formatValid: boolean | null;
  validation: 'valid' | 'invalid' | 'absent';
  reasonCodes: string[];
  normalizedOrigin?: string | null;
  trusted?: boolean;
};
function safeName(name: string, index: number): string {
  // Parameter names are requested, but ID/token-like or non-field-like names
  // must not become an escape hatch for private values. Never reflect URLs.
  return /^[a-z][A-Za-z_]{0,47}$/.test(name) && !/[a-f0-9]{16}/i.test(name)
    ? name
    : `<redacted-parameter-name-${index + 1}>`;
}
function serverInfo(value: string) {
  const trusted = approvedOrigin(value) !== null;
  let normalizedOrigin: string | null = null;
  const reasons: string[] = [];
  if (value.length > 256)
    return { normalizedOrigin, trusted: false, reasons: ['value-too-long'] };
  if (value.trim() !== value || /[\\\s]/.test(value))
    reasons.push('server-whitespace-or-backslash');
  try {
    const url = new URL(value);
    // Reflect only an operator-approved origin. Unknown hosts can contain IDs
    // or credentials; report their failure code without copying that hostname.
    normalizedOrigin = approvedOrigin(url.origin);
    if (url.protocol !== 'https:') reasons.push('server-requires-https');
    if (url.username || url.password) reasons.push('server-credentials');
    if (url.pathname !== '/' && url.pathname !== '')
      reasons.push('server-path');
    if (url.search || url.hash) reasons.push('server-query-or-fragment');
    if (url.port) reasons.push('server-port');
    if (!normalizedOrigin) reasons.push('server-origin-not-allowlisted');
  } catch {
    reasons.push('server-invalid-url');
  }
  return { normalizedOrigin, trusted, reasons };
}

/** Returns sanitized text only. Never returns the parsed context, raw URL or values. */
export function sanitizedLaunchDiagnostic(
  search: string,
  embedded: boolean,
  extension: boolean,
): string | null {
  if (!import.meta.env.DEV) return null;
  const parsed = parseLaunch(search, embedded, extension);
  const base = {
    format: 'forge-launch-diagnostic-v1',
    parserStatus: parsed.status,
    parserReason:
      parsed.issue ?? (parsed.context ? 'valid-context' : 'missing-context'),
  };
  if (search.length > 4096)
    return JSON.stringify(
      {
        ...base,
        reasonCodes: ['query-too-long'],
        fieldsInspected: false,
      },
      null,
      2,
    );
  const params = new URLSearchParams(search);
  const names = [...new Set(params.keys())];
  const alternate =
    params.has('versionId') ||
    params.has('workspaceOrVersion') ||
    params.has('workspaceOrVersionId');
  const required = new Set([
    'documentId',
    'elementId',
    'server',
    ...(alternate ? [] : ['workspaceId']),
  ]);
  const inspectNames = [...new Set([...knownNames, ...names])].slice(0, 64);
  const fields: Field[] = inspectNames.map((name) => {
    const values = params.getAll(name);
    const expected = (knownNames as readonly string[]).includes(name);
    const reasons: string[] = [];
    if (!expected) reasons.push('unexpected-parameter');
    if (!values.length && required.has(name)) reasons.push('missing-required');
    if (values.length > 1) reasons.push('duplicate-parameter');
    for (const value of values) {
      if (value.length > 256) reasons.push('value-too-long');
      if (hasControl(value)) reasons.push('control-character');
      if (idNames.has(name) && !idFormat.test(value))
        reasons.push('invalid-id-format');
      if (
        (OPAQUE_LAUNCH_METADATA as readonly string[]).includes(name) &&
        !validOpaqueLaunchMetadata(value)
      )
        reasons.push('invalid-opaque-metadata');
      if (name === 'companyId' && value !== 'cad' && !idFormat.test(value))
        reasons.push('invalid-company-id-format');
      if (
        name === 'locale' &&
        !/^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8}){0,3}$/.test(value)
      )
        reasons.push('invalid-locale-format');
      if (name === 'workspaceOrVersion' && value !== 'w' && value !== 'v')
        reasons.push('unsupported-revision-kind');
      if (name === 'server') reasons.push(...serverInfo(value).reasons);
    }
    const server = name === 'server' ? serverInfo(values[0] ?? '') : null;
    return {
      name: expected ? name : safeName(name, names.indexOf(name)),
      expected,
      required: required.has(name),
      present: values.length > 0,
      occurrences: values.length,
      type: values.length ? 'string' : 'missing',
      length: values.length === 1 ? values[0]!.length : null,
      lengths: values.map((value) => value.length),
      formatValid: values.length ? reasons.length === 0 : null,
      validation: reasons.length
        ? 'invalid'
        : values.length
          ? 'valid'
          : 'absent',
      reasonCodes: [...new Set(reasons)],
      ...(server
        ? { normalizedOrigin: server.normalizedOrigin, trusted: server.trusted }
        : {}),
    };
  });
  const relationReasons: string[] = [];
  const flag = (names: string[], reason: string) => {
    relationReasons.push(reason);
    for (const field of fields) {
      if (names.includes(field.name)) {
        field.validation = 'invalid';
        field.reasonCodes.push(reason);
      }
    }
  };
  if (params.has('workspaceOrVersion') !== params.has('workspaceOrVersionId'))
    flag(
      ['workspaceOrVersion', 'workspaceOrVersionId'],
      'incomplete-revision-pair',
    );
  if (
    (params.get('workspaceId') && params.get('versionId')) ||
    (params.has('workspaceOrVersion') &&
      (params.get('workspaceId') || params.get('versionId')))
  )
    flag(
      [
        'workspaceId',
        'versionId',
        'workspaceOrVersion',
        'workspaceOrVersionId',
      ],
      'conflicting-revision-parameters',
    );
  return JSON.stringify(
    {
      ...base,
      receivedParameterNames: names
        .slice(0, 64)
        .map((name, index) =>
          (knownNames as readonly string[]).includes(name)
            ? name
            : safeName(name, index),
        ),
      reasonCodes: [
        ...new Set([
          ...fields.flatMap((field) => field.reasonCodes),
          ...relationReasons,
        ]),
      ],
      unexpectedParameterNames: fields
        .filter((field) => !field.expected)
        .map((field) => field.name),
      truncated: new Set([...knownNames, ...names]).size > 64,
      fields,
    },
    null,
    2,
  );
}
