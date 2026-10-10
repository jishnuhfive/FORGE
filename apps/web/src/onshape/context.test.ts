import { describe, expect, it } from 'vitest';
import { approvedOrigin, parseLaunch } from './context';
import { selectionLabel } from './model';
import {
  capturedLaunchFixture,
  capturedLaunchQuery,
} from './__fixtures__/launch';

const valid = new URLSearchParams({
  server: 'https://cad.onshape.com',
  documentId: 'a'.repeat(24),
  elementId: 'c'.repeat(24),
  workspaceOrVersion: 'w',
  workspaceOrVersionId: 'b'.repeat(24),
});
const parse = (change: Record<string, string> = {}) => {
  const params = new URLSearchParams(valid);
  for (const [key, value] of Object.entries(change)) params.set(key, value);
  return parseLaunch(`?${params}`, true, true);
};
describe('Onshape launch boundary', () => {
  it('normalizes workspace context without retaining raw queries', () => {
    expect(parse().context).toEqual({
      server: 'https://cad.onshape.com',
      documentId: 'a'.repeat(24),
      elementId: 'c'.repeat(24),
      revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
    });
  });
  it('preserves version semantics', () => {
    expect(parse({ workspaceOrVersion: 'v' }).context?.revision).toEqual({
      kind: 'version',
      versionId: 'b'.repeat(24),
    });
  });
  it('retains an optional validated microversion without pretending it is a workspace', () => {
    expect(
      parse({ microversionId: 'd'.repeat(24) }).context?.microversionId,
    ).toBe('d'.repeat(24));
  });
  it.each([
    'documentId',
    'elementId',
    'workspaceOrVersionId',
    'microversionId',
  ])('rejects malformed %s', (field) => {
    for (const value of ['bad', 'a'.repeat(25), 'g'.repeat(24), '<script>', ''])
      expect(parse({ [field]: value }).status).toBe('EMBEDDED_CONTEXT_ERROR');
  });
  it.each(['m', 'workspace', 'x', ''])(
    'rejects unsupported revision kind %s',
    (value) => {
      expect(parse({ workspaceOrVersion: value }).status).toBe(
        'EMBEDDED_CONTEXT_ERROR',
      );
    },
  );
  it('rejects duplicate, ambiguous and incomplete revision pairs', () => {
    expect(
      parseLaunch(`?${valid}&documentId=${'a'.repeat(24)}`, true, true).context,
    ).toBeNull();
    expect(parse({ workspaceId: 'b'.repeat(24) }).context).toBeNull();
    const params = new URLSearchParams(valid);
    params.delete('workspaceOrVersionId');
    expect(parseLaunch(`?${params}`, true, true).status).toBe(
      'EMBEDDED_CONTEXT_ERROR',
    );
  });
  it.each(['workspaceId', 'versionId'])(
    'accepts the explicit %s form',
    (key) => {
      const params = new URLSearchParams(valid);
      params.delete('workspaceOrVersion');
      params.delete('workspaceOrVersionId');
      params.set(key, 'd'.repeat(24));
      expect(parseLaunch(`?${params}`, true, true).context?.revision.kind).toBe(
        key === 'workspaceId' ? 'workspace' : 'version',
      );
    },
  );
  it('allows missing optional metadata, waits for missing required launch context', () => {
    expect(parse().context).not.toHaveProperty('elementType');
    expect(parse().context).not.toHaveProperty('microversionId');
    expect(parseLaunch('', true, true).status).toBe('EMBEDDED_INITIALIZING');
  });
  it('does not infer Onshape from iframe presence or copied top-level query', () => {
    expect(parseLaunch(`?${valid}`, false, true).status).toBe('STANDALONE');
    expect(parseLaunch(`?${valid}`, true, false).status).toBe(
      'EMBEDDED_CONTEXT_ERROR',
    );
  });
  it.each([
    'access_token',
    'refresh_token',
    'code',
    'returnUrl',
    'elementType',
  ])('rejects unrecognized/sensitive launch field %s', (key) => {
    const state = parse({ [key]: 'never-retain-this' });
    expect(state.context).toBeNull();
    expect(JSON.stringify(state)).not.toContain('never-retain-this');
  });
  it('bounds query length and rejects control characters', () => {
    expect(parseLaunch('x'.repeat(4097), true, true).context).toBeNull();
    expect(parse({ locale: 'en\nUS' }).context).toBeNull();
  });
  it('discards valid unused Onshape defaults', () => {
    const state = parse({
      userId: 'd'.repeat(24),
      clientId: 'e'.repeat(24),
      companyId: 'cad',
      locale: 'en-US',
    });
    expect(state.context).not.toBeNull();
    expect(state.context).not.toHaveProperty('userId');
    expect(state.context).not.toHaveProperty('clientId');
  });
});
describe('operator-owned origin policy', () => {
  it.each([
    'https://cad.onshape.com',
    'https://CAD.ONSHAPE.COM/',
    'https://cad.onshape.com:443',
  ])('normalizes approved origin %s', (value) =>
    expect(approvedOrigin(value)).toBe('https://cad.onshape.com'),
  );
  it.each([
    '',
    'null',
    '*',
    'http://cad.onshape.com',
    'https://evil.example',
    'https://cad.onshape.com.evil.example',
    'https://enterprise.onshape.com',
    'https://oauth.onshape.com',
    'https://cad.onshape.com:444',
    'https://user@cad.onshape.com',
    'https://cad.onshape.com/path',
    'https://cad.onshape.com/?token=secret',
    'https://cad.onshape.com/#x',
    ' https://cad.onshape.com',
    'https://cad.onshape.com\\@evil.example',
  ])('rejects %s', (value) => {
    expect(approvedOrigin(value)).toBeNull();
    expect(parse({ server: value }).status).toBe('UNTRUSTED_ORIGIN');
  });
});
describe('internal selection presentation (not an Onshape wire contract)', () => {
  it.each([
    [[], 'No selection'],
    [[{ type: 'face' as const }], '1 face selected'],
    [
      [{ type: 'edge' as const }, { type: 'edge' as const }],
      '2 edges selected',
    ],
    [
      [
        { type: 'face' as const },
        { type: 'edge' as const },
        { type: 'body' as const },
      ],
      '3 entities selected',
    ],
  ])('labels %j', (entities, expected) =>
    expect(selectionLabel({ status: 'available', entities })).toBe(expected),
  );
  it.each(['waiting', 'stale', 'unavailable'] as const)(
    'does not claim no selection when %s',
    (status) =>
      expect(selectionLabel({ status, entities: [] })).not.toBe('No selection'),
  );
});

