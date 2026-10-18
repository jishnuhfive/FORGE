import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  approve,
  cancelPlan,
  contextBody,
  createPlan,
  parseEvent,
  parsePlan,
  parsePreview,
  parseResult,
  planStatus,
} from './api';
import type { PlanPreview } from './api';

const preview: PlanPreview = {
  proposal_id: 'p'.repeat(43),
  digest: 'd'.repeat(64),
  expires_at: 2000000000,
  operations: [
    {
      type: 'SET_EXTRUDE_DEPTH',
      label: 'Extrude fixture',
      feature_type: 'extrude',
      position: 2,
      field: 'Depth',
      current: '20 mm',
      proposed: '30 mm',
    },
  ],
};
const csrf = 'a'.repeat(64);
const signal = () => new AbortController().signal;
const final = {
  type: 'result',
  state: 'verified_success',
  operations: ['verified_success'],
};
const progress = (stage: string) => ({
  type: 'progress',
  operation: 1,
  total: 1,
  stage,
});
const json = (data: unknown) =>
  new Response(JSON.stringify(data), {
    headers: { 'Content-Type': 'application/json' },
  });
function stream(lines: unknown[]): Response {
  return new Response(
    lines.map((line) => JSON.stringify(line) + '\n').join(''),
    { headers: { 'Content-Type': 'application/x-ndjson' } },
  );
}
afterEach(() => vi.unstubAllGlobals());

describe('closed multi-operation contracts', () => {
  it('parses the authoritative preview without provider identities', () => {
    expect(parsePlan({ outcome: 'plan', preview })).toEqual({
      outcome: 'plan',
      preview,
    });
  });
  it.each([
    'featureId',
    'providerFeatureId',
    'microversion',
    'payload',
    'url',
    'method',
    'FeatureScript',
    'token',
  ])('rejects private or extra %s at all plan boundaries', (key) => {
    expect(() =>
      parsePlan({ outcome: 'plan', preview, [key]: 'synthetic' }),
    ).toThrow();
    expect(() => parsePreview({ ...preview, [key]: 'synthetic' })).toThrow();
    expect(() =>
      parsePreview({
        ...preview,
        operations: [{ ...preview.operations[0], [key]: 'synthetic' }],
      }),
    ).toThrow();
    expect(() =>
      parsePlan({
        outcome: 'clarification',
        reason: 'ambiguous_target',
        choices: [
          {
            label: 'Fillet',
            feature_type: 'fillet',
            position: 3,
            [key]: 'synthetic',
          },
        ],
      }),
    ).toThrow();
  });
  it.each([
    { proposal_id: 'x' },
    { digest: 'A'.repeat(64) },
    { expires_at: 1.5 },
    { operations: [] },
    { operations: Array(6).fill(preview.operations[0]) },
    { operations: [{ ...preview.operations[0], type: 'DELETE' }] },
    { operations: [{ ...preview.operations[0], feature_type: 'sketch' }] },
    { operations: [{ ...preview.operations[0], field: 'Volume' }] },
    { operations: [{ ...preview.operations[0], field: 'Radius' }] },
    { operations: [{ ...preview.operations[0], position: 0 }] },
    { operations: [{ ...preview.operations[0], label: '' }] },
    { operations: [{ ...preview.operations[0], proposed: 'x'.repeat(257) }] },
  ])('rejects malformed preview %j', (change) => {
    expect(() => parsePreview({ ...preview, ...change })).toThrow();
  });
  it.each([
    { outcome: 'unknown', reason: 'missing_value', choices: [] },
    { outcome: 'clarification', reason: 'provider prose', choices: [] },
    {
      outcome: 'clarification',
      reason: 'missing_value',
      choices: [],
      payload: {},
    },
    {
      outcome: 'clarification',
      reason: 'missing_value',
      choices: Array(7).fill({}),
    },
  ])('rejects malformed clarification', (raw) => {
    expect(() => parsePlan(raw)).toThrow();
  });
  it.each([
    { state: 'success', operations: ['verified_success'] },
    { state: 'verified_success', operations: ['pending'] },
    { state: 'pending', operations: ['verified_success'] },
    { state: 'cancelled', operations: ['write_failed'] },
    { state: 'partial_failure', operations: ['write_failed'] },
    {
      state: 'verified_success',
      operations: ['verified_success'],
      payload: {},
    },
    { state: 'verified_success', operations: [] },
    { state: 'execution_uncertain', operations: ['executing'] },
  ])('rejects misleading result journals', (raw) => {
    expect(() => parseResult(raw, 1)).toThrow();
  });
  it('retains A1 uncertainty even if all operations were journaled verified', () => {
    expect(
      parseResult(
        { state: 'execution_uncertain', operations: ['verified_success'] },
        1,
      ).state,
    ).toBe('execution_uncertain');
  });
  it.each([
    { ...progress('checking'), operation: 0 },
    { ...progress('checking'), total: 2 },
    { ...progress('checking'), operation: 2 },
    progress('success'),
    { ...progress('checking'), featureId: 'synthetic' },
    { ...final, operations: ['skipped'] },
    { type: 'error', code: 'raw-provider-error' },
    { type: 'operation_result', operation: 1, total: 1, state: 'success' },
  ])('rejects invalid event boundaries', (raw) => {
    expect(() => parseEvent(raw, 1)).toThrow();
  });
});

