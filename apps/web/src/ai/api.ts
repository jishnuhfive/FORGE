import { bounded, object } from '../cad/api';
import type { OnshapeClientContext } from '../onshape/model';

export const messages = {
  not_configured:
    'Forge AI is not configured. Ask your administrator to configure it.',
  connection_unavailable:
    'The AI connection is unavailable. Try again when ready.',
  authentication_failed: 'The AI connection needs administrator attention.',
  rate_limited:
    'The AI service is rate limited. Please wait before trying again.',
  quota_unavailable:
    'AI capacity is unavailable. Ask your administrator to check the service limits.',
  capacity_unavailable:
    'AI capacity is temporarily unavailable. Please wait before trying again.',
  timeout: 'The AI request timed out. Try again when ready.',
  invalid_response: 'The response could not be verified. Try again when ready.',
  refused:
    'Forge could not answer that request. Try a safe engineering question.',
  incomplete: 'The AI response was incomplete. Try a shorter question.',
  context_unavailable:
    'A current workspace Part Studio is required. Open Forge inside Onshape.',
  read_permission_required:
    'CAD read permission or document access is required. Check your Onshape connection.',
  evidence_unavailable:
    'Current CAD evidence is unavailable or inconsistent. Try again after the model finishes updating.',
  session_expired:
    'Your Forge session changed. Check your connection before trying again.',
  request_in_progress:
    'A request is already running. Wait before trying again.',
  cancelled: 'Request cancelled.',
} as const;
export type ErrorCode = keyof typeof messages;
export const stages = {
  understanding: 'Understanding request…',
  inspecting: 'Inspecting current CAD…',
  reviewing: 'Reviewing evidence…',
  preparing: 'Preparing answer…',
} as const;
export type Stage = keyof typeof stages;
export type Selection = 'none' | 'FACE' | 'EDGE' | 'unknown';
export type HistoryMessage = { role: 'user' | 'assistant'; content: string };
export interface Answer {
  answer: string;
  evidence: {
    id: string;
    statement: string;
    status: 'verified' | 'unverified' | 'unknown' | 'assumption';
  }[];
  uncertainties: string[];
  discussion: string;
  assumptions: string[];
  follow_up_questions: string[];
  capability_state: 'read_only';
  captured_at: string | null;
}
export class AiError extends Error {
  constructor(
    public readonly code: ErrorCode,
    public readonly retryAfter = 5,
  ) {
    super(code);
  }
}
function text(value: unknown, max: number): value is string {
  return typeof value === 'string' && value.length <= max;
}
function texts(value: unknown, count: number) {
  return (
    Array.isArray(value) &&
    value.length <= count &&
    value.every((v) => text(v, 600))
  );
}
export function parseAnswer(value: unknown): Answer {
  const data = object(value, [
    'answer',
    'evidence',
    'uncertainties',
    'discussion',
    'assumptions',
    'follow_up_questions',
    'capability_state',
    'captured_at',
  ]);
  if (
    !text(data.answer, 30000) ||
    !text(data.discussion, 1600) ||
    !texts(data.uncertainties, 6) ||
    !texts(data.assumptions, 3) ||
    !texts(data.follow_up_questions, 3) ||
    data.capability_state !== 'read_only' ||
    !(
      data.captured_at === null ||
      (text(data.captured_at, 40) &&
        /^\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|\+00:00)$/.test(data.captured_at) &&
        Number.isFinite(Date.parse(data.captured_at)))
    ) ||
    !Array.isArray(data.evidence) ||
    data.evidence.length > 12
  )
    throw new AiError('invalid_response');
  for (const value of data.evidence) {
    const item = object(value, ['id', 'statement', 'status']);
    if (
      !text(item.id, 64) ||
      !text(item.statement, 2400) ||
      !item.statement.trim() ||
      !['verified', 'unverified', 'unknown', 'assumption'].includes(
        item.status as string,
      )
    )
      throw new AiError('invalid_response');
  }
  return data as unknown as Answer;
}

export async function askForge(
  context: OnshapeClientContext,
  csrf: string,
  prompt: string,
  selection: Selection,
  history: HistoryMessage[],
  signal: AbortSignal,
  progress: (stage: Stage) => void,
): Promise<Answer> {
  if (
    context.revision.kind !== 'workspace' ||
    context.server !== 'https://cad.onshape.com' ||
    (context.elementType && context.elementType !== 'partStudio')
  )
    throw new AiError('context_unavailable');
  const response = await fetch('/api/ai/ask', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify({
      prompt,
      context: {
        documentId: context.documentId,
        workspaceId: context.revision.workspaceId,
        elementId: context.elementId,
        revisionKind: 'workspace',
      },
      selection,
      history: history.slice(-6),
    }),
  });
  if (!response.ok) {
    // Fixed public codes only. Raw server/provider content is never rendered.
    if (response.status === 401 || response.status === 403)
      throw new AiError('session_expired');
    if (response.status === 429) throw new AiError('rate_limited', 60);
    if (response.status === 503) {
      const body = await response.text();
      if (body.length < 256 && body === '{"detail":"not_configured"}')
        throw new AiError('not_configured');
    }
    throw new AiError('connection_unavailable');
  }
  if (
    !response.body ||
    !response.headers.get('content-type')?.includes('application/x-ndjson')
  )
    throw new AiError('invalid_response');
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '';
  let bytes = 0;
  let result: Answer | null = null;
  let terminal = false;
  let eventCount = 0;
  try {
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.length;
      if (bytes > 262144) throw new AiError('invalid_response');
      buffer += decoder.decode(chunk.value, { stream: true });
      let newline: number;
      while ((newline = buffer.indexOf('\n')) !== -1) {
        if (terminal || ++eventCount > 8) throw new AiError('invalid_response');
        const event: unknown = JSON.parse(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
        if (!event || typeof event !== 'object' || !('type' in event))
          throw new AiError('invalid_response');
        if (event.type === 'progress') {
          const data = object(event, ['type', 'stage']);
          if (
            typeof data.stage !== 'string' ||
            !Object.hasOwn(stages, data.stage)
          )
            throw new AiError('invalid_response');
          progress(data.stage as Stage);
        } else if (event.type === 'result') {
          const data = object(event, ['type', 'result']);
          result = parseAnswer(data.result);
          terminal = true;
        } else if (event.type === 'error') {
          const data = object(event, ['type', 'code', 'retry_after_seconds']);
          if (
            typeof data.code !== 'string' ||
            !Object.hasOwn(messages, data.code) ||
            !(
              data.retry_after_seconds === null ||
              bounded(data.retry_after_seconds, 1, 86400)
            )
          )
            throw new AiError('invalid_response');
          throw new AiError(
            data.code as ErrorCode,
            (data.retry_after_seconds as number | null) ?? 5,
          );
        } else throw new AiError('invalid_response');
      }
    }
    buffer += decoder.decode();
    if (buffer.trim() || !result) throw new AiError('invalid_response');
    return result;
  } catch (cause) {
    if (cause instanceof AiError || signal.aborted) throw cause;
    throw new AiError('invalid_response');
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
