// The only module that knows creation endpoint paths and wire shapes. The browser
// never builds, signs or executes CAD operations: it submits text, displays the
// server's validated brief and plan, and relays the human's confirmed approval.
import { object, bounded } from '../cad/api';
import {
  ModifyError,
  contextBody,
  messages,
  readJson,
  type ErrorCode,
  type OperationState,
} from '../modify/api';
import type { OnshapeClientContext } from '../onshape/model';

export const BASE = '/api/create/';

export const intentKeys = [
  'define_base_profile',
  'form_base_body',
  'define_cut_profile',
  'remove_material',
] as const;
export type IntentKey = (typeof intentKeys)[number];

export const clarifyFields = [
  'object_kind',
  'units',
  'width',
  'length',
  'thickness',
  'hole_count',
  'hole_diameter',
  'hole_position',
] as const;
const unsupportedReasons = [
  'unsupported_object',
  'unsupported_feature',
  'not_a_creation_request',
] as const;
export const rejectionCodes = [
  'invalid_model_output',
  'hole_outside_plate',
  'insufficient_wall',
  'holes_overlap',
  'hole_too_small',
] as const;

export interface Length {
  value: number;
  unit: 'mm' | 'cm' | 'm' | 'in';
}
export interface Hole {
  diameter: Length;
  center_x: Length;
  center_y: Length;
}
export interface Brief {
  kind: 'rect_plate_with_through_holes';
  width: Length;
  length: Length;
  thickness: Length;
  holes: Hole[];
}
export interface PlanStep {
  id: string;
  intent: IntentKey;
  operation: string;
  /** Human-readable geometry derived from the server's plan, in millimetres. */
  detail: string;
}
export interface Explanation {
  step_id: string;
  intent: IntentKey;
  text: string;
}
export interface CreationProposal {
  proposal_id: string;
  expires_at: number;
  brief: Brief;
  digest: string;
  steps: PlanStep[];
  explanations: Explanation[];
}
export type CreationResponse =
  | ({ status: 'ready' } & CreationProposal)
  | {
      status: 'needs_clarification';
      reason: 'missing_dimension' | 'ambiguous_intent';
      fields: (typeof clarifyFields)[number][];
      questions: string[];
    }
  | { status: 'unsupported'; reason: string; message: string }
  | { status: 'rejected'; code: (typeof rejectionCodes)[number] };

export type CreationState =
  | 'pending'
  | 'claimed'
  | 'verifying'
  | 'verified_success'
  | 'partial_failure'
  | 'write_failed'
  | 'rejected_stale'
  | 'execution_uncertain';
const creationStates: readonly CreationState[] = [
  'pending',
  'claimed',
  'verifying',
  'verified_success',
  'partial_failure',
  'write_failed',
  'rejected_stale',
  'execution_uncertain',
];
const stepStates: readonly OperationState[] = [
  'pending',
  'checking',
  'executing',
  'verifying',
  'verified_success',
  'rejected_stale',
  'write_failed',
  'execution_uncertain',
  'skipped',
];
export interface CreationResult {
  state: CreationState;
  steps: OperationState[];
}

export const rejectionMessages: Record<
  (typeof rejectionCodes)[number],
  string
> = {
  invalid_model_output:
    'Forge could not turn that into a buildable design. Rewrite the request with explicit dimensions and units.',
  hole_outside_plate: 'A hole would extend past the edge of the plate.',
  insufficient_wall:
    'A hole would leave less than 2 mm of material to the edge or to another hole.',
  holes_overlap: 'Two holes would overlap.',
  hole_too_small: 'A hole is smaller than the 1 mm minimum diameter.',
};
export const clarifyLabels: Record<(typeof clarifyFields)[number], string> = {
  object_kind: 'Part type',
  units: 'Units',
  width: 'Width',
  length: 'Length (depth)',
  thickness: 'Thickness',
  hole_count: 'Number of holes',
  hole_diameter: 'Hole diameter',
  hole_position: 'Hole position',
};

function fail(): never {
  throw new ModifyError('invalid_request');
}
const member = <T extends string>(
  value: unknown,
  values: readonly T[],
): value is T => typeof value === 'string' && values.includes(value as T);
const handle = (value: unknown): value is string =>
  typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
const shortText = (value: unknown): value is string =>
  typeof value === 'string' &&
  value.trim().length > 0 &&
  Array.from(value).length <= 256;
const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

