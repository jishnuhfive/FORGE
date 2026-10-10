import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { OnshapeContext } from '../store';
import { parseLaunch } from '../context';
import SelectionDiagnostic from './SelectionDiagnostic';
import { captureSelectionStructure, resetDiagnostics } from './diagnostics';
const launch = parseLaunch(
  `?server=https://cad.onshape.com&documentId=${'a'.repeat(24)}&workspaceId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}`,
  true,
  true,
);
afterEach(() => {
  resetDiagnostics();
  vi.unstubAllEnvs();
});
it('requires opt-in, displays only sanitized output, copies it on user click and clears it', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
  render(
    <OnshapeContext.Provider value={launch}>
      <SelectionDiagnostic />
    </OnshapeContext.Provider>,
  );
  expect(
    screen.queryByLabelText('Sanitized structure'),
  ).not.toBeInTheDocument();
  fireEvent.click(
    screen.getByRole('button', {
      name: 'Enable sanitized selection diagnostic',
    }),
  );
  expect(
    screen.getByRole('button', { name: 'Copy sanitized structure' }),
  ).toBeDisabled();
  act(() =>
    captureSelectionStructure({
      messageName: 'SELECTION',
      data: { entityType: 'FACE', entityId: 'private-id' },
    }),
  );
  const sanitized = (
    screen.getByLabelText('Sanitized structure') as HTMLTextAreaElement
  ).value;
  expect(sanitized).not.toContain('private-id');
  fireEvent.click(
    screen.getByRole('button', { name: 'Copy sanitized structure' }),
  );
  expect(await screen.findByText('Sanitized structure copied.')).toBeVisible();
  expect(writeText).toHaveBeenCalledExactlyOnceWith(sanitized);
  fireEvent.click(screen.getByRole('button', { name: 'Clear diagnostic' }));
  expect(
    screen.queryByLabelText('Sanitized structure'),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Disable diagnostic' }));
  expect(
    screen.getByRole('button', {
      name: 'Enable sanitized selection diagnostic',
    }),
  ).toBeVisible();
});
it('has no UI in standalone or production', () => {
  const first = render(<SelectionDiagnostic />);
  expect(first.container).toBeEmptyDOMElement();
  first.unmount();
  vi.stubEnv('DEV', false);
  const second = render(
    <OnshapeContext.Provider value={launch}>
      <SelectionDiagnostic />
    </OnshapeContext.Provider>,
  );
  expect(second.container).toBeEmptyDOMElement();
});