describe('real workspace-style right-panel launch', () => {
  const workspace = new URLSearchParams({
    documentId: 'a'.repeat(24),
    workspaceId: 'b'.repeat(24),
    elementId: 'c'.repeat(24),
    server: 'https://cad.onshape.com',
  });
  it('normalizes the configured workspace URL identically to the w/id form', () => {
    expect(parseLaunch(`?${workspace}`, true, true)).toEqual(parse());
  });
  it.each(['bad', '', 'g'.repeat(24), 'b'.repeat(25)])(
    'rejects malformed explicit workspaceId %s',
    (value) => {
      const query = new URLSearchParams(workspace);
      query.set('workspaceId', value);
      expect(parseLaunch(`?${query}`, true, true).status).toBe(
        'EMBEDDED_CONTEXT_ERROR',
      );
    },
  );
  it('waits without context when workspaceId is missing', () => {
    const query = new URLSearchParams(workspace);
    query.delete('workspaceId');
    expect(parseLaunch(`?${query}`, true, true)).toMatchObject({
      status: 'EMBEDDED_INITIALIZING',
      context: null,
    });
  });
  it.each([
    `workspaceId=${'d'.repeat(24)}`,
    `versionId=${'d'.repeat(24)}`,
    `workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}`,
    `workspaceOrVersion=v&workspaceOrVersionId=${'d'.repeat(24)}`,
  ])('rejects conflicting workspace parameters %s', (extra) => {
    expect(parseLaunch(`?${workspace}&${extra}`, true, true).status).toBe(
      'EMBEDDED_CONTEXT_ERROR',
    );
  });
  it('rejects an untrusted server for the workspace form', () => {
    const query = new URLSearchParams(workspace);
    query.set('server', 'https://evil.example');
    expect(parseLaunch(`?${query}`, true, true)).toMatchObject({
      status: 'UNTRUSTED_ORIGIN',
      context: null,
    });
  });
});

describe('sanitized real launch metadata regression', () => {
  it('normalizes the captured field shape and discards all ancillary metadata', () => {
    expect(parseLaunch(capturedLaunchQuery, true, true).context).toEqual({
      documentId: 'a'.repeat(24),
      elementId: 'c'.repeat(24),
      revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
      server: 'https://cad.onshape.com',
    });
  });
  it.each(['clientId', 'sessionCompanyId', 'theme'])(
    'accepts bounded opaque %s without using it as authority or presentation',
    (name) => {
      for (const value of [
        'opaque.value:with/punctuation',
        'https://evil.example',
        '<ignored>',
        'x'.repeat(128),
      ]) {
        const query = new URLSearchParams(capturedLaunchFixture);
        query.set(name, value);
        const result = parseLaunch(`?${query}`, true, true);
        expect(result.context?.server).toBe('https://cad.onshape.com');
        expect(JSON.stringify(result)).not.toContain(value);
        expect(result.context).not.toHaveProperty(name);
      }
    },
  );
  it.each(['clientId', 'sessionCompanyId', 'theme'])(
    'rejects empty, oversized, control-bearing and duplicate %s',
    (name) => {
      for (const value of [
        '',
        'x'.repeat(129),
        'bad\nvalue',
        'bad\u007fvalue',
      ]) {
        const query = new URLSearchParams(capturedLaunchFixture);
        query.set(name, value);
        expect(parseLaunch(`?${query}`, true, true).context).toBeNull();
      }
      expect(
        parseLaunch(`${capturedLaunchQuery}&${name}=duplicate`, true, true)
          .context,
      ).toBeNull();
    },
  );
  it.each(['documentId', 'workspaceId', 'elementId', 'server', 'access_token'])(
    'metadata compatibility cannot bypass invalid or forbidden %s',
    (name) => {
      const query = new URLSearchParams(capturedLaunchFixture);
      query.set(name, name === 'server' ? 'https://evil.example' : 'invalid');
      expect(parseLaunch(`?${query}`, true, true).context).toBeNull();
    },
  );
});
