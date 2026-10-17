import { object, bounded } from '../cad/api';
import type { OnshapeClientContext } from '../onshape/model';

export const messages = {
  write_disabled: 'Safe CAD editing is disabled in this environment.',
  write_permission_required:
    'Forge needs your permission before it can modify this Onshape document. Reconnect after the operator authorizes write access.',
  reconsent_required:
    'Reconnect your Onshape account before preparing a change.',
  authorization_unknown:
    'Forge could not establish write permission. Reauthorize before trying again.',
  unsupported_edit:
    'Forge supports only suppressing the final ordinary Fillet. Other CAD edits are not supported.',
  unsupported_target:
    'No eligible terminal Fillet could be verified. Unknown or unsupported model details prevent this edit.',
  ambiguous_target:
    'The target is ambiguous. Review the feature list and choose one supported target.',
  model_changed:
    'The model changed since this proposal was created. Review the updated model and create a new proposal.',
  context_changed:
    'Your account or document context changed. Request a new proposal.',
  proposal_expired:
    'This proposal expired. Request a new proposal from fresh model evidence.',
  proposal_used:
    'This proposal was already used. Check its status before requesting another change.',
  proposal_unavailable: 'This proposal is unavailable in your current session.',
  proposal_tampered:
    'The preview no longer matches. Discard it and request a new proposal.',
  session_expired: 'Sign in again. Your previous approval is no longer valid.',
  permission_or_access_required:
    'Onshape access could not be established. Check your connection and document permissions.',
  rate_limited:
    'Forge can prepare another change shortly. Wait before trying again.',
  workspace_fenced:
    'A previous change requires inspection. Further Forge writes are blocked for this workspace.',
  execution_uncertain:
    'The change may have occurred. Inspect Onshape history and feature state before another change. Forge will not retry the write.',
  recovery_required:
    'Inspect the feature in Onshape. The workspace remains blocked until deliberate operator recovery.',
  onshape_unavailable:
    'Forge could not read the model. Request a fresh proposal when the connection is available.',
  invalid_request:
    'This request could not be verified. Review the model and try again.',
  csrf_failed:
    'This request could not be authorized. Reopen Forge and review a fresh proposal.',
} as const;
export type ErrorCode = keyof typeof messages;
export class ModifyError extends Error {
  constructor(public readonly code: ErrorCode) {
    super(code);
  }
}
export interface Candidate {
  handle: string;
  label: string;
  position: number;
  expires_at: number;
}
export interface Proposal {
  proposal_id: string;
  digest: string;
  operation_type: 'suppress_terminal_fillet_v1';
  label: string;
  position: number;
  current: 'Active';
  proposed: 'Suppressed';
  expires_at: number;
}
const handle = (value: unknown): value is string =>
  typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
const label = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0 && value.length <= 256;
export function parseCandidate(raw: unknown): Candidate {
  const v = object(raw, ['handle', 'label', 'position', 'expires_at']);
  if (
    !handle(v.handle) ||
    !label(v.label) ||
    !bounded(v.position, 1, 20) ||
    !bounded(v.expires_at, 1, 9999999999)
  )
    throw new ModifyError('invalid_request');
  return v as unknown as Candidate;
}
export function parseProposal(raw: unknown): Proposal {
  const v = object(raw, [
    'proposal_id',
    'digest',
    'operation_type',
    'label',
    'position',
    'current',
    'proposed',
    'expires_at',
  ]);
  if (
    !handle(v.proposal_id) ||
    typeof v.digest !== 'string' ||
    !/^[a-f0-9]{64}$/.test(v.digest) ||
    v.operation_type !== 'suppress_terminal_fillet_v1' ||
    !label(v.label) ||
    !bounded(v.position, 1, 20) ||
    v.current !== 'Active' ||
    v.proposed !== 'Suppressed' ||
    !bounded(v.expires_at, 1, 9999999999)
  )
    throw new ModifyError('invalid_request');
  return v as unknown as Proposal;
}
function error(value: unknown): ModifyError {
  const code =
    typeof value === 'string' && Object.hasOwn(messages, value)
      ? (value as ErrorCode)
      : 'invalid_request';
  return new ModifyError(code);
}
export function contextBody(context: OnshapeClientContext) {
  if (
    context.revision.kind !== 'workspace' ||
    context.server !== 'https://cad.onshape.com'
  )
    throw new ModifyError('context_changed');
  return {
    documentId: context.documentId,
    workspaceId: context.revision.workspaceId,
    elementId: context.elementId,
    revisionKind: 'workspace',
  };
}
export async function call(
  path: string,
  csrf: string,
  signal: AbortSignal,
  body?: object,
): Promise<unknown> {
  const response = await fetch('/api/modify/' + path, {
    method: body ? 'POST' : 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await readJson(response);
  if (!response.ok) throw error((data as { detail?: unknown })?.detail);
  return data;
}
async function readJson(response: Response): Promise<unknown> {
  const reader = response.body?.getReader();
  if (!reader) throw error(null);
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 65536) throw error(null);
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const c of chunks) {
    bytes.set(c, offset);
    offset += c.length;
  }
  let data: unknown;
  try {
    data = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    throw error(null);
  }
  return data;
}
export async function approve(
  proposal: Proposal,
  csrf: string,
  signal: AbortSignal,
  progress: (stage: string) => void,
): Promise<string> {
  const response = await fetch(
    '/api/modify/proposals/' + proposal.proposal_id + '/approve',
    {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
      signal,
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ digest: proposal.digest }),
    },
  );
  if (!response.ok) {
    let data: unknown;
    try {
      data = await readJson(response);
    } catch {
      throw new ModifyError('execution_uncertain');
    }
    const code = (data as { detail?: unknown })?.detail;
    if (typeof code !== 'string' || !Object.hasOwn(messages, code))
      throw new ModifyError('execution_uncertain');
    throw error(code);
  }
  const reader = response.body?.getReader();
  if (!reader) throw new ModifyError('execution_uncertain');
  let buffer = '';
  let size = 0;
  let count = 0;
  let result: string | undefined;
  let verifiedStage = false;
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 8192) throw new ModifyError('execution_uncertain');
      buffer += decoder.decode(value, { stream: true });
      let n: number;
      while ((n = buffer.indexOf('\n')) >= 0) {
        if (++count > 5) throw new ModifyError('execution_uncertain');
        const parsed = JSON.parse(buffer.slice(0, n)) as Record<
          string,
          unknown
        >;
        const event = object(
          parsed,
          parsed.type === 'progress'
            ? ['type', 'stage']
            : parsed.type === 'result'
              ? ['type', 'state']
              : ['type', 'code'],
        );
        if (result) throw new ModifyError('execution_uncertain');
        buffer = buffer.slice(n + 1);
        if (
          event.type === 'progress' &&
          ['checking', 'conformance_wait', 'executing', 'verifying'].includes(
            String(event.stage),
          )
        ) {
          verifiedStage ||= event.stage === 'verifying';
          progress(String(event.stage));
        } else if (event.type === 'error') throw error(event.code);
        else if (
          event.type === 'result' &&
          typeof event.state === 'string' &&
          [
            'verified_success',
            'execution_uncertain',
            'unverified_result',
            'recovery_required',
          ].includes(event.state)
        ) {
          if (event.state === 'verified_success' && !verifiedStage)
            throw new ModifyError('execution_uncertain');
          result = event.state;
        } else throw new ModifyError('execution_uncertain');
      }
    }
  } finally {
    await reader.cancel();
  }
  if (buffer.trim() || !result) throw new ModifyError('execution_uncertain');
  return result;
}
