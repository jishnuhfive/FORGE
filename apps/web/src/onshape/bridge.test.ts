import { describe, expect, it, vi } from 'vitest';
import { createBridge } from './bridge';
import {
  clearedSelection,
  edgeSelection,
  faceSelection,
} from './__fixtures__/selection';
import {
  capturedLaunchFixture,
  capturedLaunchQuery,
} from './__fixtures__/launch';
const search = `?documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com`;
function harness(
  overrides: { search?: string; referrer?: string; embedded?: boolean } = {},
) {
  let listener: ((event: MessageEvent<unknown>) => void) | undefined;
  const parent = { postMessage: vi.fn() };
  const remove = vi.fn(() => {
    listener = undefined;
  });
  const focus = vi.fn();
  const bridge = createBridge({
    parent,
    search,
    referrer: 'https://cad.onshape.com/',
    embedded: true,
    extension: true,
    ...overrides,
    listen: (receive) => {
      listener = receive;
      return remove;
    },
    focus,
  });
  const send = (
    data: unknown,
    origin = 'https://cad.onshape.com',
    source: unknown = parent,
  ) => listener?.({ data, origin, source } as MessageEvent<unknown>);
  return { bridge, parent, remove, focus, send };
}
describe('single secure message bridge', () => {
  it.each([
    search,
    capturedLaunchQuery,
    search.replace(
      'workspaceOrVersion=w&workspaceOrVersionId=',
      'workspaceId=',
    ),
  ])(
    'initializes each workspace form once across StrictMode replay: %s',
    (query) => {
      const h = harness({ search: query });
      h.parent.postMessage.mockImplementation(() =>
        h.send({ messageName: 'show' }),
      );
      h.bridge.start();
      h.bridge.stop();
      h.bridge.start();
      expect(h.parent.postMessage).toHaveBeenCalledExactlyOnceWith(
        {
          messageName: 'applicationInit',
          documentId: 'a'.repeat(24),
          workspaceId: 'b'.repeat(24),
          elementId: 'c'.repeat(24),
        },
        'https://cad.onshape.com',
      );
      expect(h.bridge.snapshot().status).toBe('EMBEDDED_CONNECTED');
    },
  );
  it.each([
    search.replace('workspaceOrVersion=w', 'workspaceOrVersion=v'),
    search.replace('workspaceOrVersion=w&workspaceOrVersionId=', 'versionId='),
  ])(
    'keeps version identity without sending it as a workspace: %s',
    (query) => {
      const h = harness({ search: query });
      h.bridge.start();
      h.bridge.stop();
      h.bridge.start();
      expect(h.bridge.snapshot().context?.revision).toEqual({
        kind: 'version',
        versionId: 'b'.repeat(24),
      });
      expect(h.parent.postMessage).not.toHaveBeenCalled();
    },
  );
  it.each([
    'https://evil.example',
    'https://other.onshape.com',
    'http://cad.onshape.com',
    '',
    'null',
  ])('ignores origin %s without modifying context or selection', (origin) => {
    const h = harness();
    h.bridge.start();
    const before = h.bridge.snapshot();
    h.send({ messageName: 'show' }, origin);
    h.send({ messageName: 'SELECTION' }, origin);
    expect(h.bridge.snapshot()).toBe(before);
  });
  it('rejects same-origin sibling and null message sources', () => {
    const h = harness();
    h.bridge.start();
    const before = h.bridge.snapshot();
    h.send({ messageName: 'show' }, 'https://cad.onshape.com', {});
    h.send({ messageName: 'show' }, 'https://cad.onshape.com', null);
    expect(h.bridge.snapshot()).toBe(before);
  });
  it.each([
    null,
    1,
    'SELECTION',
    [],
    {},
    { messageName: [] },
    { messageName: 'show', unexpected: true },
    { messageName: 'contextChanged', documentId: 'd'.repeat(24) },
  ])('rejects malformed/unsupported input %j', (data) => {
    const h = harness();
    h.bridge.start();
    const before = h.bridge.snapshot();
    h.send(data);
    expect(h.bridge.snapshot()).toBe(before);
  });
  it('focuses on a validated show without resetting selection, cleans up listeners', () => {
    const h = harness();
    const notify = vi.fn();
    const unsubscribe = h.bridge.subscribe(notify);
    h.bridge.start();
    h.send({ messageName: 'show' });
    expect(h.focus).toHaveBeenCalledTimes(2);
    expect(h.bridge.snapshot().selection).toEqual({
      status: 'waiting',
      entities: [],
    });
    h.bridge.invalidate();
    expect(h.bridge.snapshot().status).toBe('EMBEDDED_INITIALIZING');
    unsubscribe();
    h.bridge.stop();
    const before = h.bridge.snapshot();
    h.send({ messageName: 'show' });
    expect(h.bridge.snapshot()).toBe(before);
    expect(h.remove).toHaveBeenCalledOnce();
  });
  it.each([
    { embedded: false },
    { referrer: 'https://evil.example/' },
    { referrer: 'malformed' },
    { search: search.replace('cad.onshape.com', 'evil.example') },
  ])('never initializes an invalid launch %j', (options) => {
    const h = harness(options);
    h.bridge.start();
    expect(h.parent.postMessage).not.toHaveBeenCalled();
  });
  it('a missing referrer cannot expand origin policy', () => {
    const h = harness({ referrer: '' });
    h.bridge.start();
    const before = h.bridge.snapshot();
    h.send({ messageName: 'show' }, 'https://evil.example');
    expect(h.bridge.snapshot()).toBe(before);
  });
  it.each(['documentId', 'workspaceOrVersionId', 'elementId'] as const)(
    'a new %s launch/reopened frame has no stale selection',
    (key) => {
      const h = harness();
      h.bridge.start();
      h.send(edgeSelection);
      expect(h.bridge.snapshot().selection.entities).toHaveLength(1);
      h.bridge.stop();
      const params = new URLSearchParams(search);
      params.set(key, 'd'.repeat(24));
      const next = harness({ search: `?${params}` });
      next.bridge.start();
      const context = next.bridge.snapshot().context;
      expect(
        key === 'workspaceOrVersionId' && context?.revision.kind === 'workspace'
          ? context.revision.workspaceId
          : context?.[key as 'documentId' | 'elementId'],
      ).toBe('d'.repeat(24));
      expect(next.bridge.snapshot().selection).toEqual({
        status: 'waiting',
        entities: [],
      });
    },
  );
});