describe('approval stream safety', () => {
  it('handles UTF-8/chunk boundaries and returns only the final result', async () => {
    const bytes = new TextEncoder().encode(
      [
        progress('checking'),
        progress('executing'),
        progress('verifying'),
        {
          type: 'operation_result',
          operation: 1,
          total: 1,
          state: 'verified_success',
        },
        final,
      ]
        .map((e) => JSON.stringify(e) + '\n')
        .join(''),
    );
    const chunks = new ReadableStream<Uint8Array>({
      start(controller) {
        for (let i = 0; i < bytes.length; i += 3)
          controller.enqueue(bytes.slice(i, i + 3));
        controller.close();
      },
    });
    const fetcher = vi.fn(
      async () =>
        new Response(chunks, {
          headers: { 'Content-Type': 'application/x-ndjson; charset=utf-8' },
        }),
    );
    vi.stubGlobal('fetch', fetcher);
    const events = vi.fn();
    expect(await approve(preview, csrf, signal(), events)).toEqual({
      state: 'verified_success',
      operations: ['verified_success'],
    });
    expect(events).toHaveBeenCalledTimes(4);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it.each(
    [
      [],
      [progress('executing')],
      [progress('checking'), progress('checking')],
      [progress('verifying'), progress('executing')],
      [final, final],
      [
        {
          type: 'operation_result',
          operation: 1,
          total: 1,
          state: 'write_failed',
        },
        final,
      ],
      [{ type: 'error', code: 'execution_uncertain' }],
      [progress('checking'), { ...final, featureId: 'synthetic-private' }],
    ].map((lines) => ({ lines })),
  )('never retries an incomplete or inconsistent stream', async ({ lines }) => {
    const fetcher = vi.fn(async () => stream(lines));
    vi.stubGlobal('fetch', fetcher);
    await expect(
      approve(preview, csrf, signal(), () => {}),
    ).rejects.toMatchObject({ code: 'execution_uncertain' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it.each([
    'not-json\n',
    JSON.stringify(final),
    ' '.repeat(512) + '\n',
    ' '.repeat(8193),
    '\n',
    JSON.stringify(progress('checking')) + '\n' + '{',
    Array(22)
      .fill(JSON.stringify(progress('checking')) + '\n')
      .join(''),
  ])('rejects malformed, unterminated or oversized streams', async (body) => {
    const fetcher = vi.fn(
      async () =>
        new Response(body, {
          headers: { 'Content-Type': 'application/x-ndjson' },
        }),
    );
    vi.stubGlobal('fetch', fetcher);
    await expect(
      approve(preview, csrf, signal(), () => {}),
    ).rejects.toMatchObject({ code: 'execution_uncertain' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('enforces the byte limit rather than the character length', async () => {
    const body =
      JSON.stringify({ ...progress('checking'), private: 'é'.repeat(250) }) +
      '\n';
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(body, {
            headers: { 'Content-Type': 'application/x-ndjson' },
          }),
      ),
    );
    await expect(
      approve(preview, csrf, signal(), () => {}),
    ).rejects.toMatchObject({ code: 'execution_uncertain' });
  });
  it('rejects invalid UTF-8 without claiming success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(new Uint8Array([0xff, 10]), {
            headers: { 'Content-Type': 'application/x-ndjson' },
          }),
      ),
    );
    await expect(
      approve(preview, csrf, signal(), () => {}),
    ).rejects.toMatchObject({ code: 'execution_uncertain' });
  });
  it('does not treat HTTP 200 JSON as an approval stream', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(final)),
    );
    await expect(
      approve(preview, csrf, signal(), () => {}),
    ).rejects.toMatchObject({ code: 'execution_uncertain' });
  });
  it('accepts only the digest in the approval payload', async () => {
    const fetcher = vi.fn(async () => stream([final]));
    vi.stubGlobal('fetch', fetcher);
    await approve(preview, csrf, signal(), () => {});
    expect(fetcher).toHaveBeenCalledWith(
      '/api/modify/plans/' + preview.proposal_id + '/approve',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ digest: preview.digest }),
        credentials: 'same-origin',
      }),
    );
  });
  it('never retries a fetch failure', async () => {
    const fetcher = vi.fn(async () => {
      throw new TypeError('synthetic disconnect');
    });
    vi.stubGlobal('fetch', fetcher);
    await expect(
      approve(preview, csrf, signal(), () => {}),
    ).rejects.toMatchObject({ code: 'execution_uncertain' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});

describe('bounded HTTP planning/status/cancel', () => {
  it('status and cancel never invoke approval', async () => {
    const fetcher = vi.fn(async (url: string) =>
      json(
        url.endsWith('/cancel')
          ? { state: 'cancelled', operations: ['skipped'] }
          : { state: 'pending', operations: ['pending'] },
      ),
    );
    vi.stubGlobal('fetch', fetcher);
    await planStatus(preview, csrf, signal());
    await cancelPlan(preview, csrf, signal());
    expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
      '/api/modify/plans/' + preview.proposal_id,
      '/api/modify/plans/' + preview.proposal_id + '/cancel',
    ]);
  });
  it('bounds and strictly decodes the planning JSON body', async () => {
    const context = {
      documentId: 'a'.repeat(24),
      elementId: 'c'.repeat(24),
      server: 'https://cad.onshape.com',
      revision: { kind: 'workspace' as const, workspaceId: 'b'.repeat(24) },
    };
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(' '.repeat(65537), {
            headers: { 'Content-Type': 'application/json' },
          }),
      ),
    );
    await expect(
      createPlan(context, 'rename fillet', csrf, signal()),
    ).rejects.toThrow();
    expect(() =>
      contextBody({
        ...context,
        revision: { kind: 'version', versionId: 'v'.repeat(24) },
      }),
    ).toThrow();
  });
});
