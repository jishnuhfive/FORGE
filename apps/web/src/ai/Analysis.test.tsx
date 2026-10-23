import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { Design } from '../features/Design';
import { OnshapeContext } from '../onshape/store';
import type { ClientState, OnshapeClientContext } from '../onshape/model';
import { Analysis } from './Analysis';
import {
  resultStream,
  syntheticAnswer,
  syntheticSelectionAnswer,
  syntheticWriteAnswer,
} from './__fixtures__/response';

const context: OnshapeClientContext = {
  documentId: 'a'.repeat(24),
  elementId: 'c'.repeat(24),
  revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
  server: 'https://cad.onshape.com',
};
const me: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Synthetic engineer',
  connection: 'connected',
  csrf_token: 'd'.repeat(64),
  verified_at: 1,
};
const client: ClientState = {
  status: 'EMBEDDED_CONNECTED',
  context,
  selection: { status: 'available', entities: [] },
};
function tree(state = client, account = me) {
  return (
    <AuthContext.Provider
      value={{
        me: account,
        reload: async () => undefined,
        endSession: vi.fn(),
      }}
    >
      <OnshapeContext.Provider value={state}>
        <Design />
      </OnshapeContext.Provider>
    </AuthContext.Provider>
  );
}
function fill(prompt = 'What is in this model?') {
  fireEvent.change(screen.getByLabelText('Design prompt'), {
    target: { value: prompt },
  });
}
function send() {
  fireEvent.click(screen.getByRole('button', { name: 'Send prompt' }));
}
function fakeSuccess() {
  const fetch = vi.fn().mockImplementation(() =>
    Promise.resolve(
      new Response(resultStream(), {
        headers: { 'Content-Type': 'application/x-ndjson' },
      }),
    ),
  );
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

describe('Read-only analysis UX', () => {
  for (const kind of ['FACE', 'EDGE'] as const)
    it(`shows ${kind} ownership unknown without assumptions or capability offers`, async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(
          new Response(resultStream(syntheticSelectionAnswer(kind)), {
            headers: { 'Content-Type': 'application/x-ndjson' },
          }),
        ),
      );
      render(
        <Analysis context={context} csrf={'d'.repeat(64)} selection={kind} />,
      );
      fill(`What do you know about the ${kind.toLowerCase()} I selected?`);
      send();
      await screen.findByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      });
      expect(
        screen.getByText(
          /Owning part, body, feature, dimensions.*are currently unknown/,
        ),
      ).toBeVisible();
      for (const name of [
        'Assumptions',
        'Suggestions · unverified',
        'To explore next',
      ])
        expect(screen.queryByRole('heading', { name })).toBeNull();
      fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
      expect(
        screen.getByText(
          `The selected ${kind.toLowerCase()}'s owning body is unknown.`,
        ),
      ).toBeVisible();
      expect(
        screen.getByText(
          `The selected ${kind.toLowerCase()}'s owning part is unknown.`,
        ),
      ).toBeVisible();
      expect(
        screen.getByText(
          `The selected ${kind.toLowerCase()}'s owning feature is unknown.`,
        ),
      ).toBeVisible();
    });
  it('accepts a validated initial launch while selection is still unknown', () => {
    const fetch = fakeSuccess();
    render(
      tree({
        ...client,
        status: 'EMBEDDED_INITIALIZING',
        selection: { status: 'waiting', entities: [] },
      }),
    );
    expect(screen.getByLabelText('Design prompt')).toBeEnabled();
    expect(screen.getByText('Selection unknown')).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
  });
  it('discloses transfer and sends only after explicit keyboard action', async () => {
    const fetch = fakeSuccess();
    render(tree());
    fireEvent.click(screen.getByRole('button', { name: 'Data use' }));
    expect(screen.getByRole('dialog', { name: 'Your data' })).toHaveTextContent(
      'configured AI service',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }));
    expect(fetch).not.toHaveBeenCalled();
    fill();
    fireEvent.keyDown(screen.getByLabelText('Design prompt'), {
      key: 'Enter',
      ctrlKey: true,
    });
    expect(
      await screen.findByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(screen.getByText('unknown')).toBeVisible();
    expect(
      screen.getByRole('heading', { name: 'Technical limits' }),
    ).toBeVisible();
    expect(fetch).toHaveBeenCalledOnce();
    expect(JSON.stringify(localStorage)).not.toContain(
      'What is in this model?',
    );
  });
  it('shows real progress and prevents duplicate sends', async () => {
    let output: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        output = controller;
      },
    });
    const fetch = vi.fn().mockResolvedValue(
      new Response(stream, {
        headers: { 'Content-Type': 'application/x-ndjson' },
      }),
    );
    vi.stubGlobal('fetch', fetch);
    render(tree());
    fill();
    send();
    fireEvent.submit(screen.getByLabelText('Design prompt').closest('form')!);
    expect(fetch).toHaveBeenCalledOnce();
    await act(async () => {
      output!.enqueue(
        new TextEncoder().encode('{"type":"progress","stage":"inspecting"}\n'),
      );
    });
    expect(screen.getByText('Inspecting current CAD…')).toBeVisible();
    expect(
      document.querySelector('.user-prompt[data-pending]'),
    ).toHaveTextContent('What is in this model?');
    expect(screen.getByLabelText('Design prompt')).toBeDisabled();
    await act(async () => {
      output!.enqueue(
        new TextEncoder().encode(
          JSON.stringify({ type: 'result', result: syntheticAnswer }) + '\n',
        ),
      );
      output!.close();
    });
    expect(
      await screen.findByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
  });
  for (const [code, message] of [
    ['not_configured', 'not configured'],
    ['rate_limited', 'rate limited'],
    ['capacity_unavailable', 'capacity is temporarily unavailable'],
    ['evidence_unavailable', 'inconsistent'],
    ['timeout', 'timed out'],
  ] as const)
    it(`shows safe ${code} without automatic retry`, async () => {
      const fetch = vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ type: 'error', code, retry_after_seconds: 1 }) +
              '\n',
            { headers: { 'Content-Type': 'application/x-ndjson' } },
          ),
        );
      vi.stubGlobal('fetch', fetch);
      render(tree());
      fill();
      send();
      expect(await screen.findByRole('alert')).toHaveTextContent(message);
      expect(screen.getByRole('button', { name: 'Try again' })).toBeDisabled();
      await waitFor(
        () =>
          expect(
            screen.getByRole('button', { name: 'Try again' }),
          ).toBeEnabled(),
        { timeout: 2000 },
      );
      expect(fetch).toHaveBeenCalledOnce();
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
      await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    });
  for (const kind of ['none', 'FACE', 'EDGE'] as const)
    it(`normalizes ${kind} without selection references`, async () => {
      const fetch = fakeSuccess();
      const state: ClientState = {
        ...client,
        selection: {
          status: 'available',
          entities:
            kind === 'none'
              ? []
              : [
                  {
                    type: kind === 'FACE' ? 'face' : 'edge',
                    reference: 'private-selection-ref',
                  },
                ],
        },
      };
      render(tree(state));
      expect(
        screen.getByText(
          kind === 'none'
            ? 'No selection'
            : kind === 'FACE'
              ? '1 face selected'
              : '1 edge selected',
        ),
      ).toBeVisible();
      fill();
      send();
      await screen.findByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      });
      const body = fetch.mock.calls[0]?.[1] as RequestInit;
      expect(JSON.parse(body.body as string).selection).toBe(kind);
      expect(body.body).not.toContain('private-selection-ref');
    });
  for (const field of [
    'document',
    'workspace',
    'element',
    'account',
    'disconnect',
  ] as const)
    it(`clears old conversation on ${field} change`, async () => {
      fakeSuccess();
      const view = render(tree());
      fill();
      send();
      await screen.findByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      });
      let next = context;
      if (field === 'document')
        next = { ...context, documentId: 'e'.repeat(24) };
      if (field === 'workspace')
        next = {
          ...context,
          revision: { kind: 'workspace', workspaceId: 'e'.repeat(24) },
        };
      if (field === 'element') next = { ...context, elementId: 'e'.repeat(24) };
      view.rerender(
        tree(
          { ...client, context: next },
          {
            ...me,
            csrf_token: field === 'account' ? 'e'.repeat(64) : me.csrf_token,
            connection: field === 'disconnect' ? 'disconnected' : 'connected',
          },
        ),
      );
      expect(
        screen.queryByRole('heading', {
          name: /^(Response|Current model|Selected face|Selected edge)$/,
        }),
      ).not.toBeInTheDocument();
    });
  it('preserves conversation across same-context visibility and selection changes without calls', async () => {
    const fetch = fakeSuccess();
    const view = render(tree());
    fill();
    send();
    await screen.findByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    });
    fireEvent(document, new Event('visibilitychange'));
    fireEvent(window, new Event('focus'));
    view.rerender(
      tree({
        ...client,
        selection: { status: 'available', entities: [{ type: 'face' }] },
      }),
    );
    expect(
      screen.getByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).toBeVisible();
    expect(fetch).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole('button', { name: 'Clear conversation' }));
    expect(
      screen.queryByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).not.toBeInTheDocument();
  });
  it('cancels safely and discards late responses', async () => {
    let cancelled = false;
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        (_path: string, options: RequestInit) =>
          new Promise((_resolve, reject) =>
            options.signal?.addEventListener('abort', () => {
              cancelled = true;
              reject(new DOMException('Aborted', 'AbortError'));
            }),
          ),
      ),
    );
    render(tree());
    fill();
    send();
    fireEvent.click(screen.getByRole('button', { name: 'Stop request' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Request cancelled',
    );
    expect(cancelled).toBe(true);
    expect(
      screen.queryByRole('heading', {
        name: /^(Response|Current model|Selected face|Selected edge)$/,
      }),
    ).not.toBeInTheDocument();
  });
  it('renders the read-only write contract with unknown width and expandable evidence', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(resultStream(syntheticWriteAnswer), {
          headers: { 'Content-Type': 'application/x-ndjson' },
        }),
      ),
    );
    render(tree());
    fill('Make this model 20 mm wider.');
    send();
    expect(await screen.findByText(/Forge is read-only here/)).toBeVisible();
    expect(
      screen.getByText(/which parameter controls the width/),
    ).toBeVisible();
    expect(screen.queryByText(/performed no CAD writes/)).toBeNull();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Assumptions' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('list', { name: 'Evidence' }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(
      screen.getByRole('list', { name: 'Evidence' }).children,
    ).toHaveLength(3);
    expect(screen.getByText('unknown', { exact: true })).toBeVisible();
  });
  it('renders suggestions and assumptions as explicitly unverified text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          resultStream({
            ...syntheticAnswer,
            answer: "Forge is currently read-only and can't modify CAD yet.",
            discussion:
              '<script>unsafe()</script> Consider a wider mounting plate.',
            assumptions: ['Assume low static loads.'],
          }),
          { headers: { 'Content-Type': 'application/x-ndjson' } },
        ),
      ),
    );
    render(
      <Analysis context={context} csrf={'d'.repeat(64)} selection="none" />,
    );
    fill('Make this model 20 mm wider.');
    send();
    expect(
      await screen.findByText(
        "Forge is currently read-only and can't modify CAD yet.",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole('heading', { name: 'Suggestions · unverified' }),
    ).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Assumptions' })).toBeVisible();
    expect(document.querySelector('script')).toBeNull();
  });
  it('mounts meaningful evidence only on expansion and removes rows on collapse', async () => {
    fakeSuccess();
    render(tree());
    fill();
    send();
    const toggle = await screen.findByRole('button', { name: 'Evidence' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('list', { name: 'Evidence' })).toBeNull();
    fireEvent.click(toggle);
    const list = screen.getByRole('list', { name: 'Evidence' });
    expect(list).toHaveTextContent(
      'Sketch 1 is first in the returned feature list.',
    );
    for (const row of list.querySelectorAll('li')) {
      expect(
        row.querySelector('span:last-child')?.textContent?.trim(),
      ).toBeTruthy();
    }
    fireEvent.click(screen.getByRole('button', { name: 'Hide evidence' }));
    expect(screen.queryByRole('list', { name: 'Evidence' })).toBeNull();
    expect(document.querySelector('.ai-evidence li')).toBeNull();
  });
  it('omits Evidence and Suggestions cleanly when empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          resultStream({
            ...syntheticAnswer,
            evidence: [],
            uncertainties: [],
            discussion: '  ',
          }),
          { headers: { 'Content-Type': 'application/x-ndjson' } },
        ),
      ),
    );
    render(tree());
    fill();
    send();
    await screen.findByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    });
    expect(screen.queryByRole('button', { name: 'Evidence' })).toBeNull();
    expect(screen.queryByRole('list', { name: 'Evidence' })).toBeNull();
    expect(screen.queryByText('Suggestions · unverified')).toBeNull();
  });
  it('does not render an exact answer duplicate as a suggestion', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          resultStream({
            ...syntheticAnswer,
            discussion: syntheticAnswer.answer,
          }),
          { headers: { 'Content-Type': 'application/x-ndjson' } },
        ),
      ),
    );
    render(tree());
    fill();
    send();
    await screen.findByRole('heading', {
      name: /^(Response|Current model|Selected face|Selected edge)$/,
    });
    expect(screen.queryByText('Suggestions · unverified')).toBeNull();
  });
});
