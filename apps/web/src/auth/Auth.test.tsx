import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { App } from '../App';
import { parseMe } from './api';

const signedOut = {
  status: 'signed_out',
  configured: true,
  display_name: null,
  connection: null,
  csrf_token: null,
  verified_at: null,
};
const signedIn = {
  ...signedOut,
  status: 'authenticated',
  display_name: 'Test Engineer',
  connection: 'connected',
  csrf_token: 'a'.repeat(64),
  verified_at: 1_700_000_000,
};
const json = (data: object) =>
  new Response(JSON.stringify(data), {
    headers: { 'Content-Type': 'application/json' },
  });

beforeEach(() => {
  window.location.hash = '';
  localStorage.clear();
  localStorage.setItem(
    'forge.preferences.v1',
    JSON.stringify({ onboarded: true }),
  );
});

it('shows signed-out screen and a top-level Onshape login action', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(signedOut)));
  render(<App />);
  const link = await screen.findByRole('link', {
    name: 'Continue with Onshape',
  });
  expect(link).toHaveAttribute('href', '/auth/onshape/start');
  expect(link).toHaveAttribute('target', '_top');
  expect(screen.queryByLabelText('Design prompt')).not.toBeInTheDocument();
  // Prevent jsdom navigation, while still testing the authorizing feedback.
  link.addEventListener('click', (event) => event.preventDefault());
  fireEvent.click(link);
  expect(screen.getByText('Opening Onshape…')).toBeVisible();
});

it('shows a safe unconfigured state without pretending authentication works', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(json({ ...signedOut, configured: false })),
  );
  render(<App />);
  expect(
    await screen.findByText(/awaiting server configuration/),
  ).toBeVisible();
  expect(
    screen.queryByRole('link', { name: 'Continue with Onshape' }),
  ).not.toBeInTheDocument();
});

it('loads the authenticated workspace and account settings', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() => Promise.resolve(json(signedIn))),
  );
  render(<App />);
  expect(await screen.findByLabelText('Design prompt')).toBeVisible();
  fireEvent.keyDown(screen.getByRole('button', { name: 'Workspace menu' }), {
    key: 'ArrowDown',
  });
  fireEvent.click(
    await screen.findByRole('menuitem', { name: 'Appearance & settings' }),
  );
  expect(await screen.findByText('Onshape account')).toBeVisible();
  expect(screen.getByText('Connected')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Sign out' })).toBeEnabled();
});

it('signs out with a CSRF-protected POST', async () => {
  window.location.hash = '/settings';
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(json(signedIn))
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValue(json(signedOut));
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }));
  expect(
    await screen.findByRole('link', { name: 'Continue with Onshape' }),
  ).toBeVisible();
  expect(fetch).toHaveBeenCalledWith(
    '/auth/logout',
    expect.objectContaining({
      method: 'POST',
      headers: { 'X-CSRF-Token': signedIn.csrf_token },
    }),
  );
  expect(localStorage.getItem('forge.preferences.v1')).not.toContain(
    signedIn.csrf_token,
  );
});

it('requires confirmation and distinguishes local disconnect from remote revocation', async () => {
  window.location.hash = '/settings';
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(json(signedIn))
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValue(json({ ...signedIn, connection: 'disconnected' }));
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  fireEvent.click(
    await screen.findByRole('button', { name: 'Disconnect Onshape' }),
  );
  expect(screen.getByRole('dialog')).toBeVisible();
  expect(fetch).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Confirm disconnect' }));
  expect(await screen.findByText('Reconnect required')).toBeVisible();
  expect(screen.getByText(/Forge removed its stored access/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Sign out' })).toBeVisible();
});

it.each(['revoked', 'error', 'disconnected'])(
  'offers reconnect for %s authorization',
  async (connection) => {
    window.location.hash = '/settings';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(json({ ...signedIn, connection })),
    );
    render(<App />);
    expect(
      await screen.findByRole('link', { name: 'Reconnect Onshape' }),
    ).toHaveAttribute('href', '/auth/onshape/start');
  },
);

it('explains authorization denial without reflecting raw provider text', async () => {
  window.location.hash = '/auth/authorization_denied';
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(signedOut)));
  render(<App />);
  expect(await screen.findByText(/Authorization was denied/)).toBeVisible();
});

it('explains session expiry and requires fresh login', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(json({ ...signedOut, status: 'session_expired' })),
  );
  render(<App />);
  expect(await screen.findByText(/session has expired/)).toBeVisible();
});

it('shows recoverable network errors without exception text', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockRejectedValueOnce(new Error('private-debug-details'))
      .mockResolvedValue(json(signedOut)),
  );
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
  expect(
    await screen.findByRole('link', { name: 'Continue with Onshape' }),
  ).toBeVisible();
  expect(screen.queryByText('private-debug-details')).not.toBeInTheDocument();
});

it('keeps the UI lab independent from authentication', async () => {
  window.location.hash = '/lab';
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  await screen.findByText('Forge UI lab');
  await waitFor(() => expect(fetch).not.toHaveBeenCalled());
});

it.each([
  { ...signedIn, csrf_token: 'bad' },
  { ...signedIn, status: ['authenticated'] },
  { ...signedIn, access_token: 'must-never-be-returned' },
  { ...signedIn, display_name: null },
  { ...signedIn, connection: 'unknown' },
])('rejects invalid authentication responses', (value) => {
  expect(() => parseMe(value)).toThrow('Invalid auth response');
});

it('preserves local drafts during a transient session-status network failure', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(json(signedIn))
    .mockRejectedValue(new Error('offline'));
  vi.stubGlobal('fetch', fetch);
  render(<App />);
  fireEvent.change(await screen.findByLabelText('Design prompt'), {
    target: { value: 'Keep my draft' },
  });
  fireEvent(window, new Event('focus'));
  expect(
    await screen.findByText(/Your local draft is still here/),
  ).toBeVisible();
  expect(screen.getByLabelText('Design prompt')).toHaveValue('Keep my draft');
});
