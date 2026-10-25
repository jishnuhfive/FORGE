import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { Creation } from './Creation';
const context = {
  documentId: 'a'.repeat(24),
  workspaceId: 'b'.repeat(24),
  elementId: 'c'.repeat(24),
};
const brief = {
  kind: 'rect_plate_with_through_holes',
  width: { value: 60, unit: 'mm' },
  length: { value: 40, unit: 'mm' },
  thickness: { value: 10, unit: 'mm' },
  holes: [],
};
const preview = {
  proposal_id: 'a'.repeat(43),
  digest: 'b'.repeat(64),
  brief,
  plan: {
    steps: [
      { op: { operation: 'CREATE_SKETCH_RECT' } },
      { op: { operation: 'EXTRUDE_NEW' } },
    ],
  },
};
afterEach(() => vi.unstubAllGlobals());
async function setup() {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'ready', brief })),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify(preview)));
  vi.stubGlobal('fetch', fetch);
  render(<Creation context={context} csrf={'c'.repeat(64)} />);
  fireEvent.change(screen.getByLabelText('Creation request'), {
    target: { value: 'Create a 60 by 40 by 10 mm plate with no holes' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Interpret creation request' }),
  );
  await screen.findByText(/Width 60 mm/);
  fireEvent.click(
    screen.getByRole('button', { name: 'Prepare creation preview' }),
  );
  await screen.findByText('New-body extrusion');
  return fetch;
}
it('requires explicit brief confirmation and sends one approval', async () => {
  const fetch = await setup();
  const approve = screen.getByRole('button', { name: 'Approve creation once' });
  expect(approve).toBeDisabled();
  fetch.mockResolvedValueOnce(
    new Response(JSON.stringify({ state: 'verified_success' })),
  );
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(approve);
  fireEvent.click(approve);
  await screen.findByText(/Creation verified by fresh provider evidence/);
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(approve).toBeDisabled();
});
it('cancel never calls approval', async () => {
  const fetch = await setup();
  fetch.mockResolvedValueOnce(
    new Response(JSON.stringify({ state: 'cancelled' })),
  );
  fireEvent.click(screen.getByRole('button', { name: 'Cancel creation' }));
  await screen.findByText(/Creation cancelled/);
  expect(String(fetch.mock.calls[2]?.[0])).toContain('/cancel');
  expect(
    fetch.mock.calls.some((call) => String(call[0]).includes('/approve')),
  ).toBe(false);
});
it('lost acknowledgement never retries approval or reports success', async () => {
  const fetch = await setup();
  fetch.mockRejectedValueOnce(new Error('network'));
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(
    screen.getByRole('button', { name: 'Approve creation once' }),
  );
  await screen.findByText(/Completion is unconfirmed/);
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Approve creation once' }),
    ).toBeDisabled(),
  );
  expect(fetch).toHaveBeenCalledTimes(3);
});