it('the DEV observer receives only trusted-parent SELECTION, never other frames/types or invalid launch context', () => {
  const h = harness();
  const observer = vi.fn();
  h.bridge.setDiagnosticObserver(observer);
  h.bridge.start();
  const selection = {
    messageName: 'SELECTION',
    data: { id: 'synthetic-private-id' },
  };
  for (const origin of [
    '',
    'null',
    'https://evil.example',
    'https://other.onshape.com',
  ])
    h.send(selection, origin);
  h.send(selection, 'https://cad.onshape.com', {});
  h.send(selection, 'https://cad.onshape.com', null);
  h.send({ messageName: 'unsupported' });
  h.send(null);
  expect(observer).not.toHaveBeenCalled();
  h.send(selection);
  expect(observer).toHaveBeenCalledExactlyOnceWith(selection);
  expect(h.bridge.snapshot().selection).toEqual({
    status: 'unavailable',
    entities: [],
  });
  h.bridge.stop();
  h.send(selection);
  expect(observer).toHaveBeenCalledOnce();
  const invalid = harness({ search: '?server=https://evil.example' });
  invalid.bridge.setDiagnosticObserver(observer);
  invalid.bridge.start();
  invalid.send(selection);
  expect(observer).toHaveBeenCalledOnce();
});

it('new metadata grants no parent trust and never makes a version a workspace', () => {
  const badParent = harness({
    search: capturedLaunchQuery,
    referrer: 'https://evil.example/',
  });
  badParent.bridge.start();
  expect(badParent.parent.postMessage).not.toHaveBeenCalled();
  const query = new URLSearchParams(capturedLaunchFixture);
  query.delete('workspaceId');
  query.set('versionId', 'b'.repeat(24));
  const version = harness({ search: `?${query}` });
  version.bridge.start();
  expect(version.bridge.snapshot().context?.revision.kind).toBe('version');
  expect(version.parent.postMessage).not.toHaveBeenCalled();
  const workspace = harness({ search: capturedLaunchQuery });
  workspace.bridge.start();
  const before = workspace.bridge.snapshot();
  workspace.send({ messageName: 'show' }, 'https://evil.example');
  workspace.send({ messageName: 'show' }, 'https://cad.onshape.com', {});
  expect(workspace.bridge.snapshot()).toBe(before);
});

