import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { parseLaunch } from '../onshape/context';
import type { ClientState } from '../onshape/model';
import { ReadCad } from './ReadCad';
import { syntheticProof } from './__fixtures__/proof';
import type { ReadProof, Section } from './api';

const launch = parseLaunch(
  `?server=https://cad.onshape.com&documentId=${'a'.repeat(24)}&workspaceId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}`,
  true,
  true,
);
const me: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Test Engineer',
  connection: 'connected',
  csrf_token: 'f'.repeat(64),
  verified_at: null,
};
const view = (state = launch, account = me) => (
  <AuthContext.Provider
    value={{ me: account, reload: vi.fn(), endSession: vi.fn() }}
  >
    <ReadCad state={state} />
  </AuthContext.Provider>
);
const respond = (value: unknown = syntheticProof) =>
  new Response(JSON.stringify(value));
const click = async () =>
  act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Read CAD data' }));
  });
afterEach(() => vi.useRealTimers());

it('reads only on explicit action, blocks duplicates and renders a compact summary', async () => {
  let resolve!: (response: Response) => void;
  const fetch = vi.fn(
    () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  );
  vi.stubGlobal('fetch', fetch);
  render(view());
  expect(fetch).not.toHaveBeenCalled();
  await click();
  expect(
    screen.getByText('Reading this Part Studio from Onshape…'),
  ).toBeVisible();
  expect(
    screen.getByRole('button', { name: 'Reading CAD data…' }),
  ).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Reading CAD data…' }));
  expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => resolve(respond()));
  expect(screen.getByText('Onshape data connected')).toBeVisible();
  expect(screen.getByText('2 features')).toBeVisible();
  expect(screen.getByText('1 part')).toBeVisible();
  expect(screen.getByText('Mass properties available')).toBeVisible();
  expect(
    screen.getByText(/single consistent CAD version is unverified/),
  ).toBeVisible();
  expect(screen.getByRole('button', { name: 'Read CAD data' })).toBeDisabled();
  for (const value of [
    'a'.repeat(24),
    'b'.repeat(24),
    'c'.repeat(24),
    me.csrf_token!,
    'sourceMicroversion',
    'btType',
  ])
    expect(document.body.textContent).not.toContain(value);
});

it.each([
  [
    'unauthorized',
    'read_permission_required',
    /Additional Onshape read permission required/,
  ],
  ['unauthorized', 'connection_required', /Onshape connection required/],
  [
    'forbidden',
    'permission_or_access_required',
    /Check the app’s document-read permission/,
  ],
  ['forbidden', 'document_forbidden', /Access to this document is forbidden/],
  ['not_found', 'not_found', /Document or element not found/],
  ['rate_limited', 'rate_limited', /Onshape API rate limit reached/],
  ['rate_limited', 'quota_exceeded', /Onshape API allowance reached/],
  [
    'provider_failure',
    'provider_unavailable',
    /Onshape temporarily unavailable/,
  ],
  ['provider_failure', 'provider_timeout', /Onshape took too long/],
  ['provider_failure', 'invalid_response', /could not verify/],
  ['unavailable', 'response_too_large', /exceeds the current read size limit/],
] as const)(
  'handles %s / %s without discarding successful sections',
  async (status, code, text) => {
    const result: ReadProof = {
      ...syntheticProof,
      bodies: { status, code, count: null, retry_after_seconds: null },
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(result)));
    render(view());
    await click();
    expect(screen.getByText(text)).toBeVisible();
    expect(screen.getByText('2 features')).toBeVisible();
    expect(screen.getByText('1 part')).toBeVisible();
  },
);

it.each(['documentId', 'workspaceId', 'elementId', 'microversionId'] as const)(
  'clears completed data on %s change',
  async (field) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond()));
    const { rerender } = render(view());
    await click();
    expect(screen.getByText('2 features')).toBeVisible();
    const context = launch.context!;
    const changed: ClientState = {
      ...launch,
      context:
        field === 'workspaceId'
          ? {
              ...context,
              revision: { kind: 'workspace', workspaceId: 'e'.repeat(24) },
            }
          : { ...context, [field]: 'e'.repeat(24) },
    };
    rerender(view(changed));
    expect(screen.queryByText('2 features')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Read CAD data' })).toBeEnabled();
  },
);

