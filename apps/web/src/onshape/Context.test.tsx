import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Design } from '../features/Design';
import { CadContext } from '../components/CadContext';
import { AuthGate } from '../auth/AuthGate';
import { OnshapeContext } from './store';
import { parseLaunch } from './context';
import { standaloneState } from './model';
import type { ClientState } from './model';
const launch = parseLaunch(
  `?server=https://cad.onshape.com&documentId=${'a'.repeat(24)}&workspaceId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}`,
  true,
  true,
);
it.each([
  [standaloneState, 'Not inside Onshape'],
  [parseLaunch('', true, true), 'Waiting for document context'],
  [
    parseLaunch('?documentId=bad', true, true),
    'Document context could not be validated',
  ],
  [
    parseLaunch('?server=https://evil.example', true, true),
    'Onshape origin could not be verified',
  ],
] as const)('renders context status', (state, text) => {
  render(<CadContext context={{ kind: 'live', state }} />);
  expect(screen.getByText(text)).toBeVisible();
});
it.each([
  [[], 'No selection'],
  [
    [{ type: 'face' as const, reference: 'synthetic-face-reference' }],
    '1 face selected',
  ],
  [
    [{ type: 'edge' as const, reference: 'synthetic-edge-reference' }],
    '1 edge selected',
  ],
  [[{ type: 'edge' as const }, { type: 'edge' as const }], '2 edges selected'],
])('renders internal selection presentation %j', (entities, label) => {
  const state: ClientState = {
    ...launch,
    status: 'EMBEDDED_CONNECTED',
    selection: { status: 'available', entities },
  };
  render(<CadContext context={{ kind: 'live', state }} />);
  expect(screen.getByText(label)).toBeVisible();
  expect(screen.queryByText('a'.repeat(24))).not.toBeInTheDocument();
  expect(document.body.textContent).not.toContain('synthetic-face-reference');
  expect(document.body.textContent).not.toContain('synthetic-edge-reference');
});
it('keeps launch context visible when embedded authentication is unavailable and safely rechecks', async () => {
  const me = {
    status: 'signed_out',
    configured: true,
    display_name: null,
    connection: null,
    csrf_token: null,
    verified_at: null,
  };
  const fetch = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(me))),
    );
  vi.stubGlobal('fetch', fetch);
  render(
    <OnshapeContext.Provider value={launch}>
      <AuthGate>
        <p>Private workspace</p>
      </AuthGate>
    </OnshapeContext.Provider>,
  );
  expect(
    await screen.findByText(/Your Forge session is unavailable/),
  ).toBeVisible();
  expect(screen.getByText('Onshape launch context')).toBeVisible();
  expect(screen.queryByText('Private workspace')).not.toBeInTheDocument();
  expect(
    screen.getByRole('link', { name: 'Open Forge in a new tab' }),
  ).toHaveAttribute('rel', 'noopener noreferrer');
  await act(async () =>
    fireEvent.click(
      screen.getByRole('button', { name: 'Check panel session' }),
    ),
  );
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const call of fetch.mock.calls) expect(call[0]).toBe('/api/me');
});

it.each([
  [launch, 'Onshape workspace context'],
  [standaloneState, 'Not inside Onshape'],
  [parseLaunch('', true, true), 'Waiting for document context'],
  [parseLaunch('?documentId=bad', true, true), 'Document context unavailable'],
  [
    parseLaunch('?server=https://evil.example', true, true),
    'Onshape origin could not be verified',
  ],
] as const)(
  'Design composer reflects normalized context instead of the static fallback',
  (state, label) => {
    render(
      <OnshapeContext.Provider value={state}>
        <Design />
      </OnshapeContext.Provider>,
    );
    expect(screen.getByText(label)).toBeVisible();
    expect(screen.queryByText('No CAD context')).not.toBeInTheDocument();
    expect(screen.queryByText('a'.repeat(24))).not.toBeInTheDocument();
  },
);