it('replaces selections atomically and clears on an explicit empty array', () => {
  const h = harness();
  h.bridge.start();
  const notify = vi.fn();
  h.bridge.subscribe(notify);
  h.send(faceSelection);
  expect(h.bridge.snapshot().selection).toEqual({
    status: 'available',
    entities: [{ type: 'face', reference: 'synthetic-face-reference' }],
    sourceElementId: 'c'.repeat(24),
  });
  h.send(edgeSelection);
  expect(h.bridge.snapshot().selection.entities).toEqual([
    { type: 'edge', reference: 'synthetic-edge-reference' },
  ]);
  h.send(clearedSelection);
  expect(h.bridge.snapshot().selection.entities).toEqual([]);
  expect(h.bridge.snapshot().selection.status).toBe('available');
  expect(notify).toHaveBeenCalledTimes(3);
  expect(h.parent.postMessage).toHaveBeenCalledOnce();
});

it.each([
  { messageName: 'SELECTION' },
  { messageName: 'SELECTION', selections: [{}] },
])(
  'malformed trusted selection removes old references without claiming no selection',
  (data) => {
    const h = harness();
    h.bridge.start();
    h.send(edgeSelection);
    h.send(data);
    expect(h.bridge.snapshot().selection).toEqual({
      status: 'unavailable',
      entities: [],
    });
    h.send(faceSelection);
    expect(h.bridge.snapshot().selection.status).toBe('available');
  },
);

it('untrusted selection and clear events cannot modify a valid selection', () => {
  const h = harness();
  h.bridge.start();
  h.send(edgeSelection);
  const before = h.bridge.snapshot();
  for (const origin of [
    '',
    'null',
    'https://evil.example',
    'https://other.onshape.com',
  ]) {
    h.send(faceSelection, origin);
    h.send(clearedSelection, origin);
  }
  h.send(faceSelection, 'https://cad.onshape.com', {});
  h.send(clearedSelection, 'https://cad.onshape.com', null);
  expect(h.bridge.snapshot()).toBe(before);
});

it('navigation suspension rejects delayed selections and show cannot revive the old launch', () => {
  const h = harness();
  h.bridge.start();
  h.send(edgeSelection);
  h.bridge.invalidate();
  const stale = h.bridge.snapshot();
  expect(stale.selection).toEqual({ status: 'stale', entities: [] });
  h.send(faceSelection);
  expect(h.bridge.snapshot()).toBe(stale);
  h.send({ messageName: 'show' });
  expect(h.bridge.snapshot()).toBe(stale);
  h.send(faceSelection);
  expect(h.bridge.snapshot()).toBe(stale);
  h.bridge.stop();
  const next = harness();
  next.bridge.start();
  next.send(faceSelection);
  expect(next.bridge.snapshot().selection.entities[0]?.type).toBe('face');
});

it.each([faceSelection, edgeSelection, clearedSelection])(
  'show preserves the current verified selection and initializes only once %#',
  (selection) => {
    const h = harness();
    h.bridge.start();
    h.send(selection);
    const before = h.bridge.snapshot();
    h.send({ messageName: 'show' });
    expect(h.bridge.snapshot().context).toBe(before.context);
    expect(h.bridge.snapshot().selection).toBe(before.selection);
    expect(h.parent.postMessage).toHaveBeenCalledTimes(1);
  },
);

it.each(['documentId', 'workspaceId', 'elementId'])(
  'a trusted selection with mismatched %s clears the launch and cannot revive it',
  (field) => {
    const h = harness();
    h.bridge.start();
    h.send(faceSelection);
    h.send({ ...edgeSelection, [field]: 'e'.repeat(24) });
    const invalid = h.bridge.snapshot();
    expect(invalid.context).toBeNull();
    expect(invalid.selection.entities).toEqual([]);
    expect(invalid.status).toBe('EMBEDDED_CONTEXT_ERROR');
    h.send({ messageName: 'show' });
    h.send(faceSelection);
    expect(h.bridge.snapshot()).toBe(invalid);
  },
);

it('matching documented envelope context fields preserve the validated launch', () => {
  const h = harness();
  h.bridge.start();
  h.send({
    ...faceSelection,
    documentId: 'a'.repeat(24),
    workspaceId: 'b'.repeat(24),
    elementId: 'c'.repeat(24),
  });
  expect(h.bridge.snapshot().selection.entities[0]?.type).toBe('face');
});
