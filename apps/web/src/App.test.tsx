import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Workspace as App } from './App';

function route(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
}
function dismissIntro() {
  fireEvent.click(screen.getByRole('button', { name: 'Skip introduction' }));
}
function ready() {
  localStorage.setItem(
    'forge.preferences.v1',
    JSON.stringify({ onboarded: true }),
  );
}

beforeEach(() => {
  localStorage.clear();
  window.location.hash = '';
});

describe('Forge application foundation', () => {
  it('renders the workspace, brand, purpose and first-run introduction', () => {
    render(<App />);
    expect(
      screen.getByRole('dialog', { name: 'Welcome to Forge' }),
    ).toBeVisible();
    expect(screen.getByText(/AI engineering inside Onshape/)).toBeVisible();
    dismissIntro();
    expect(screen.getByRole('main')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Forge workspace' })).toBeVisible();
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Ask about this Part Studio',
      }),
    ).toBeVisible();
    expect(screen.getByText('Local design draft')).toBeVisible();
  });
  it('persists skipped onboarding and does not reopen on a new mount', () => {
    const first = render(<App />);
    dismissIntro();
    first.unmount();
    render(<App />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(
      JSON.parse(localStorage.getItem('forge.preferences.v1') ?? '{}')
        .onboarded,
    ).toBe(true);
  });
  it('switches Design, Modify and Learn modes using keyboard controls', () => {
    ready();
    render(<App />);
    const modify = screen.getByRole('tab', { name: 'Modify' });
    fireEvent.keyDown(modify, { key: 'Enter' });
    expect(
      screen.getByRole('heading', { name: 'Refine with intention.' }),
    ).toBeVisible();
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Learn' }), {
      key: 'Enter',
    });
    expect(
      screen.getByRole('heading', { name: 'Learn with Forge' }),
    ).toBeVisible();
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Design' }), {
      key: 'Enter',
    });
    expect(screen.getByLabelText('Design prompt')).toBeVisible();
  });
  it('keeps a prompt local and does not send network requests', () => {
    ready();
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    fireEvent.change(screen.getByLabelText('Design prompt'), {
      target: { value: 'A compact motor mount' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send prompt' }));
    expect(screen.getByText('Your local draft')).toBeVisible();
    expect(screen.getByText(/has not been sent to a service/)).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
    expect(localStorage.getItem('forge.preferences.v1')).not.toContain(
      'A compact motor mount',
    );
  });
  it('supports settings navigation and persistent theme preference', async () => {
    ready();
    render(<App />);
    route('/settings');
    fireEvent.click(screen.getByLabelText('Dark', { exact: true }));
    expect(document.documentElement.dataset.theme).toBe('dark');
    fireEvent.click(screen.getByLabelText('Light', { exact: true }));
    expect(document.documentElement.dataset.theme).toBe('light');
    fireEvent.click(screen.getByLabelText('Imperial', { exact: true }));
    expect(
      JSON.parse(localStorage.getItem('forge.preferences.v1') ?? '{}').units,
    ).toBe('imperial');
    fireEvent.click(screen.getByRole('button', { name: /Back to workspace/ }));
    expect(
      await screen.findByRole('heading', {
        name: 'Ask about this Part Studio',
      }),
    ).toBeVisible();
  });
  it('sanitizes invalid browser preferences without crashing', () => {
    localStorage.setItem(
      'forge.preferences.v1',
      JSON.stringify({
        theme: 'neon',
        width: -1,
        depth: 99999,
        height: 'oops',
        printer: 32,
      }),
    );
    window.location.hash = '/settings';
    render(<App />);
    dismissIntro();
    expect(screen.getByLabelText('Bed width (mm)')).toHaveValue(220);
    expect(screen.getByLabelText('Bed depth (mm)')).toHaveValue(220);
    expect(screen.getByLabelText('Build height (mm)')).toHaveValue(250);
    expect(screen.getByLabelText('Dark', { exact: true })).toBeChecked();
  });
  it('handles malformed storage', () => {
    localStorage.setItem('forge.preferences.v1', '{invalid');
    render(<App />);
    expect(screen.getByRole('dialog')).toBeVisible();
  });
  it('preserves session interaction when persistence is unavailable', () => {
    ready();
    render(<App />);
    route('/settings');
    fireEvent.click(screen.getByLabelText('Light', { exact: true }));
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage unavailable');
    });
    fireEvent.click(screen.getByLabelText('Dark', { exact: true }));
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(
      screen.getByText(/Preferences last for this session only/),
    ).toBeVisible();
  });
  it('persists only the allowlisted reduced transparency preference', () => {
    ready();
    render(<App />);
    route('/settings');
    fireEvent.click(screen.getByLabelText('Reduce transparency'));
    expect(document.documentElement.dataset.transparency).toBe('reduced');
    expect(
      JSON.parse(localStorage.getItem('forge.preferences.v1') ?? '{}')
        .reduceTransparency,
    ).toBe(true);
  });
  it('shows empty history without synthetic real project records', () => {
    ready();
    window.location.hash = '/history';
    render(<App />);
    expect(screen.getByText('No history yet')).toBeVisible();
    expect(screen.queryByText('Camera Slider')).not.toBeInTheDocument();
  });
  it('loads the explicitly labeled development-only preview', async () => {
    window.location.hash = '/lab';
    render(<App />);
    expect(await screen.findByText('Forge UI lab')).toBeVisible();
    expect(
      screen.getByText(
        /All project data, progress and validation are mock previews/,
      ),
    ).toBeVisible();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Preview state'), {
      target: { value: 'Plan' },
    });
    expect(
      screen.getByRole('heading', { name: 'A plan before a part' }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: /Approve and Build/ }));
    expect(screen.getByText('No agent executing')).toBeVisible();
  });
});
