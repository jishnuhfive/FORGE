import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import LaunchDiagnostic from './LaunchDiagnostic';
afterEach(() => {
  window.history.replaceState(null, '', '/');
  vi.unstubAllEnvs();
});
it('shows and copies only sanitized launch information even without valid context', async () => {
  window.history.replaceState(
    null,
    '',
    `/extension?documentId=synthetic-private-id&clientId=${'x'.repeat(129)}&server=https://cad.onshape.com`,
  );
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  render(<LaunchDiagnostic />);
  expect(
    screen.queryByLabelText('Sanitized launch context'),
  ).not.toBeInTheDocument();
  fireEvent.click(
    screen.getByRole('button', { name: 'Show sanitized launch diagnostic' }),
  );
  const text = (
    screen.getByLabelText('Sanitized launch context') as HTMLTextAreaElement
  ).value;
  expect(text).toContain('invalid-opaque-metadata');
  expect(text).not.toContain('synthetic-private-id');
  expect(text).not.toContain('x'.repeat(129));
  fireEvent.click(
    screen.getByRole('button', { name: 'Copy sanitized launch diagnostic' }),
  );
  expect(
    await screen.findByText('Sanitized launch diagnostic copied.'),
  ).toBeVisible();
  expect(writeText).toHaveBeenCalledExactlyOnceWith(text);
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole('button', { name: 'Clear launch diagnostic' }),
  );
  expect(
    screen.queryByLabelText('Sanitized launch context'),
  ).not.toBeInTheDocument();
});
it('offers manual copying when clipboard access is denied', async () => {
  window.history.replaceState(null, '', '/extension');
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: {
      writeText: vi.fn().mockRejectedValue(new Error('synthetic-denial')),
    },
  });
  render(<LaunchDiagnostic />);
  fireEvent.click(
    screen.getByRole('button', { name: 'Show sanitized launch diagnostic' }),
  );
  fireEvent.click(
    screen.getByRole('button', { name: 'Copy sanitized launch diagnostic' }),
  );
  expect(
    await screen.findByText('Select the sanitized text and copy it manually.'),
  ).toBeVisible();
});
it('is absent outside the extension and in production', () => {
  const first = render(<LaunchDiagnostic />);
  expect(first.container).toBeEmptyDOMElement();
  first.unmount();
  window.history.replaceState(null, '', '/extension?diagnostics=true');
  vi.stubEnv('DEV', false);
  expect(render(<LaunchDiagnostic />).container).toBeEmptyDOMElement();
});
