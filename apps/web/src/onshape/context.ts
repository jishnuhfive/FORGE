import { ONSHAPE_ORIGINS } from './policy';
import { standaloneState } from './model';
import type { ClientState, OnshapeClientContext } from './model';

const identifier = /^[a-f0-9]{24}$/;
// Observed ancillary fields, never context, identity, origins or UI preferences.
// Their provider-specific syntax is opaque; validate bounds then discard them.
export const OPAQUE_LAUNCH_METADATA = [
  'clientId',
  'sessionCompanyId',
  'theme',
] as const;
export function validOpaqueLaunchMetadata(value: string): boolean {
  return (
    value.length > 0 &&
    value.length <= 128 &&
    !Array.from(value).some(
      (character) =>
        character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127,
    )
  );
}
const fields = new Set([
  'documentId',
  'elementId',
  'workspaceId',
  'versionId',
  'workspaceOrVersion',
  'workspaceOrVersionId',
  'microversionId',
  'server',
  // Known ancillary launch fields: validate then discard unused metadata.
  'companyId',
  'userId',
  'locale',
  ...OPAQUE_LAUNCH_METADATA,
]);
export function approvedOrigin(value: string): string | null {
  if (value.length > 256 || value.trim() !== value || /[\\\s]/.test(value))
    return null;
  try {
    const url = new URL(value);
    if (
      url.protocol !== 'https:' ||
      url.username ||
      url.password ||
      (url.pathname !== '/' && url.pathname !== '') ||
      url.search ||
      url.hash ||
      url.port
    )
      return null;
    return ONSHAPE_ORIGINS.includes(url.origin) ? url.origin : null;
  } catch {
    return null;
  }
}
export function parseLaunch(
  search: string,
  embedded: boolean,
  extension: boolean,
): ClientState {
  if (!embedded) return standaloneState;
  const fail = (
    issue: ClientState['issue'],
    status: ClientState['status'] = 'EMBEDDED_CONTEXT_ERROR',
  ): ClientState => ({
    status,
    context: null,
    selection: { status: 'waiting', entities: [] },
    issue,
  });
  if (!extension) return fail('invalid-context');
  if (search.length > 4096) return fail('invalid-context');
  const params = new URLSearchParams(search);
  for (const [key, value] of params) {
    if (
      !fields.has(key) ||
      params.getAll(key).length !== 1 ||
      value.length > 256 ||
      Array.from(value).some(
        (character) =>
          character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127,
      )
    )
      return fail('invalid-context');
  }
  const serverValue = params.get('server');
  const server = serverValue === null ? null : approvedOrigin(serverValue);
  if (serverValue !== null && !server)
    return fail('untrusted-server', 'UNTRUSTED_ORIGIN');
  for (const key of [
    'documentId',
    'elementId',
    'workspaceId',
    'versionId',
    'workspaceOrVersionId',
    'microversionId',
    'userId',
  ]) {
    const value = params.get(key);
    if (value !== null && !identifier.test(value))
      return fail('invalid-context');
  }
  for (const field of OPAQUE_LAUNCH_METADATA) {
    const value = params.get(field);
    if (value !== null && !validOpaqueLaunchMetadata(value))
      return fail('invalid-context');
  }
  const company = params.get('companyId');
  if (company !== null && company !== 'cad' && !identifier.test(company))
    return fail('invalid-context');
  const locale = params.get('locale');
  if (
    locale !== null &&
    !/^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8}){0,3}$/.test(locale)
  )
    return fail('invalid-context');
  const kind = params.get('workspaceOrVersion');
  const id = params.get('workspaceOrVersionId');
  if (
    (kind !== null && kind !== 'w' && kind !== 'v') ||
    (kind === null) !== (id === null)
  )
    return fail('invalid-context');
  const workspaceId = params.get('workspaceId');
  const versionId = params.get('versionId');
  if (
    (workspaceId && versionId) ||
    (kind !== null && (workspaceId || versionId))
  )
    return fail('invalid-context');
  const revision: OnshapeClientContext['revision'] | null =
    kind === 'w' && id
      ? { kind: 'workspace', workspaceId: id }
      : kind === 'v' && id
        ? { kind: 'version', versionId: id }
        : workspaceId
          ? { kind: 'workspace', workspaceId }
          : versionId
            ? { kind: 'version', versionId }
            : null;
  const documentId = params.get('documentId');
  const elementId = params.get('elementId');
  if (!server || !documentId || !elementId || !revision) {
    return {
      status: 'EMBEDDED_INITIALIZING',
      context: null,
      selection: { status: 'waiting', entities: [] },
    };
  }
  const microversionId = params.get('microversionId');
  return {
    status: 'EMBEDDED_INITIALIZING',
    context: {
      documentId,
      elementId,
      revision,
      server,
      ...(microversionId ? { microversionId } : {}),
    },
    selection: { status: 'waiting', entities: [] },
  };
}
