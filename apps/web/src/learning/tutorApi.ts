import { bounded, object } from '../cad/api';
import type { OnshapeClientContext } from '../onshape/model';
import type { Experience, LearningGoal } from './lesson';

// Fixed public copy. Raw server or provider text is never rendered.
export const tutorMessages = {
  not_configured: 'Ask Forge isn’t set up on this server.',
  connection_unavailable: 'Ask Forge couldn’t answer right now. Try again.',
  authentication_failed: 'Ask Forge needs administrator attention.',
  rate_limited:
    'You’ve asked a lot of questions. Please wait a bit before asking again.',
  quota_unavailable: 'The AI service is busy. Try again in a moment.',
  capacity_unavailable: 'The AI service is busy. Try again in a moment.',
  timeout: 'Ask Forge took too long. Try again.',
  invalid_response: 'Ask Forge couldn’t verify that answer. Try again.',
  refused: 'Ask Forge can’t help with that. Try a question about the step.',
  incomplete: 'That answer was cut short. Try a shorter question.',
  context_unavailable:
    'Open this in a Part Studio for questions about your model.',
  read_permission_required:
    'Forge needs permission to read your model. Check your Onshape connection.',
  evidence_unavailable:
    'Forge couldn’t read your model right now. Try again after it finishes updating.',
  session_expired: 'Your Forge session changed. Check your connection.',
  request_in_progress: 'A question is already running. Please wait.',
  cancelled: 'Request cancelled.',
} as const;
export type TutorErrorCode = keyof typeof tutorMessages;
export class TutorError extends Error {
  constructor(
    public readonly code: TutorErrorCode,
    public readonly retryAfter = 5,
  ) {
    super(code);
  }
}
export const stageText = {
  understanding: 'Reading your question…',
  inspecting: 'Reading your model…',
  reviewing: 'Thinking it through…',
  preparing: 'Preparing the answer…',
} as const;
export type TutorStage = keyof typeof stageText;

export interface TutorHints {
  experience: Experience;
  goal: LearningGoal;
  hints_revealed: 0 | 1 | 2 | 3;
  guidance: 'full' | 'reduced' | 'independent';
  investigation: {
    stage: 'observed' | 'predicted' | 'explained' | 'recommended';
    prediction_answered: boolean;
    rechecked: boolean;
    resolved: boolean;
  } | null;
}
export interface TutorMessage {
  role: 'user' | 'assistant';
  content: string;
}
export type CheckWord = 'verified' | 'not_met' | 'unverified';
export interface TutorAnswerView {
  explanation: string;
  reasoning_question: string | null;
  next_action: string | null;
  observed: { source: 'check' | 'cad'; status: string; statement: string }[];
  unknowns: string[];
  notes: string[];
  latest_check: { outcome: CheckWord; captured_at: string } | null;
  used_cad: boolean;
  captured_at: string | null;
  capability_state: 'read_only';
}

function text(value: unknown, max: number): value is string {
  return typeof value === 'string' && value.length <= max;
}
function texts(value: unknown, count: number, max: number): value is string[] {
  return (
    Array.isArray(value) &&
    value.length <= count &&
    value.every((v) => text(v, max))
  );
}
export function parseTutorAnswer(value: unknown): TutorAnswerView {
  const fail = () => new TutorError('invalid_response');
  let data: Record<string, unknown>;
  try {
    data = object(value, [
      'explanation',
      'reasoning_question',
      'next_action',
      'observed',
      'unknowns',
      'notes',
      'latest_check',
      'used_cad',
      'captured_at',
      'capability_state',
    ]);
  } catch {
    throw fail();
  }
  if (
    !text(data.explanation, 1200) ||
    !data.explanation.trim() ||
    !(data.reasoning_question === null || text(data.reasoning_question, 400)) ||
    !(data.next_action === null || text(data.next_action, 400)) ||
    !texts(data.unknowns, 8, 600) ||
    !texts(data.notes, 6, 600) ||
    typeof data.used_cad !== 'boolean' ||
    data.capability_state !== 'read_only' ||
    !(data.captured_at === null || text(data.captured_at, 40)) ||
    !Array.isArray(data.observed) ||
    data.observed.length > 12
  )
    throw fail();
  for (const raw of data.observed) {
    try {
      const item = object(raw, ['source', 'status', 'statement']);
      if (
        !['check', 'cad'].includes(item.source as string) ||
        !text(item.status, 40) ||
        !text(item.statement, 2400) ||
        !item.statement.trim()
      )
        throw fail();
    } catch {
      throw fail();
    }
  }
  if (data.latest_check !== null) {
    try {
      const check = object(data.latest_check, ['outcome', 'captured_at']);
      if (
        !['verified', 'not_met', 'unverified'].includes(
          check.outcome as string,
        ) ||
        !text(check.captured_at, 40)
      )
        throw fail();
    } catch {
      throw fail();
    }
  }
  return data as unknown as TutorAnswerView;
}

