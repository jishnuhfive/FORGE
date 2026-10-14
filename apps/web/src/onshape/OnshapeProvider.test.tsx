import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AuthContext } from '../auth/context';
import type { Me } from '../auth/api';
import { CadContext } from '../components/CadContext';
import { inspectorFixture } from '../cad/__fixtures__/inspector';
import { OnshapeProvider } from './OnshapeProvider';
import { useOnshapeContext } from './store';
import {
  faceSelection,
  edgeSelection,
  clearedSelection,
} from './__fixtures__/selection';
import type { ClientState } from './model';

const originalUrl = window.location.href;
const search = `?server=https://cad.onshape.com&documentId=${'a'.repeat(24)}&workspaceId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}`;
const me: Me = {
  status: 'authenticated',
  configured: true,
  display_name: 'Synthetic engineer',
  connection: 'connected',
  csrf_token: 'f'.repeat(64),
  verified_at: null,
};
afterEach(() => window.history.replaceState({}, '', originalUrl));

function setup() {
  window.history.replaceState({}, '', `/extension${search}`);
  vi.spyOn(document, 'referrer', 'get').mockReturnValue(
    'https://cad.onshape.com/',
  );
  const parent = { postMessage: vi.fn() };
  vi.stubGlobal('parent', parent);
  const fetch = vi
    .fn()
    .mockImplementation(
      async () => new Response(JSON.stringify(inspectorFixture())),
    );
  vi.stubGlobal('fetch', fetch);
  let state: ClientState | undefined;
  function Probe() {
    state = useOnshapeContext();
    return <CadContext context={{ kind: 'live', state }} />;
  }
  const view = () => (
    <OnshapeProvider>
      <AuthContext.Provider
        value={{ me, reload: vi.fn(), endSession: vi.fn() }}
      >
        <Probe />
      </AuthContext.Provider>
    </OnshapeProvider>
  );
  const rendered = render(view());
  const send = (
    data: unknown,
    origin = 'https://cad.onshape.com',
    source: unknown = parent,
  ) =>
    act(() => {
      const event = new MessageEvent('message', { data, origin });
      Object.defineProperty(event, 'source', { value: source });
      window.dispatchEvent(event);
    });
  const read = async () =>
    act(async () =>
      fireEvent.click(screen.getByRole('button', { name: 'Refresh CAD' })),
    );
  return { ...rendered, view, parent, fetch, send, read, state: () => state! };
}

it.each([faceSelection, edgeSelection])(
  'same-frame visibility/focus/show preserves context, selection and captured evidence %#',
  async (selection) => {
    const h = setup();
    h.send(selection);
    await h.read();
    const before = h.state();
    const captured = document.querySelector('time')!;
    const hidden = vi.spyOn(document, 'hidden', 'get');
    act(() => {
      hidden.mockReturnValue(true);
      document.dispatchEvent(new Event('visibilitychange'));
      window.dispatchEvent(new Event('blur'));
      hidden.mockReturnValue(false);
      document.dispatchEvent(new Event('visibilitychange'));
      window.dispatchEvent(new Event('focus'));
    });
    h.send({ messageName: 'show' });
    expect(h.state().context).toBe(before.context);
    expect(h.state().selection).toBe(before.selection);
    expect(document.querySelector('time')).toBe(captured);
    expect(captured.dateTime).toBe(inspectorFixture().source.captured_at);
    expect(screen.getByText('Sketch 1')).toBeVisible();
    expect(
      screen.queryByText('Selection needs refresh'),
    ).not.toBeInTheDocument();
    expect(h.fetch).toHaveBeenCalledTimes(1);
    expect(h.parent.postMessage).toHaveBeenCalledTimes(1);
    h.send(clearedSelection);
    expect(screen.getByText('No selection')).toBeVisible();
  },
);

it('navigation and bfcache restoration suspend old references and cannot be revived by show', async () => {
  const h = setup();
  h.send(faceSelection);
  await h.read();
  act(() =>
    window.dispatchEvent(
      new PageTransitionEvent('pagehide', { persisted: true }),
    ),
  );
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
  expect(screen.getByText('Selection needs refresh')).toBeVisible();
  act(() =>
    window.dispatchEvent(
      new PageTransitionEvent('pageshow', { persisted: true }),
    ),
  );
  h.send({ messageName: 'show' });
  h.send(edgeSelection);
  expect(h.state().selection.entities).toEqual([]);
  expect(
    screen.queryByRole('button', { name: 'Refresh CAD' }),
  ).not.toBeInTheDocument();
  expect(h.fetch).toHaveBeenCalledTimes(1);
});

it.each(['documentId', 'workspaceId', 'elementId'])(
  'a fresh frame for changed %s starts without prior inspection or selection',
  async (field) => {
    const h = setup();
    h.send(faceSelection);
    await h.read();
    h.unmount();
    const query = new URLSearchParams(search);
    query.set(field, 'e'.repeat(24));
    window.history.replaceState({}, '', `/extension?${query}`);
    render(h.view());
    expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
    expect(screen.getByText('Waiting for selection context')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Refresh CAD' })).toBeEnabled();
    expect(h.fetch).toHaveBeenCalledTimes(1);
    expect(h.parent.postMessage).toHaveBeenCalledTimes(2);
  },
);

it('actual panel destruction/recreation clears evidence even for the same launch tuple', async () => {
  const h = setup();
  h.send(faceSelection);
  await h.read();
  h.unmount();
  render(h.view());
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
  expect(screen.getByText('Waiting for selection context')).toBeVisible();
  expect(h.fetch).toHaveBeenCalledTimes(1);
  expect(h.parent.postMessage).toHaveBeenCalledTimes(2);
});

it('untrusted messages cannot change valid state or resurrect a suspended frame', async () => {
  const h = setup();
  h.send(faceSelection);
  await h.read();
  const before = h.state();
  h.send(edgeSelection, 'https://evil.example');
  h.send({ messageName: 'show' }, 'https://cad.onshape.com', {});
  expect(h.state()).toBe(before);
  expect(screen.getByText('Sketch 1')).toBeVisible();
  act(() => window.dispatchEvent(new Event('pagehide')));
  const suspended = h.state();
  h.send(faceSelection, 'https://evil.example');
  h.send({ messageName: 'show' }, 'https://cad.onshape.com', {});
  expect(h.state()).toBe(suspended);
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
});

it('malformed trusted selection clears inspection; a valid selection enables only explicit rereading', async () => {
  const h = setup();
  h.send(faceSelection);
  await h.read();
  h.send({ messageName: 'SELECTION', selections: [{ entityType: 'FACE' }] });
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
  expect(h.state().selection.entities).toEqual([]);
  h.send({ messageName: 'show' });
  expect(h.state().selection.status).toBe('unavailable');
  h.send(clearedSelection);
  expect(screen.getByRole('button', { name: 'Refresh CAD' })).toBeEnabled();
  expect(screen.queryByText('Sketch 1')).not.toBeInTheDocument();
  expect(h.fetch).toHaveBeenCalledTimes(1);
});
