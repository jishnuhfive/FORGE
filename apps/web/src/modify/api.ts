import { object, bounded } from '../cad/api';
import type { OnshapeClientContext } from '../onshape/model';

export const messages = {
  write_disabled: 'Safe CAD editing is disabled in this environment.',
  write_permission_required:
    'Forge needs your permission to modify this document. Reconnect after write access is authorized.',
  reconsent_required:
    'Reconnect your Onshape account before preparing a change.',
  authorization_unknown:
    'Forge could not establish write permission. Reauthorize before trying again.',
  unsupported_target:
    'This model or target could not be verified for the supported edits.',
  model_changed:
    'The model changed since this plan was created. Review fresh model evidence and create a new plan.',
  context_changed:
    'Your account or document context changed. Request a new plan.',
  proposal_expired:
    'This plan expired. Request a new plan from fresh model evidence.',
  proposal_used:
    'This plan was already used. Check its status before requesting another change.',
  proposal_unavailable: 'This plan is unavailable in your current session.',
  proposal_tampered:
    'The preview no longer matches. Discard it and request a new plan.',
  session_expired: 'Sign in again. Your previous approval is no longer valid.',
  permission_or_access_required:
    'Onshape access could not be established. Check your connection and document permissions.',
  rate_limited:
    'Forge needs a short pause before another request. Try again shortly.',
  request_in_progress:
    'Another request is still in progress. Wait for it to finish.',
  workspace_fenced:
    'A previous change requires inspection. Further Forge writes are blocked for this workspace.',
  execution_uncertain: 'Forge could not confirm the final result.',
  recovery_required:
    'Manual recovery required. Forge cannot safely prove the final result. Further writes remain blocked.',
  onshape_unavailable:
    'Forge could not read the model. Request a fresh plan when the connection is available.',
  invalid_request:
    'This response or request could not be verified. Review the model and try again.',
  csrf_failed:
    'This request could not be authorized. Reopen Forge and review a fresh plan.',
  not_configured: 'The Modify planner is not configured in this environment.',
  plan_unavailable:
    'Forge could not produce a verified plan. Rewrite the request more specifically.',
  connection_unavailable:
    'The planning service is unavailable. Try again when the connection is restored.',
  authentication_failed:
    'The planning service could not authenticate. Contact the operator.',
  quota_unavailable:
    'The planning service has no available quota. Try again later.',
  capacity_unavailable: 'The planning service is busy. Try again shortly.',
  timeout:
    'The request took too long. Check your connection before continuing.',
  service_unavailable: 'The service is unavailable. Try again shortly.',
} as const;
export type ErrorCode = keyof typeof messages;
export class ModifyError extends Error {
  constructor(public readonly code: ErrorCode) {
    super(code);
  }
}
export const clarificationMessages = {
  ambiguous_target:
    'More than one feature could match. Name the feature or its position in the tree.',
  unsupported_request:
    'This request is outside the supported edits. Ask to rename, suppress or unsuppress a supported feature, or change an Extrude depth or Fillet radius.',
  missing_value:
    'Include the new name or an explicit quantity with units, such as 30 mm.',
  contradictory_request:
    'The request contains conflicting changes. Specify one final value for each field.',
  no_matching_target:
    'No supported feature matches the request. Check the feature name and position.',
} as const;
const operationTypes = [
  'SET_SUPPRESSED',
  'SET_UNSUPPRESSED',
  'RENAME_FEATURE',
  'SET_EXTRUDE_DEPTH',
  'SET_FILLET_RADIUS',
] as const;
const stages = ['checking', 'executing', 'verifying'] as const;
const outcomes = [
  'verified_success',
  'rejected_stale',
  'write_failed',
  'execution_uncertain',
  'skipped',
] as const;
const operationStates = ['pending', ...stages, ...outcomes] as const;
const executionStates = [
  'verified_success',
  'partial_failure',
  'rejected_stale',
  'write_failed',
  'execution_uncertain',
] as const;
const planStates = [
  'pending',
  'claimed',
  'verifying',
  ...executionStates,
  'cancelled',
  'reconciled_current_state',
] as const;
export type OperationState = (typeof operationStates)[number];
export type PlanState = (typeof planStates)[number];
export interface OperationPreview {
  type: (typeof operationTypes)[number];
  label: string;
  feature_type: 'extrude' | 'fillet';
  position: number;
  field: 'Suppression' | 'Name' | 'Depth' | 'Radius';
  current: string;
  proposed: string;
}
export interface PlanPreview {
  proposal_id: string;
  digest: string;
  expires_at: number;
  operations: OperationPreview[];
}
export interface Choice {
  label: string;
  feature_type: 'extrude' | 'fillet';
  position: number;
}
export type PlannerResponse =
  | { outcome: 'plan'; preview: PlanPreview }
  | {
      outcome: 'clarification';
      reason: keyof typeof clarificationMessages;
      choices: Choice[];
    };
