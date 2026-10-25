import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Create } from './Create';
import { ready, proposalId, verified } from './__fixtures__/plate';
import type { OnshapeClientContext } from '../onshape/model';

const context: OnshapeClientContext = {
  documentId: 'a'.repeat(24),
  elementId: 'c'.repeat(24),
  server: 'https://cad.onshape.com',
  revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
};
const csrf = 'f'.repeat(64);
const REQUEST =
  'Make a 60 by 40 by 10 mm plate with an 8 mm centered through-hole.';

type Handler = (url: string, init: RequestInit) => unknown;
let calls: { url: string; init: RequestInit }[] = [];
function mock(handler: Handler) {
  calls = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      const out = (await handler(url, init)) as {
        status?: number;
        body: unknown;
      };
      return new Response(JSON.stringify(out.body), {
        status: out.status ?? 200,
        headers: { 'content-type': 'application/json' },
      });
    }),
  );
}
const ok = (body: unknown) => ({ body });
const userEvent = {
  type: async (el: HTMLElement, value: string) => {
    fireEvent.change(el, { target: { value } });
  },
  click: async (el: HTMLElement) => {
    fireEvent.click(el);
  },
};
async function submit(text = REQUEST) {
  render(<Create context={context} csrf={csrf} />);
  await userEvent.type(screen.getByLabelText('Part request'), text);
  await userEvent.click(screen.getByRole('button', { name: 'Prepare brief' }));
}
const approveButton = () =>
  screen.getByRole('button', { name: /Approve and build/ });