function length(raw: unknown, signed: boolean): Length {
  const v = object(raw, ['value', 'unit']);
  if (
    !finite(v.value) ||
    (!signed && v.value <= 0) ||
    Math.abs(v.value) > 2_000_000 ||
    !member(v.unit, ['mm', 'cm', 'm', 'in'])
  )
    fail();
  return { value: v.value, unit: v.unit };
}
function brief(raw: unknown): Brief {
  const v = object(raw, ['kind', 'width', 'length', 'thickness', 'holes']);
  if (
    v.kind !== 'rect_plate_with_through_holes' ||
    !Array.isArray(v.holes) ||
    v.holes.length > 4
  )
    fail();
  return {
    kind: v.kind,
    width: length(v.width, false),
    length: length(v.length, false),
    thickness: length(v.thickness, false),
    holes: (v.holes as unknown[]).map((h) => {
      const hole = object(h, ['diameter', 'center_x', 'center_y']);
      return {
        diameter: length(hole.diameter, false),
        center_x: length(hole.center_x, true),
        center_y: length(hole.center_y, true),
      };
    }),
  };
}

export function mm(um: number): string {
  return `${Number((um / 1000).toFixed(3))} mm`;
}
function um(value: unknown, signed = false): number {
  if (!bounded(value, signed ? -2_000_000 : 1, 2_000_000)) fail();
  return value as number;
}
function target(raw: unknown): string {
  if (!raw || typeof raw !== 'object') fail();
  const kind = (raw as { kind?: unknown }).kind;
  if (kind === 'base_plane') {
    const v = object(raw, ['kind', 'plane']);
    if (!member(v.plane, ['TOP', 'FRONT', 'RIGHT'])) fail();
    return `${v.plane} plane`;
  }
  const v = object(raw, ['kind', 'step', 'face']);
  if (
    kind !== 'step_face' ||
    typeof v.step !== 'string' ||
    !member(v.face, ['start_cap', 'end_cap'])
  )
    fail();
  return v.face === 'end_cap' ? 'top face of the body' : 'bottom face of body';
}
function extent(raw: unknown): string {
  if ((raw as { kind?: unknown } | null)?.kind === 'through_all') {
    object(raw, ['kind']);
    return 'through all';
  }
  const v = object(raw, ['kind', 'depth_um']);
  if (v.kind !== 'blind') fail();
  return `${mm(um(v.depth_um))} deep`;
}
const stepId = (value: unknown): value is string =>
  typeof value === 'string' && /^s[0-9]{2,3}$/.test(value);
