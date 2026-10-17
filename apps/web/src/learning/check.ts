import { bounded, object } from '../cad/api';
import type { OnshapeClientContext } from '../onshape/model';

export type Status = 'PASS' | 'FAIL' | 'WARNING' | 'UNVERIFIED';
export type StepOutcome = 'verified' | 'not_met' | 'unverified';
const statuses: readonly Status[] = ['PASS', 'FAIL', 'WARNING', 'UNVERIFIED'];
const outcomes: readonly StepOutcome[] = ['verified', 'not_met', 'unverified'];
const reasons = [
  'met',
  'met_by_alternative',
  'missing',
  'suppressed',
  'evidence_unavailable',
  'evidence_incomplete',
  'evidence_stale',
  'not_observable',
  'ambiguous_signal',
  'constraint_not_met',
] as const;

export interface RequirementResult {
  requirement_id: string;
  description: string;
  blocking: boolean;
  evidence: string[];
  outcome: { status: Status; reason: string; finding: string };
}
export interface StepCheck {
  lesson_id: 'mounting-bracket';
  step_id: string;
  outcome: StepOutcome;
  results: RequirementResult[];
  captured_at: string;
  consistency: 'unverified' | 'mismatch';
}
// Public, fixed wording. Raw status codes and server text are never rendered.
export const checkErrors = {
  not_signed_in: 'Sign in with Onshape to check your model.',
  no_context: 'Open this lesson inside a Part Studio in Onshape to check it.',
  no_access:
    'Forge needs permission to read this document. Check your Onshape connection.',
  running: 'A check is already running. Please wait a moment.',
  cooldown: 'Forge can check again shortly.',
  unavailable:
    'Forge couldn’t read your model right now. Your model has not been changed.',
  invalid: 'Forge couldn’t verify that response. Try checking again.',
} as const;
export type CheckErrorCode = keyof typeof checkErrors;
export class CheckError extends Error {
  constructor(
    public readonly code: CheckErrorCode,
    public readonly retryAfter = 5,
  ) {
    super(code);
  }
}
function text(value: unknown, max: number): value is string {
  return typeof value === 'string' && value.length <= max;
}
export function parseCheck(value: unknown): StepCheck {
  const fail = () => new CheckError('invalid');
  let data: Record<string, unknown>;
  try {
    data = object(value, [
      'lesson_id',
      'step_id',
      'outcome',
      'results',
      'captured_at',
      'consistency',
    ]);
  } catch {
    throw fail();
  }
  if (
    data.lesson_id !== 'mounting-bracket' ||
    !text(data.step_id, 64) ||
    !outcomes.includes(data.outcome as StepOutcome) ||
    !text(data.captured_at, 40) ||
    !/^\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|\+00:00)$/.test(data.captured_at) ||
    !['unverified', 'mismatch'].includes(data.consistency as string) ||
    !Array.isArray(data.results) ||
    data.results.length < 1 ||
    data.results.length > 8
  )
    throw fail();
  for (const raw of data.results) {
    try {
      const item = object(raw, [
        'requirement_id',
        'description',
        'blocking',
        'evidence',
        'outcome',
      ]);
      const outcome = object(item.outcome, ['status', 'reason', 'finding']);
      if (
        !text(item.requirement_id, 64) ||
        !text(item.description, 200) ||
        typeof item.blocking !== 'boolean' ||
        !Array.isArray(item.evidence) ||
        item.evidence.length > 8 ||
        !item.evidence.every((e) => text(e, 64)) ||
        !statuses.includes(outcome.status as Status) ||
        !(reasons as readonly unknown[]).includes(outcome.reason) ||
        !text(outcome.finding, 300) ||
        !outcome.finding.trim()
      )
        throw fail();
    } catch {
      throw fail();
    }
  }
  return data as unknown as StepCheck;
}

export async function checkStep(
  context: OnshapeClientContext | null,
  csrf: string | null,
  stepId: string,
  signal: AbortSignal,
): Promise<StepCheck> {
  if (!csrf) throw new CheckError('not_signed_in');
  if (
    !context ||
    context.revision.kind !== 'workspace' ||
    context.server !== 'https://cad.onshape.com' ||
    (context.elementType && context.elementType !== 'partStudio')
  )
    throw new CheckError('no_context');
  const response = await fetch('/api/learning/check-step', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify({
      lesson_id: 'mounting-bracket',
      step_id: stepId,
      context: {
        documentId: context.documentId,
        workspaceId: context.revision.workspaceId,
        elementId: context.elementId,
        revisionKind: 'workspace',
      },
    }),
  });
  if (!response.ok) {
    let retry = 5;
    try {
      const body: unknown = await response.json();
      const seconds = (body as { retry_after_seconds?: unknown })
        .retry_after_seconds;
      if (bounded(seconds, 1, 86400)) retry = seconds as number;
    } catch {
      // A non-JSON failure carries nothing worth showing.
    }
    if (response.status === 401) throw new CheckError('not_signed_in');
    if (response.status === 403) throw new CheckError('no_access');
    if (response.status === 409) throw new CheckError('running', retry);
    if (response.status === 429) throw new CheckError('cooldown', retry);
    throw new CheckError('unavailable');
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new CheckError('invalid');
  }
  return parseCheck(body);
}