it('aborts old reads and ignores late success after context changes', async () => {
  let resolve!: (response: Response) => void;
  const fetch = vi.fn<(url: string, options: RequestInit) => Promise<Response>>(
    () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  );
  vi.stubGlobal('fetch', fetch);
  const { rerender } = render(view());
  await click();
  const signal = fetch.mock.calls[0]![1].signal;
  rerender(
    view({
      ...launch,
      context: { ...launch.context!, elementId: 'e'.repeat(24) },
    }),
  );
  expect(signal?.aborted).toBe(true);
  await act(async () => resolve(respond()));
  expect(screen.queryByText('2 features')).not.toBeInTheDocument();
});

it.each(['disconnect', 'account', 'lifecycle'] as const)(
  'clears read data on %s change',
  async (change) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond()));
    const { rerender } = render(view());
    await click();
    if (change === 'disconnect')
      rerender(view(launch, { ...me, connection: 'disconnected' }));
    else if (change === 'account')
      rerender(view(launch, { ...me, csrf_token: 'e'.repeat(64) }));
    else
      rerender(
        view({ ...launch, selection: { status: 'stale', entities: [] } }),
      );
    expect(screen.queryByText('2 features')).not.toBeInTheDocument();
  },
);

it('clears read data when the page is hidden', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond()));
  render(view());
  await click();
  act(() => window.dispatchEvent(new Event('pagehide')));
  expect(screen.queryByText('2 features')).not.toBeInTheDocument();
});

it('honors Retry-After without polling', async () => {
  vi.useFakeTimers();
  const limited: Section = {
    status: 'rate_limited',
    code: 'rate_limited',
    count: null,
    retry_after_seconds: 120,
  };
  const fetch = vi.fn().mockResolvedValue(
    respond({
      ...syntheticProof,
      features: limited,
      parts: limited,
      bodies: limited,
      mass: limited,
      has_mass: null,
    }),
  );
  vi.stubGlobal('fetch', fetch);
  render(view());
  await click();
  await act(async () => vi.advanceTimersByTime(119000));
  expect(screen.getByRole('button', { name: 'Read CAD data' })).toBeDisabled();
  await act(async () => vi.advanceTimersByTime(1000));
  expect(screen.getByRole('button', { name: 'Read CAD data' })).toBeEnabled();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('reports mismatched microversions and missing assigned mass', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      respond({
        ...syntheticProof,
        consistency: 'mismatch',
        has_mass: false,
      }),
    ),
  );
  render(view());
  await click();
  expect(screen.getByText(/CAD changed during this read/)).toBeVisible();
  expect(
    screen.getByText('Mass unavailable; material/density may be missing'),
  ).toBeVisible();
  expect(
    screen.queryByText('Mass properties available'),
  ).not.toBeInTheDocument();
  expect(screen.getByText('2 features')).toBeVisible();
  expect(screen.getByText('1 part')).toBeVisible();
  expect(screen.getByText('1 body')).toBeVisible();
});

it('shows successfully read missing mass with other CAD counts and no provider error', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      respond({
        ...syntheticProof,
        has_mass: false,
      }),
    ),
  );
  render(view());
  await click();
  expect(screen.getByText('Onshape data connected')).toBeVisible();
  expect(
    screen.getByText('Mass unavailable; material/density may be missing'),
  ).toBeVisible();
  expect(screen.getByText('2 features')).toBeVisible();
  expect(screen.getByText('1 part')).toBeVisible();
  expect(screen.getByText('1 body')).toBeVisible();
  expect(
    screen.queryByText('Mass properties available'),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText(/Onshape returned data Forge could not verify/),
  ).not.toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(
    /nominal|lower|upper|massSigns/,
  );
});

it.each([401, 403, 422, 503])(
  'sanitizes failed Forge HTTP %s',
  async (status) => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response('private-provider-error', { status })),
    );
    render(view());
    await click();
    expect(document.body.textContent).not.toContain('private-provider-error');
    expect(
      screen.queryByText('Onshape data connected'),
    ).not.toBeInTheDocument();
  },
);

it('rejects unvalidated provider data and never renders it', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      respond({
        ...syntheticProof,
        token: 'private-token',
        raw: { feature: 'private-feature' },
      }),
    ),
  );
  render(view());
  await click();
  expect(screen.getByText(/Onshape temporarily unavailable/)).toBeVisible();
  expect(document.body.textContent).not.toContain('private-token');
  expect(document.body.textContent).not.toContain('private-feature');
});

it('offers no reads without authentication or for version contexts', () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  const { rerender } = render(<ReadCad state={launch} />);
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  rerender(
    view({
      ...launch,
      context: {
        ...launch.context!,
        revision: { kind: 'version', versionId: 'e'.repeat(24) },
      },
    }),
  );
  expect(screen.getByText(/workspace Part Studios only/)).toBeVisible();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});
