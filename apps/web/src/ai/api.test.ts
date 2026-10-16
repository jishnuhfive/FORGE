import { describe, expect, it, vi } from 'vitest';
import { askForge, parseAnswer } from './api';
import { resultStream, syntheticAnswer } from './__fixtures__/response';
import type { OnshapeClientContext } from '../onshape/model';

const context: OnshapeClientContext = {
  documentId: 'a'.repeat(24),
  elementId: 'c'.repeat(24),
  revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
  server: 'https://cad.onshape.com',
};
function response(body: string) {
  return new Response(body, {
    headers: { 'Content-Type': 'application/x-ndjson' },
  });
}
function ask() {
  return askForge(
    context,
    'd'.repeat(64),
    'What features?',
    'FACE',
    [],
    new AbortController().signal,
    vi.fn(),
  );
}

describe('AI stream boundary', () => {
  it('sends only approved fields with CSRF and normalized selection', async () => {
    const fetch = vi.fn().mockResolvedValue(response(resultStream()));
    vi.stubGlobal('fetch', fetch);
    expect(await ask()).toEqual(syntheticAnswer);
    const [path, options] = fetch.mock.calls[0] as [string, RequestInit];
    expect(path).toBe('/api/ai/ask');
    expect(options.credentials).toBe('same-origin');
    expect(options.cache).toBe('no-store');
    expect(JSON.parse(options.body as string)).toEqual({
      prompt: 'What features?',
      context: {
        documentId: 'a'.repeat(24),
        workspaceId: 'b'.repeat(24),
        elementId: 'c'.repeat(24),
        revisionKind: 'workspace',
      },
      selection: 'FACE',
      history: [],
    });
    expect(options.headers).toEqual({
      'Content-Type': 'application/json',
      'X-CSRF-Token': 'd'.repeat(64),
    });
  });
  it('handles split UTF-8 chunks and reports normalized progress', async () => {
    const bytes = new TextEncoder().encode(
      resultStream({
        ...syntheticAnswer,
        discussion: 'An unverified idea → review it.',
      }),
    );
    const stream = new ReadableStream({
      start(controller) {
        for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
        controller.close();
      },
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(stream, {
          headers: { 'Content-Type': 'application/x-ndjson' },
        }),
      ),
    );
    const progress = vi.fn();
    const result = await askForge(
      context,
      'd'.repeat(64),
      'Explain',
      'none',
      [],
      new AbortController().signal,
      progress,
    );
    expect(progress).toHaveBeenCalledWith('inspecting');
    expect(result.discussion).toContain('→');
  });
  for (const body of [
    '{"type":"response.output_text.delta","delta":"raw"}\n',
    '{"type":"progress","stage":"reasoning"}\n',
    '{"type":"progress","stage":"inspecting","raw_tool_result":{}}\n',
    '{"type":"result","result":{}}\n',
    '{"type":"error","code":"private-provider-body","retry_after_seconds":null}\n',
    '{"type":"progress","stage":"inspecting"}\n',
    resultStream() + '{"type":"progress","stage":"inspecting"}\n',
    'x'.repeat(262145),
  ])
    it('rejects malformed, unbounded or raw provider streams', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body)));
      await expect(ask()).rejects.toThrow();
    });
  for (const [status, body, code] of [
    [503, '{"detail":"not_configured"}', 'not_configured'],
    [503, 'raw traceback private', 'connection_unavailable'],
    [401, 'private', 'session_expired'],
    [403, 'private', 'session_expired'],
    [429, 'private', 'rate_limited'],
  ] as const)
    it(`maps HTTP ${status} safely`, async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(new Response(body, { status })),
      );
      await expect(ask()).rejects.toThrow(code);
    });
  it('honors fixed error codes and retry delay', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          response(
            '{"type":"error","code":"rate_limited","retry_after_seconds":37}\n',
          ),
        ),
    );
    await expect(ask()).rejects.toMatchObject({
      code: 'rate_limited',
      retryAfter: 37,
    });
  });
  it('rejects unsupported context before sending', async () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    await expect(
      askForge(
        { ...context, server: 'https://evil.example' },
        '',
        '',
        'none',
        [],
        new AbortController().signal,
        vi.fn(),
      ),
    ).rejects.toThrow('context_unavailable');
    expect(fetch).not.toHaveBeenCalled();
  });
  for (const update of [
    { capability_state: 'write' },
    { evidence: [{ id: 'a', statement: 'x', status: 'PASS' }] },
    { evidence: [{ id: 'a', statement: '', status: 'verified' }] },
    { evidence: [{ id: 'a', statement: ' \t\n ', status: 'verified' }] },
    { evidence: [{ id: 'a', statement: '\u00a0', status: 'verified' }] },
    { answer: 'x'.repeat(30001) },
    { uncertainties: Array(7).fill('x') },
    { raw_response: {} },
  ])
    it('rejects invalid final contracts', () => {
      expect(() => parseAnswer({ ...syntheticAnswer, ...update })).toThrow();
    });
});