export interface TutorQuestion {
  lessonId: 'mounting-bracket' | 'mounting-plate';
  stepId: string;
  question: string;
  history: TutorMessage[];
  learner: TutorHints;
  evidenceToken: string | null;
  context: OnshapeClientContext | null;
}

// Only a validated, workspace Part Studio context may allow a CAD read.
function cadContext(context: OnshapeClientContext | null) {
  if (
    !context ||
    context.revision.kind !== 'workspace' ||
    context.server !== 'https://cad.onshape.com' ||
    (context.elementType && context.elementType !== 'partStudio')
  )
    return null;
  return {
    documentId: context.documentId,
    workspaceId: context.revision.workspaceId,
    elementId: context.elementId,
    revisionKind: 'workspace' as const,
  };
}

export async function askTutor(
  request: TutorQuestion,
  csrf: string,
  signal: AbortSignal,
  progress: (stage: TutorStage) => void,
): Promise<TutorAnswerView> {
  const response = await fetch('/api/learning/tutor', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify({
      lesson_id: request.lessonId,
      step_id: request.stepId,
      question: request.question,
      history: request.history.slice(-6),
      learner: request.learner,
      evidence_token: request.evidenceToken,
      context: cadContext(request.context),
    }),
  });
  if (!response.ok) {
    if (response.status === 401 || response.status === 403)
      throw new TutorError('session_expired');
    if (response.status === 429) {
      let wait = 60;
      try {
        const body = (await response.json()) as {
          retry_after_seconds?: unknown;
        };
        if (bounded(body.retry_after_seconds, 1, 86400))
          wait = body.retry_after_seconds as number;
      } catch {
        // Nothing worth showing in a malformed body.
      }
      throw new TutorError('rate_limited', wait);
    }
    if (response.status === 503) throw new TutorError('not_configured');
    throw new TutorError('connection_unavailable');
  }
  if (
    !response.body ||
    !response.headers.get('content-type')?.includes('application/x-ndjson')
  )
    throw new TutorError('invalid_response');
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '';
  let bytes = 0;
  let result: TutorAnswerView | null = null;
  let terminal = false;
  let events = 0;
  try {
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.length;
      if (bytes > 262144) throw new TutorError('invalid_response');
      buffer += decoder.decode(chunk.value, { stream: true });
      let newline: number;
      while ((newline = buffer.indexOf('\n')) !== -1) {
        if (terminal || ++events > 8) throw new TutorError('invalid_response');
        const event: unknown = JSON.parse(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
        if (!event || typeof event !== 'object' || !('type' in event))
          throw new TutorError('invalid_response');
        if (event.type === 'progress') {
          const data = object(event, ['type', 'stage']);
          if (
            typeof data.stage !== 'string' ||
            !Object.hasOwn(stageText, data.stage)
          )
            throw new TutorError('invalid_response');
          progress(data.stage as TutorStage);
        } else if (event.type === 'result') {
          result = parseTutorAnswer(object(event, ['type', 'result']).result);
          terminal = true;
        } else if (event.type === 'error') {
          const data = object(event, ['type', 'code', 'retry_after_seconds']);
          if (
            typeof data.code !== 'string' ||
            !Object.hasOwn(tutorMessages, data.code) ||
            !(
              data.retry_after_seconds === null ||
              bounded(data.retry_after_seconds, 1, 86400)
            )
          )
            throw new TutorError('invalid_response');
          throw new TutorError(
            data.code as TutorErrorCode,
            (data.retry_after_seconds as number | null) ?? 5,
          );
        } else throw new TutorError('invalid_response');
      }
    }
    buffer += decoder.decode();
    if (buffer.trim() || !result) throw new TutorError('invalid_response');
    return result;
  } catch (cause) {
    if (cause instanceof TutorError || signal.aborted) throw cause;
    throw new TutorError('invalid_response');
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