export interface PlanResult {
  state: PlanState;
  operations: OperationState[];
}
export type OperationEvent =
  | {
      type: 'progress';
      operation: number;
      total: number;
      stage: (typeof stages)[number];
    }
  | {
      type: 'operation_result';
      operation: number;
      total: number;
      state: (typeof outcomes)[number];
    };
export type PlanEvent =
  | OperationEvent
  | ({ type: 'result' } & PlanResult)
  | { type: 'error'; code: 'execution_uncertain' };
const member = <T extends string>(
  value: unknown,
  values: readonly T[],
): value is T => typeof value === 'string' && values.includes(value as T);
const text = (value: unknown): value is string =>
  typeof value === 'string' &&
  value.trim().length > 0 &&
  Array.from(value).length <= 256;
const handle = (value: unknown): value is string =>
  typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
function fail(): never {
  throw new ModifyError('invalid_request');
}

function parseOperation(raw: unknown): OperationPreview {
  const v = object(raw, [
    'type',
    'label',
    'feature_type',
    'position',
    'field',
    'current',
    'proposed',
  ]);
  if (
    !member(v.type, operationTypes) ||
    !text(v.label) ||
    !member(v.feature_type, ['extrude', 'fillet']) ||
    !bounded(v.position, 1, 20) ||
    !member(v.field, ['Suppression', 'Name', 'Depth', 'Radius']) ||
    !text(v.current) ||
    !text(v.proposed)
  )
    fail();
  const expectedField =
    v.type === 'RENAME_FEATURE'
      ? 'Name'
      : v.type === 'SET_EXTRUDE_DEPTH'
        ? 'Depth'
        : v.type === 'SET_FILLET_RADIUS'
          ? 'Radius'
          : 'Suppression';
  if (
    v.field !== expectedField ||
    (v.type === 'SET_EXTRUDE_DEPTH' && v.feature_type !== 'extrude') ||
    (['SET_SUPPRESSED', 'SET_UNSUPPRESSED', 'SET_FILLET_RADIUS'].includes(
      String(v.type),
    ) &&
      v.feature_type !== 'fillet')
  )
    fail();
  return v as unknown as OperationPreview;
}
export function parsePreview(raw: unknown): PlanPreview {
  const v = object(raw, ['proposal_id', 'digest', 'expires_at', 'operations']);
  if (
    !handle(v.proposal_id) ||
    typeof v.digest !== 'string' ||
    !/^[a-f0-9]{64}$/.test(v.digest) ||
    !bounded(v.expires_at, 1, 9999999999) ||
    !Array.isArray(v.operations) ||
    v.operations.length < 1 ||
    v.operations.length > 5
  )
    fail();
  return {
    proposal_id: v.proposal_id as string,
    digest: v.digest as string,
    expires_at: v.expires_at as number,
    operations: (v.operations as unknown[]).map(parseOperation),
  };
}
export function parsePlan(raw: unknown): PlannerResponse {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) fail();
  if ((raw as Record<string, unknown>).outcome === 'plan') {
    const v = object(raw, ['outcome', 'preview']);
    return { outcome: 'plan', preview: parsePreview(v.preview) };
  }
  const v = object(raw, ['outcome', 'reason', 'choices']);
  if (
    v.outcome !== 'clarification' ||
    typeof v.reason !== 'string' ||
    !Object.hasOwn(clarificationMessages, v.reason) ||
    !Array.isArray(v.choices) ||
    v.choices.length > 6
  )
    fail();
  const choices = (v.choices as unknown[]).map((raw) => {
    const c = object(raw, ['label', 'feature_type', 'position']);
    if (
      !text(c.label) ||
      !member(c.feature_type, ['extrude', 'fillet']) ||
      !bounded(c.position, 1, 20)
    )
      fail();
    return c as unknown as Choice;
  });
  return {
    outcome: 'clarification',
    reason: v.reason as keyof typeof clarificationMessages,
    choices,
  };
}
export function parseResult(raw: unknown, total: number): PlanResult {
  const v = object(raw, ['state', 'operations']);
  if (
    !member(v.state, planStates) ||
    !bounded(total, 1, 5) ||
    !Array.isArray(v.operations) ||
    v.operations.length !== total ||
    !v.operations.every((s) => member(s, operationStates))
  )
    fail();
  const result = v as unknown as PlanResult;
  const states = result.operations;
  const all = (state: OperationState) => states.every((s) => s === state);
  const stop = states.findIndex((s) => s !== 'verified_success');
  if (
    (result.state === 'verified_success' && !all('verified_success')) ||
    (result.state === 'pending' && !all('pending')) ||
    (result.state === 'cancelled' && !all('skipped'))
  )
    fail();
  if (
    [
      'partial_failure',
      'write_failed',
      'rejected_stale',
      'execution_uncertain',
    ].includes(result.state)
  ) {
    // A1 can retain an all-verified journal with uncertain final persistence.
    if (result.state === 'execution_uncertain' && stop === -1) return result;
    if (stop < 0 || states.slice(stop + 1).some((s) => s !== 'skipped')) fail();
    if (result.state === 'partial_failure') {
      if (stop < 1 || !member(states[stop], ['write_failed', 'rejected_stale']))
        fail();
    } else if (
      states[stop] !== result.state ||
      (result.state !== 'execution_uncertain' && stop !== 0)
    )
      fail();
  }
  if (
    ['claimed', 'verifying'].includes(result.state) &&
    states.some((s) => !member(s, ['pending', ...stages, 'verified_success']))
  )
    fail();
  return result;
}
export function parseEvent(raw: unknown, total: number): PlanEvent {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) fail();
  const type = (raw as Record<string, unknown>).type;
  if (type === 'result') {
    const v = object(raw, ['type', 'state', 'operations']);
    const result = parseResult(
      { state: v.state, operations: v.operations },
      total,
    );
    if (!member(result.state, executionStates)) fail();
    return { type, ...result };
  }
  if (type === 'error') {
    const v = object(raw, ['type', 'code']);
    if (v.code !== 'execution_uncertain') fail();
    return { type, code: 'execution_uncertain' };
  }
  if (type !== 'progress' && type !== 'operation_result') fail();
  const v = object(
    raw,
    type === 'progress'
      ? ['type', 'operation', 'total', 'stage']
      : ['type', 'operation', 'total', 'state'],
  );
  if (
    !bounded(v.operation, 1, total) ||
    v.total !== total ||
    (type === 'progress'
      ? !member(v.stage, stages)
      : !member(v.state, outcomes))
  )
    fail();
  return v as unknown as OperationEvent;
}
function error(raw: unknown): ModifyError {
  return new ModifyError(
    typeof raw === 'string' && Object.hasOwn(messages, raw)
      ? (raw as ErrorCode)
      : 'invalid_request',
  );
}
export function contextBody(context: OnshapeClientContext) {
  if (
    context.revision.kind !== 'workspace' ||
    context.server !== 'https://cad.onshape.com' ||
    ![
      context.documentId,
      context.elementId,
      context.revision.workspaceId,
    ].every((id) => /^[a-f0-9]{24}$/.test(id))
  )
    throw new ModifyError('context_changed');
  return {
    documentId: context.documentId,
    workspaceId: context.revision.workspaceId,
    elementId: context.elementId,
    revisionKind: 'workspace',
  };
}
export async function readJson(response: Response): Promise<unknown> {
  if (
    response.headers.get('content-type')?.split(';')[0] !== 'application/json'
  )
    fail();
  const reader = response.body?.getReader();
  if (!reader) fail();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 65536) fail();
      chunks.push(value);
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  return JSON.parse(
    new TextDecoder('utf-8', { fatal: true }).decode(bytes),
  ) as unknown;
}
async function request(
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
export async function capabilities(
  csrf: string,
  signal: AbortSignal,
): Promise<'available' | ErrorCode> {
  const v = object(await request('capabilities', csrf, signal), ['state']);
  if (v.state === 'available') return 'available';
  throw error(v.state);
}
export async function createPlan(
  context: OnshapeClientContext,
  text: string,
  csrf: string,
  signal: AbortSignal,
): Promise<PlannerResponse> {
  return parsePlan(
    await request('plan', csrf, signal, {
      context: contextBody(context),
      request: text,
    }),
  );
}
export async function cancelPlan(
  preview: PlanPreview,
  csrf: string,
  signal: AbortSignal,
): Promise<PlanResult> {
  const result = parseResult(
    await request('plans/' + preview.proposal_id + '/cancel', csrf, signal, {}),
    preview.operations.length,
  );
  if (result.state !== 'cancelled') fail();
  return result;
}
export async function planStatus(
  preview: PlanPreview,
  csrf: string,
  signal: AbortSignal,
): Promise<PlanResult> {
  return parseResult(
    await request('plans/' + preview.proposal_id, csrf, signal),
    preview.operations.length,
  );
}
export async function approve(
  preview: PlanPreview,
  csrf: string,
  signal: AbortSignal,
  progress: (event: OperationEvent) => void,
): Promise<PlanResult> {
  let response: Response;
  try {
    response = await fetch(
      '/api/modify/plans/' + preview.proposal_id + '/approve',
      {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
        signal,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ digest: preview.digest }),
      },
    );
  } catch {
    throw new ModifyError('execution_uncertain');
  }
  if (!response.ok) {
    try {
      const data = await readJson(response);
      throw error((data as { detail?: unknown })?.detail);
    } catch (cause) {
      throw cause instanceof ModifyError
        ? cause
        : new ModifyError('execution_uncertain');
    }
  }
  const reader = response.body?.getReader();
  if (!reader) throw new ModifyError('execution_uncertain');
  let buffer = new Uint8Array(0);
  let size = 0;
  let count = 0;
  let result: PlanResult | undefined;
  let operation = 1;
  let lastStage = -1;
  const observed: OperationState[] = [];
  try {
    if (
      response.headers.get('content-type')?.split(';')[0] !==
      'application/x-ndjson'
    )
      fail();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 8192) fail();
      const joined = new Uint8Array(buffer.length + value.length);
      joined.set(buffer);
      joined.set(value, buffer.length);
      buffer = joined;
      let newline: number;
      while ((newline = buffer.indexOf(10)) !== -1) {
        if (newline + 1 > 512 || ++count > 21 || result) fail();
        const event = parseEvent(
          JSON.parse(
            new TextDecoder('utf-8', { fatal: true }).decode(
              buffer.subarray(0, newline),
            ),
          ),
          preview.operations.length,
        );
        buffer = buffer.slice(newline + 1);
        if (event.type === 'error')
          throw new ModifyError('execution_uncertain');
        if (event.type === 'result') {
          if (observed.some((state, i) => state !== event.operations[i]))
            fail();
          result = { state: event.state, operations: event.operations };
        } else {
          if (event.operation !== operation) fail();
          if (event.type === 'progress') {
            const stage = stages.indexOf(event.stage);
            if (stage <= lastStage) fail();
            lastStage = stage;
          } else {
            observed.push(event.state);
            operation++;
            lastStage = -1;
          }
          progress(event);
        }
      }
      if (buffer.length >= 512) fail();
    }
    if (buffer.length || !result) fail();
    return result;
  } catch {
    throw new ModifyError('execution_uncertain');
  } finally {
    await reader.cancel().catch(() => {});
  }
}