function step(raw: unknown): PlanStep {
  const v = object(raw, ['id', 'intent', 'depends_on', 'op']);
  if (
    !stepId(v.id) ||
    !member(v.intent, intentKeys) ||
    !Array.isArray(v.depends_on) ||
    !v.depends_on.every(stepId) ||
    !v.op ||
    typeof v.op !== 'object'
  )
    fail();
  const operation = (v.op as { operation?: unknown }).operation;
  let detail: string;
  let expected: IntentKey;
  switch (operation) {
    case 'CREATE_SKETCH_RECT': {
      const op = object(v.op, [
        'operation',
        'target',
        'center_x_um',
        'center_y_um',
        'width_um',
        'height_um',
      ]);
      um(op.center_x_um, true);
      um(op.center_y_um, true);
      detail = `${mm(um(op.width_um))} × ${mm(um(op.height_um))} rectangle, centered on the ${target(op.target)}`;
      expected = 'define_base_profile';
      break;
    }
    case 'CREATE_SKETCH_CIRCLE': {
      const op = object(v.op, [
        'operation',
        'target',
        'center_x_um',
        'center_y_um',
        'diameter_um',
      ]);
      detail = `Ø ${mm(um(op.diameter_um))} circle at X ${mm(um(op.center_x_um, true))}, Y ${mm(um(op.center_y_um, true))} on the ${target(op.target)}`;
      expected = 'define_cut_profile';
      break;
    }
    case 'EXTRUDE_NEW': {
      const op = object(v.op, ['operation', 'profile', 'extent']);
      if (!stepId(op.profile)) fail();
      detail = `Extrude ${extent(op.extent)} as a new body`;
      expected = 'form_base_body';
      break;
    }
    case 'EXTRUDE_REMOVE': {
      const op = object(v.op, [
        'operation',
        'profile',
        'target_body',
        'extent',
      ]);
      if (!stepId(op.profile) || !stepId(op.target_body)) fail();
      detail = `Cut ${extent(op.extent)} from the body`;
      expected = 'remove_material';
      break;
    }
    default:
      return fail();
  }
  if (v.intent !== expected) fail();
  return { id: v.id, intent: v.intent, operation: operation as string, detail };
}
function proposal(raw: Record<string, unknown>): CreationProposal {
  const plan = object(raw.plan, ['capability', 'digest', 'steps']);
  if (
    !handle(raw.proposal_id) ||
    !bounded(raw.expires_at, 1, 9999999999) ||
    plan.capability !== 'rect_plate_with_through_holes' ||
    typeof plan.digest !== 'string' ||
    !/^[a-f0-9]{64}$/.test(plan.digest) ||
    !Array.isArray(plan.steps) ||
    plan.steps.length < 2 ||
    plan.steps.length > 10 ||
    !Array.isArray(raw.explanations)
  )
    fail();
  const steps = (plan.steps as unknown[]).map(step);
  if (
    new Set(steps.map((s) => s.id)).size !== steps.length ||
    (raw.explanations as unknown[]).length !== steps.length
  )
    fail();
  const explanations = (raw.explanations as unknown[]).map((e, i) => {
    const x = object(e, [
      'step_id',
      'intent',
      'rationale_key',
      'text',
      'authority',
    ]);
    // Learn text is read-only, server-owned, and must line up with the plan.
    if (
      x.step_id !== steps[i]?.id ||
      x.intent !== steps[i]?.intent ||
      x.rationale_key !== `creation.rationale.${steps[i]?.intent}` ||
      x.authority !== 'none' ||
      !shortText(x.text)
    )
      fail();
    return {
      step_id: x.step_id as string,
      intent: x.intent as IntentKey,
      text: x.text as string,
    };
  });
  return {
    proposal_id: raw.proposal_id as string,
    expires_at: raw.expires_at as number,
    brief: brief(raw.brief),
    digest: plan.digest,
    steps,
    explanations,
  };
}
export function parseCreation(raw: unknown): CreationResponse {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) fail();
  const status = (raw as { status?: unknown }).status;
  if (status === 'ready') {
    object(raw, [
      'status',
      'proposal_id',
      'expires_at',
      'brief',
      'plan',
      'explanations',
    ]);
    return { status, ...proposal(raw as Record<string, unknown>) };
  }
  if (status === 'needs_clarification') {
    const v = object(raw, ['status', 'reason', 'fields', 'questions']);
    if (
      !member(v.reason, ['missing_dimension', 'ambiguous_intent']) ||
      !Array.isArray(v.fields) ||
      v.fields.length < 1 ||
      v.fields.length > 8 ||
      !v.fields.every((f) => member(f, clarifyFields)) ||
      !Array.isArray(v.questions) ||
      v.questions.length !== v.fields.length ||
      !v.questions.every(shortText)
    )
      fail();
    return {
      status,
      reason: v.reason,
      fields: v.fields as (typeof clarifyFields)[number][],
      questions: v.questions as string[],
    };
  }
  if (status === 'unsupported') {
    const v = object(raw, ['status', 'reason', 'message']);
    if (!member(v.reason, unsupportedReasons) || !shortText(v.message)) fail();
    return { status, reason: v.reason, message: v.message };
  }
  if (status === 'rejected') {
    const v = object(raw, ['status', 'code']);
    if (!member(v.code, rejectionCodes)) fail();
    return { status, code: v.code };
  }
  return fail();
}
export function parseCreationResult(
  raw: unknown,
  total: number,
): CreationResult {
  const v = object(raw, ['state', 'steps']);
  if (
    !member(v.state, creationStates) ||
    !Array.isArray(v.steps) ||
    v.steps.length !== total ||
    !v.steps.every((s) => member(s, stepStates))
  )
    fail();
  const steps = v.steps as OperationState[];
  // Success is only ever the conjunction of every verified step.
  if (
    (v.state === 'verified_success') !==
    steps.every((s) => s === 'verified_success')
  )
    fail();
  if (v.state === 'pending' && !steps.every((s) => s === 'pending')) fail();
  return { state: v.state, steps };
}

function failure(raw: unknown): ModifyError {
  return new ModifyError(
    typeof raw === 'string' && Object.hasOwn(messages, raw)
      ? (raw as ErrorCode)
      : 'invalid_request',
  );
}
async function send(
  path: string,
  csrf: string,
  signal: AbortSignal,
  body?: object,
): Promise<unknown> {
  const response = await fetch(BASE + path, {
    method: body ? 'POST' : 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await readJson(response);
  if (!response.ok) throw failure((data as { detail?: unknown })?.detail);
  return data;
}

export async function requestCreation(
  context: OnshapeClientContext,
  text: string,
  csrf: string,
  signal: AbortSignal,
): Promise<CreationResponse> {
  return parseCreation(
    await send('plan', csrf, signal, {
      context: contextBody(context),
      request: text,
    }),
  );
}
/** Approval is bound to the exact plan digest and to the human's brief review. */
export async function approveCreation(
  proposal: CreationProposal,
  csrf: string,
  signal: AbortSignal,
): Promise<CreationResult> {
  try {
    return parseCreationResult(
      await send('plans/' + proposal.proposal_id + '/approve', csrf, signal, {
        digest: proposal.digest,
        brief_confirmed: true,
      }),
      proposal.steps.length,
    );
  } catch (cause) {
    // Anything after dispatch that is not a clean refusal is unproven.
    throw cause instanceof ModifyError && cause.code !== 'invalid_request'
      ? cause
      : new ModifyError('execution_uncertain');
  }
}
export async function creationStatus(
  proposal: CreationProposal,
  csrf: string,
  signal: AbortSignal,
): Promise<CreationResult> {
  return parseCreationResult(
    await send('plans/' + proposal.proposal_id, csrf, signal),
    proposal.steps.length,
  );
}
