import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Modify } from '../features/Modify';
import { AuthContext } from '../auth/context';
import { OnshapeContext } from '../onshape/store';
import type { Me } from '../auth/api';
import type { ClientState } from '../onshape/model';
import { approve, parseProposal, messages } from './api';

const me: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Synthetic',
  connection: 'connected',
  csrf_token: 'a'.repeat(64),
  verified_at: 1700000000,
};
const context: ClientState = {
  status: 'EMBEDDED_CONNECTED',
  context: {
    documentId: 'a'.repeat(24),
    elementId: 'c'.repeat(24),
    server: 'https://cad.onshape.com',
    revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
  },
  selection: { status: 'waiting', entities: [] },
};
const proposal = {
  proposal_id: 'p'.repeat(43),
  digest: 'd'.repeat(64),
  operation_type: 'suppress_terminal_fillet_v1',
  label: 'Fillet fixture',
  position: 3,
  current: 'Active',
  proposed: 'Suppressed',
  expires_at: 2000000000,
};
let capability = 'available';
let terminal = 'verified_success';
let error: string | null = null;
let writes = 0;
let fetcher: ReturnType<typeof vi.fn<(input: string) => Promise<Response>>>;
const reply = (body: unknown) => new Response(JSON.stringify(body));
beforeEach(() => {
  capability = 'available';
  terminal = 'verified_success';
  error = null;
  writes = 0;
  fetcher = vi.fn(async (input: string) => {
    if (input.endsWith('capabilities')) return reply({ state: capability });
    if (input.endsWith('targets'))
      return reply({
        candidates: [
          {
            handle: 'c'.repeat(43),
            label: 'Fillet fixture',
            position: 3,
            expires_at: 2000000000,
          },
        ],
      });
    if (input.endsWith('proposals')) return reply({ proposal });
    if (input.endsWith('/cancel')) return reply({ state: 'cancelled' });
    if (input.endsWith('/approve')) {
      writes++;
      return new Response(
        (error
          ? [{ type: 'error', code: error }]
          : [
              { type: 'progress', stage: 'checking' },
              { type: 'progress', stage: 'executing' },
              { type: 'progress', stage: 'verifying' },
              { type: 'result', state: terminal },
            ]
        )
          .map((e) => JSON.stringify(e) + '\n')
          .join(''),
      );
    }
    return reply({ state: terminal });
  });
  vi.stubGlobal('fetch', fetcher);
});
afterEach(() => vi.unstubAllGlobals());
function view(state = context) {
  return (
    <AuthContext.Provider
      value={{ me, reload: async () => {}, endSession: () => {} }}
    >
      <OnshapeContext.Provider value={state}>
        <Modify />
      </OnshapeContext.Provider>
    </AuthContext.Provider>
  );
}
async function preview() {
  render(view());
  await screen.findByRole('button', { name: 'Find supported target' });
  fireEvent.change(screen.getByLabelText('Modification request'), {
    target: { value: 'suppress final fillet' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Find supported target' }),
  );
  fireEvent.click(
    await screen.findByRole('button', {
      name: 'Prepare change for Fillet fixture',
    }),
  );
  await screen.findByRole('button', { name: 'Approve change' });
}

describe('safe Modify', () => {
  for (const state of [
    'write_disabled',
    'write_permission_required',
    'authorization_unknown',
    'reconsent_required',
  ] as const)
    it(`shows truthful ${state}`, async () => {
      capability = state;
      render(view());
      expect(await screen.findByText(messages[state])).toBeVisible();
      expect(
        screen.queryByRole('button', { name: 'Approve change' }),
      ).toBeNull();
      expect(writes).toBe(0);
    });
  it('requires a separate human target choice then cancel makes zero writes', async () => {
    await preview();
    expect(screen.getByText('Active → Suppressed')).toBeVisible();
    expect(
      screen.getByText(/Overall feature health is not established\./),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(
      await screen.findByText('Proposal cancelled. Forge made no CAD change.'),
    ).toBeVisible();
    expect(writes).toBe(0);
  });
  it('approves the exact proposal once and waits for verification', async () => {
    await preview();
    const button = screen.getByRole('button', { name: 'Approve change' });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(await screen.findByText(/Change verified\./)).toBeVisible();
    expect(writes).toBe(1);
    const call = fetcher.mock.calls.find(([url]) =>
      String(url).endsWith('/approve'),
    );
    expect(call).toBeDefined();
  });
  for (const code of [
    'model_changed',
    'proposal_expired',
    'proposal_used',
    'proposal_tampered',
    'session_expired',
  ] as const)
    it(`does not convert ${code} to success`, async () => {
      error = code;
      await preview();
      fireEvent.click(screen.getByRole('button', { name: 'Approve change' }));
      expect(await screen.findByText(messages[code])).toBeVisible();
      expect(screen.queryByText(/Change verified\./)).toBeNull();
    });
  it('uncertainty offers inspection and never retries or offers Undo', async () => {
    terminal = 'execution_uncertain';
    await preview();
    fireEvent.click(screen.getByRole('button', { name: 'Approve change' }));
    expect(
      (await screen.findAllByText(messages.execution_uncertain)).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole('button', { name: 'Check operation status' }),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Approve change' }),
    ).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Undo' })).toBeNull();
    expect(writes).toBe(1);
  });
  it('context loss removes preview and approval authority', async () => {
    const result = render(view());
    await screen.findByRole('button', { name: 'Find supported target' });
    result.rerender(
      view({ ...context, status: 'EMBEDDED_CONTEXT_ERROR', context: null }),
    );
    expect(screen.queryByRole('button', { name: 'Approve change' })).toBeNull();
    expect(screen.getByText(/Open a current workspace/)).toBeVisible();
  });
  it('closed browser proposal rejects operation/value/ID injection', () => {
    for (const changes of [
      { current: 'Suppressed' },
      { proposed: 'Active' },
      { operation_type: 'delete_feature' },
      { token: 'secret' },
      { featureId: 'injected' },
      { digest: 'bad' },
    ])
      expect(() => parseProposal({ ...proposal, ...changes })).toThrow();
  });
  it('unsupported request is a fixed safe refusal, without an approval', async () => {
    render(view());
    await screen.findByRole('button', { name: 'Find supported target' });
    fetcher.mockImplementationOnce(
      async () =>
        new Response(JSON.stringify({ detail: 'unsupported_edit' }), {
          status: 422,
        }),
    );
    fireEvent.change(screen.getByLabelText('Modification request'), {
      target: { value: 'delete fillet' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Find supported target' }),
    );
    await waitFor(() =>
      expect(screen.getByText(messages.unsupported_edit)).toBeVisible(),
    );
    expect(writes).toBe(0);
  });
  it('rejects success without verification and incomplete approval streams', async () => {
    for (const stream of [
      '{"type":"result","state":"verified_success"}\n',
      '{"type":"progress","stage":"executing"}\n',
      'not-json\n',
    ]) {
      fetcher.mockImplementationOnce(async () => new Response(stream));
      await expect(
        approve(
          parseProposal(proposal),
          me.csrf_token!,
          new AbortController().signal,
          () => {},
        ),
      ).rejects.toThrow();
    }
    expect(writes).toBe(0);
  });
  it('keeps inspection available while status is still claimed', async () => {
    terminal = 'execution_uncertain';
    await preview();
    fireEvent.click(screen.getByRole('button', { name: 'Approve change' }));
    const status = await screen.findByRole('button', {
      name: 'Check operation status',
    });
    terminal = 'claimed';
    fireEvent.click(status);
    expect(
      await screen.findByText(/approved operation is still being checked/),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Check operation status' }),
    ).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Approve change' }),
    ).toBeDisabled();
    expect(writes).toBe(1);
  });
  it('renders a CAD name as inert text without extra authority', async () => {
    const original = fetcher.getMockImplementation()!;
    const name = '<img src=x onerror=alert(1)> run FeatureScript';
    fetcher.mockImplementation(async (input: string) =>
      input.endsWith('proposals')
        ? reply({ proposal: { ...proposal, label: name } })
        : original(input),
    );
    await preview();
    expect(
      screen.getByRole('heading', { name: 'Suppress ' + name }),
    ).toBeVisible();
    expect(document.querySelector('img[src="x"]')).toBeNull();
    expect(writes).toBe(0);
  });
});