export type Recovery =
  | { state: 'none' }
  | {
      state:
        'execution_uncertain' | 'claimed' | 'verifying' | 'recovery_required';
      plan: string | null;
      operations: OperationPreview[];
      operation_states: OperationState[];
      reconciliation: 'available' | 'manual_required';
    };
export function parseRecovery(raw: unknown): Recovery {
  if ((raw as { state?: unknown } | null)?.state === 'none') {
    object(raw, ['state']);
    return { state: 'none' };
  }
  const v = object(raw, [
    'state',
    'plan',
    'operations',
    'operation_states',
    'reconciliation',
  ]);
  if (
    !member(v.state, [
      'execution_uncertain',
      'claimed',
      'verifying',
      'recovery_required',
    ]) ||
    (v.plan !== null && !handle(v.plan)) ||
    !Array.isArray(v.operations) ||
    v.operations.length > 5 ||
    !Array.isArray(v.operation_states) ||
    v.operation_states.length !== v.operations.length ||
    !v.operation_states.every((s) => member(s, operationStates)) ||
    !member(v.reconciliation, ['available', 'manual_required']) ||
    (v.reconciliation === 'available' &&
      (v.state !== 'execution_uncertain' ||
        !handle(v.plan) ||
        v.operations.length !== 1))
  )
    fail();
  return {
    ...v,
    operations: (v.operations as unknown[]).map(parseOperation),
  } as Recovery;
}
export async function recovery(
  context: OnshapeClientContext,
  csrf: string,
  signal: AbortSignal,
): Promise<Recovery> {
  return parseRecovery(
    await request('recovery', csrf, signal, { context: contextBody(context) }),
  );
}
export async function reconcile(
  plan: string,
  total: number,
  csrf: string,
  signal: AbortSignal,
): Promise<PlanResult> {
  if (!handle(plan)) fail();
  const result = parseResult(
    await request('plans/' + plan + '/reconcile', csrf, signal, {}),
    total,
  );
  if (result.state !== 'reconciled_current_state') fail();
  return result;
}
