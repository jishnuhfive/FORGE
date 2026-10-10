import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseLaunch } from '../context';
import {
  capturedLaunchFixture,
  capturedLaunchQuery,
} from '../__fixtures__/launch';
import { sanitizedLaunchDiagnostic } from './launch';
const valid = {
  documentId: 'a'.repeat(24),
  workspaceId: 'b'.repeat(24),
  elementId: 'c'.repeat(24),
  server: 'https://cad.onshape.com',
};
const query = (changes: Record<string, string> = {}) =>
  `?${new URLSearchParams({ ...valid, ...changes })}`;
function diagnose(search: string) {
  return JSON.parse(sanitizedLaunchDiagnostic(search, true, true)!) as {
    parserStatus: string;
    parserReason: string;
    receivedParameterNames: string[];
    reasonCodes: string[];
    truncated: boolean;
    fieldsInspected?: boolean;
    fields: {
      name: string;
      present: boolean;
      type: string;
      lengths: number[];
      validation: string;
      reasonCodes: string[];
      formatValid: boolean | null;
      normalizedOrigin?: string | null;
      trusted?: boolean;
    }[];
  };
}
afterEach(() => vi.unstubAllEnvs());
describe('read-only sanitized launch diagnostic', () => {
  it('shows only names, lengths, types, presence and validation for an accepted launch', () => {
    const report = diagnose(query());
    expect(report.parserReason).toBe('valid-context');
    expect(report.reasonCodes).toEqual([]);
    expect(report.receivedParameterNames).toEqual(Object.keys(valid));
    for (const name of ['documentId', 'workspaceId', 'elementId']) {
      expect(report.fields.find((field) => field.name === name)).toMatchObject({
        present: true,
        type: 'string',
        lengths: [24],
        formatValid: true,
        validation: 'valid',
        reasonCodes: [],
      });
      expect(JSON.stringify(report)).not.toContain(
        valid[name as keyof typeof valid],
      );
    }
    expect(
      report.fields.find((field) => field.name === 'server'),
    ).toMatchObject({
      normalizedOrigin: 'https://cad.onshape.com',
      trusted: true,
    });
  });
  it.each([
    ['documentId', 'unresolved-placeholder', 'invalid-id-format'],
    ['workspaceId', 'bad workspace', 'invalid-id-format'],
    ['elementId', 'private-element', 'invalid-id-format'],
    ['userId', 'private-user', 'invalid-id-format'],
    ['clientId', 'x'.repeat(129), 'invalid-opaque-metadata'],
    ['companyId', 'private-company', 'invalid-company-id-format'],
    ['locale', 'private_locale', 'invalid-locale-format'],
    ['documentId', 'x'.repeat(257), 'value-too-long'],
    ['clientId', 'private\nidentifier', 'control-character'],
  ])(
    'explains %s rejection without changing parser results or disclosing its value',
    (name, value, reason) => {
      const search = query({ [name]: value });
      const report = diagnose(search);
      expect(report.parserStatus).toBe(parseLaunch(search, true, true).status);
      expect(report.parserStatus).toBe('EMBEDDED_CONTEXT_ERROR');
      expect(report.fields.find((field) => field.name === name)).toMatchObject({
        lengths: [value.length],
        validation: 'invalid',
        reasonCodes: expect.arrayContaining([reason]),
      });
      expect(JSON.stringify(report)).not.toContain(value);
    },
  );
  it('redacts all default metadata and unexpected parameter values, including secrets', () => {
    const metadata = {
      userId: 'd'.repeat(24),
      clientId: 'e'.repeat(32),
      companyId: 'f'.repeat(24),
      locale: 'en-US',
      applicationId: 'private-app-identifier',
      access_token: 'synthetic-access-secret',
      refresh_token: 'synthetic-refresh-secret',
      cookie: 'synthetic-cookie-value',
      code: 'synthetic-oauth-code',
      returnUrl: 'https://private.example/path?secret=private-value',
    };
    const report = diagnose(query(metadata));
    for (const value of Object.values(metadata))
      expect(JSON.stringify(report)).not.toContain(value);
    expect(report.receivedParameterNames).toContain('applicationId');
    expect(
      report.fields.find((field) => field.name === 'applicationId'),
    ).toMatchObject({
      validation: 'invalid',
      reasonCodes: ['unexpected-parameter'],
    });
  });
  it.each([
    ['https://cad.onshape.com/private-path', 'server-path'],
    [
      'https://private-user:private-password@cad.onshape.com',
      'server-credentials',
    ],
    [
      'https://cad.onshape.com/?token=private-token',
      'server-query-or-fragment',
    ],
    ['https://private-id.evil.example', 'server-origin-not-allowlisted'],
    ['https://cad.onshape.com:444', 'server-port'],
    ['not-a-url-private', 'server-invalid-url'],
    ['http://cad.onshape.com', 'server-requires-https'],
    [' https://cad.onshape.com', 'server-whitespace-or-backslash'],
  ])(
    'normalizes only approved origins and explains a rejected server',
    (server, reason) => {
      const report = diagnose(query({ server }));
      const field = report.fields.find((field) => field.name === 'server');
      expect(field?.trusted).toBe(false);
      expect(field?.reasonCodes).toContain(reason);
      expect([null, 'https://cad.onshape.com']).toContain(
        field?.normalizedOrigin,
      );
      expect(JSON.stringify(report)).not.toContain('private-');
      expect(report.parserStatus).toBe(
        parseLaunch(query({ server }), true, true).status,
      );
    },
  );
  it('identifies missing required fields, duplicate names, conflicts and incomplete pairs', () => {
    const missing = new URLSearchParams(valid);
    missing.delete('workspaceId');
    expect(
      diagnose(`?${missing}`).fields.find(
        (field) => field.name === 'workspaceId',
      ),
    ).toMatchObject({
      present: false,
      type: 'missing',
      lengths: [],
      validation: 'invalid',
      reasonCodes: ['missing-required'],
    });
    expect(
      diagnose(`${query()}&workspaceId=${'d'.repeat(24)}`).reasonCodes,
    ).toContain('duplicate-parameter');
    expect(
      diagnose(query({ versionId: 'd'.repeat(24) })).reasonCodes,
    ).toContain('conflicting-revision-parameters');
    expect(diagnose(query({ workspaceOrVersion: 'w' })).reasonCodes).toContain(
      'incomplete-revision-pair',
    );
  });
  it.each(['w', 'v'])(
    'preserves the parser outcome for the explicit %s/id representation',
    (kind) => {
      const params = new URLSearchParams(valid);
      params.delete('workspaceId');
      params.set('workspaceOrVersion', kind);
      params.set('workspaceOrVersionId', 'b'.repeat(24));
      const report = diagnose(`?${params}`);
      expect(report.parserReason).toBe('valid-context');
      expect(report.reasonCodes).toEqual([]);
      expect(
        report.fields.find((field) => field.name === 'workspaceId')?.validation,
      ).toBe('absent');
    },
  );
  it('redacts suspicious parameter names and bounds diagnostic work', () => {
    const report = diagnose(
      query({
        ['d'.repeat(24)]: 'private-value',
        'https://private.example': 'private',
      }),
    );
    expect(report.receivedParameterNames).toContain(
      '<redacted-parameter-name-5>',
    );
    expect(JSON.stringify(report)).not.toContain('d'.repeat(24));
    expect(JSON.stringify(report)).not.toContain('private');
    expect(diagnose('x'.repeat(4097))).toMatchObject({
      reasonCodes: ['query-too-long'],
      fieldsInspected: false,
    });
    const many = diagnose(
      '?' +
        new URLSearchParams(
          Object.fromEntries(
            Array.from({ length: 100 }, (_, i) => [`field${i}`, 'private']),
          ),
        ),
    );
    expect(many.truncated).toBe(true);
    expect(many.fields.length).toBeLessThanOrEqual(64);
  });
  it('cannot produce a diagnostic in production', () => {
    vi.stubEnv('DEV', false);
    expect(sanitizedLaunchDiagnostic(query(), true, true)).toBeNull();
  });
  it('treats nested JSON and encoded malformed values only as opaque strings', () => {
    const nested = JSON.stringify({
      items: [{ token: 'private-nested-token', id: 'f'.repeat(24) }],
    });
    const report = diagnose(
      query({ clientId: nested, applicationId: '%7Bprivate-encoded-value%7D' }),
    );
    expect(
      report.fields.find((field) => field.name === 'clientId'),
    ).toMatchObject({
      type: 'string',
      lengths: [nested.length],
      validation: 'valid',
    });
    for (const value of [
      nested,
      'private-nested-token',
      'f'.repeat(24),
      'private-encoded-value',
    ])
      expect(JSON.stringify(report)).not.toContain(value);
  });
  it('keeps output bounded for both very wide queries and repeated empty values', () => {
    const wide =
      '?' +
      Array.from({ length: 500 }, (_, index) => `field${index}=`).join('&');
    const repeated = '?' + Array(1300).fill('a=').join('&');
    for (const search of [
      wide,
      repeated,
      query({ clientId: 'x'.repeat(10000) }),
    ]) {
      const output = sanitizedLaunchDiagnostic(search, true, true)!;
      expect(output.length).toBeLessThan(64000);
      expect(() => JSON.parse(output)).not.toThrow();
    }
  });
});

it('sanitized captured metadata is accepted, discarded and still redacted in diagnostics', () => {
  const report = diagnose(capturedLaunchQuery);
  expect(report.parserReason).toBe('valid-context');
  expect(report.reasonCodes).toEqual([]);
  for (const name of ['clientId', 'sessionCompanyId', 'theme'] as const) {
    expect(report.fields.find((field) => field.name === name)).toMatchObject({
      present: true,
      validation: 'valid',
      formatValid: true,
      lengths: [capturedLaunchFixture[name].length],
    });
    expect(JSON.stringify(report)).not.toContain(capturedLaunchFixture[name]);
  }
});