beforeEach(() => vi.useRealTimers());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('Create flow', () => {
  it('starts as an empty request with nothing built', () => {
    render(<Create context={context} csrf={csrf} />);
    expect(screen.getByText('Describe a part')).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Prepare brief' }),
    ).toHaveProperty('disabled', true);
    expect(
      (screen.getByLabelText('Part request') as HTMLTextAreaElement)
        .placeholder,
    ).toContain('60 by 40 by 10 mm plate');
  });

  it('sends only the request text and scoped context', async () => {
    mock(() => ok(ready()));
    await submit();
    await screen.findByRole('heading', { name: 'Engineering brief' });
    expect(calls).toHaveLength(1);
    expect(calls[0]!.url).toBe('/api/create/plan');
    expect(JSON.parse(calls[0]!.init.body as string)).toEqual({
      context: {
        documentId: context.documentId,
        workspaceId: 'b'.repeat(24),
        elementId: context.elementId,
        revisionKind: 'workspace',
      },
      request: REQUEST,
    });
    expect(
      (calls[0]!.init.headers as Record<string, string>)['X-CSRF-Token'],
    ).toBe(csrf);
  });

  it('shows an interpreting state while the planner runs', async () => {
    let release: (v: unknown) => void = () => {};
    const gate = new Promise((r) => (release = r));
    mock(async () => {
      await gate;
      return ok(ready());
    });
    await submit();
    expect(screen.getByText('Interpreting')).toBeTruthy();
    expect(screen.getByLabelText('Part request')).toHaveProperty(
      'disabled',
      true,
    );
    release(null);
    await screen.findByText('Ready for review');
  });

  it('asks for clarification with server-owned questions and builds nothing', async () => {
    mock(() =>
      ok({
        status: 'needs_clarification',
        reason: 'missing_dimension',
        fields: ['thickness', 'hole_diameter'],
        questions: [
          'What is the thickness?',
          'What diameter should the hole(s) be?',
        ],
      }),
    );
    await submit('Make a plate with a hole');
    const section = await screen.findByRole('region', {
      name: 'Clarification needed',
    });
    expect(screen.getByText('Needs clarification')).toBeTruthy();
    expect(within(section).getByText('Thickness')).toBeTruthy();
    expect(within(section).getByText(/What is the thickness\?/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Approve/ })).toBeNull();
    // The request stays editable so the user can add detail.
    expect(
      (screen.getByLabelText('Part request') as HTMLTextAreaElement).value,
    ).toBe('Make a plate with a hole');
  });

  it('explains unsupported requests and rejected geometry', async () => {
    mock(() =>
      ok({
        status: 'unsupported',
        reason: 'unsupported_object',
        message: 'Forge cannot create that kind of part yet.',
      }),
    );
    await submit('Make a gearbox');
    await screen.findByRole('region', { name: 'Unsupported request' });
    expect(screen.getByText('Unsupported')).toBeTruthy();
    expect(
      screen.getByText('Forge cannot create that kind of part yet.'),
    ).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Approve/ })).toBeNull();
    cleanup();
    mock(() => ok({ status: 'rejected', code: 'holes_overlap' }));
    await submit('two huge holes');
    expect(await screen.findByText('Two holes would overlap.')).toBeTruthy();
  });

  it('displays the engineering brief with explicit units', async () => {
    mock(() => ok(ready()));
    await submit();
    const brief = await screen.findByRole('region', {
      name: 'Engineering brief',
    });
    expect(within(brief).getByText('Width').nextSibling?.textContent).toBe(
      '60 mm',
    );
    expect(
      within(brief).getByText('Length (depth)').nextSibling?.textContent,
    ).toBe('40 mm');
    expect(within(brief).getByText('Thickness').nextSibling?.textContent).toBe(
      '10 mm',
    );
    expect(within(brief).getByText('1 through-hole')).toBeTruthy();
    expect(within(brief).getByText(/Ø 8 mm · centered/)).toBeTruthy();
    expect(screen.getByText(REQUEST, { exact: false })).toBeTruthy();
  });

  it('requires visible human confirmation before approval can be sent', async () => {
    mock(() => ok(ready()));
    await submit();
    await screen.findByText('Ready for review');
    expect(approveButton()).toHaveProperty('disabled', true);
    expect(screen.getByText('Needs your review')).toBeTruthy();
    expect(
      screen.getByText(/Confirm the engineering brief above/),
    ).toBeTruthy();
    fireEvent.click(approveButton());
    expect(calls).toHaveLength(1); // only the planning call
    await userEvent.click(
      screen.getByRole('checkbox', { name: /checked these dimensions/ }),
    );
    expect(screen.getByText('Reviewed')).toBeTruthy();
    expect(approveButton()).toHaveProperty('disabled', false);
  });

  it('lists the feature plan in order with editable-parametric framing', async () => {
    mock(() => ok(ready()));
    await submit();
    const list = await screen.findByRole('list', { name: 'Planned features' });
    expect(screen.getByText('Parametric')).toBeTruthy();
    expect(
      screen.getByText(/stays editable in the Onshape feature tree/),
    ).toBeTruthy();
    const titles = within(list)
      .getAllByRole('heading', { level: 3 })
      .map((h) => h.textContent);
    expect(titles).toEqual([
      'Create base rectangle sketch',
      'Extrude base body',
      'Create hole sketch',
      'Remove material',
    ]);
  });

  it('shows a concise server-owned Learn explanation for every step', async () => {
    mock(() => ok(ready()));
    await submit();
    const list = await screen.findByRole('list', { name: 'Planned features' });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(4);
    for (const item of items)
      expect(within(item).getByText('Why this step')).toBeTruthy();
    expect(
      screen.getByText('Cut the sketched shape out of the solid.'),
    ).toBeTruthy();
  });

  async function approved(approve: Handler) {
    mock((url, init) =>
      url.endsWith('/plan') ? ok(ready()) : approve(url, init),
    );
    await submit();
    await userEvent.click(
      await screen.findByRole('checkbox', { name: /checked these dimensions/ }),
    );
    await userEvent.click(approveButton());
  }

  it('binds approval to the plan digest and brief confirmation, once', async () => {
    let release: (v: unknown) => void = () => {};
    const gate = new Promise((r) => (release = r));
    await approved(async () => {
      await gate;
      return ok(verified);
    });
    expect(screen.getByText('Approved · building')).toBeTruthy();
    expect(screen.getByText(/Building and verifying in Onshape/)).toBeTruthy();
    expect(screen.queryByText('Verified')).toBeNull();
    const approval = calls[1]!;
    expect(approval.url).toBe(`/api/create/plans/${proposalId}/approve`);
    expect(JSON.parse(approval.init.body as string)).toEqual({
      digest: 'a'.repeat(64),
      brief_confirmed: true,
    });
    release(null);
    await screen.findByRole('region', { name: 'Result' });
    expect(calls).toHaveLength(2);
    expect(
      screen.queryByRole('button', { name: /Approve and build/ }),
    ).toBeNull();
  });

  it('reports verified success only from a fully verified result, then offers Learn', async () => {
    await approved(() => ok(verified));
    const result = await screen.findByRole('region', { name: 'Result' });
    expect(within(result).getByText('Verified')).toBeTruthy();
    expect(within(result).getByText(/4 of 4 steps verified/)).toBeTruthy();
    const learn = screen.getByRole('region', {
      name: 'Learn how FORGE built this',
    });
    expect(within(learn).getByText('Step 1 of 4')).toBeTruthy();
    expect(
      within(learn).getByText('Create base rectangle sketch'),
    ).toBeTruthy();
    expect(within(learn).getByText(/60 mm × 40 mm rectangle/)).toBeTruthy();
    await userEvent.click(
      within(learn).getByRole('button', { name: 'Next step' }),
    );
    expect(within(learn).getByText('Step 2 of 4')).toBeTruthy();
    expect(within(learn).getByText('Extrude base body')).toBeTruthy();
    expect(
      within(learn).getByText(
        'Extrude the outline into a solid so there is material to cut.',
      ),
    ).toBeTruthy();
    // Learn is read-only: walking through it sends nothing.
    for (let i = 0; i < 2; i++)
      await userEvent.click(
        within(learn).getByRole('button', { name: 'Next step' }),
      );
    expect(within(learn).getByText('Step 4 of 4')).toBeTruthy();
    expect(calls).toHaveLength(2);
  });

  it('does not offer Learn or claim success after a partial failure', async () => {
    await approved(() =>
      ok({
        state: 'partial_failure',
        steps: [
          'verified_success',
          'verified_success',
          'write_failed',
          'skipped',
        ],
      }),
    );
    const result = await screen.findByRole('region', { name: 'Result' });
    expect(within(result).getByText('Build stopped')).toBeTruthy();
    expect(within(result).getByText(/2 of 4 steps verified/)).toBeTruthy();
    expect(screen.queryByText('Learn how FORGE built this')).toBeNull();
    expect(screen.queryByText('Verified', { selector: 'h2' })).toBeNull();
  });

  it('treats transport failure after dispatch as uncertain and never retries', async () => {
    await approved(() => {
      throw new Error('network');
    });
    const result = await screen.findByRole('region', { name: 'Result' });
    expect(
      within(result).getByText('Forge could not confirm the result'),
    ).toBeTruthy();
    expect(
      within(result).getByText(/will not retry this approval/),
    ).toBeTruthy();
    expect(screen.queryByText('Learn how FORGE built this')).toBeNull();
    expect(calls.filter((c) => c.url.endsWith('/approve'))).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Check status' })).toBeTruthy();
  });

  it('checks status with GET and can then verify', async () => {
    let first = true;
    await approved((_url, init) => {
      if (init.method === 'GET') return ok(verified);
      if (first) {
        first = false;
        throw new Error('network');
      }
      return ok(verified);
    });
    await userEvent.click(
      await screen.findByRole('button', { name: 'Check status' }),
    );
    await screen.findByText('Learn how FORGE built this');
    const status = calls.at(-1)!;
    expect(status.init.method).toBe('GET');
    expect(status.url).toBe(`/api/create/plans/${proposalId}`);
  });

  it('stops with the model-changed message when the model is stale', async () => {
    await approved(() =>
      ok({
        state: 'rejected_stale',
        steps: ['rejected_stale', 'skipped', 'skipped', 'skipped'],
      }),
    );
    expect(
      await screen.findByText('Model changed', { selector: 'h2' }),
    ).toBeTruthy();
    expect(screen.getByText(/nothing was applied/)).toBeTruthy();
  });

  it('rejects a malformed server result rather than showing success', async () => {
    await approved(() =>
      ok({ state: 'verified_success', steps: ['verified_success'] }),
    );
    const result = await screen.findByRole('region', { name: 'Result' });
    expect(
      within(result).getByText('Forge could not confirm the result'),
    ).toBeTruthy();
    expect(screen.queryByText('Learn how FORGE built this')).toBeNull();
  });

  it('surfaces planner service errors without a plan', async () => {
    mock(() => ({ status: 503, body: { detail: 'service_unavailable' } }));
    await submit();
    expect(
      await screen.findByText('The service is unavailable. Try again shortly.'),
    ).toBeTruthy();
    expect(
      screen.queryByRole('heading', { name: 'Engineering brief' }),
    ).toBeNull();
  });

  it('lets the human edit the request, discarding the unapproved plan', async () => {
    mock(() => ok(ready()));
    await submit();
    await userEvent.click(
      await screen.findByRole('button', { name: 'Edit request' }),
    );
    expect(
      screen.queryByRole('region', { name: 'Engineering brief' }),
    ).toBeNull();
    expect(
      (screen.getByLabelText('Part request') as HTMLTextAreaElement).value,
    ).toBe(REQUEST);
  });
});

describe('busy reporting', () => {
  it('reports busy while interpreting and clears afterwards', async () => {
    let release: (v: unknown) => void = () => {};
    const gate = new Promise((r) => (release = r));
    mock(async () => {
      await gate;
      return ok(ready());
    });
    const seen: boolean[] = [];
    render(
      <Create
        context={context}
        csrf={csrf}
        onBusyChange={(b) => seen.push(b)}
      />,
    );
    await userEvent.type(screen.getByLabelText('Part request'), REQUEST);
    await userEvent.click(
      screen.getByRole('button', { name: 'Prepare brief' }),
    );
    expect(seen.at(-1)).toBe(true);
    release(null);
    await screen.findByText('Ready for review');
    expect(seen.at(-1)).toBe(false);
  });
});
