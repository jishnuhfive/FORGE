import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import ReadDiagnostic from './ReadDiagnostic';
import { syntheticProof } from '../__fixtures__/proof';
import { syntheticMassStructure } from '../__fixtures__/massStructure';

it('copies only sanitized status metadata on explicit action', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
  render(<ReadDiagnostic result={syntheticProof} />);
  expect(screen.getByText(/DEVELOPMENT ONLY/)).toBeVisible();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(writeText).not.toHaveBeenCalled();
  await act(async () =>
    fireEvent.click(
      screen.getByRole('button', { name: 'Copy sanitized read diagnostic' }),
    ),
  );
  const output = writeText.mock.calls[0]![0] as string;
  expect(output.length).toBeLessThan(2000);
  expect(JSON.parse(output).requestId).toBe(syntheticProof.request_id);
  expect(output).not.toMatch(
    /count|has_mass|token|documentId|workspaceId|elementId|raw/,
  );
  expect(screen.getByRole('status')).toHaveTextContent(
    'Sanitized read diagnostic copied.',
  );
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});

it.each(['missing', 'rejected'])(
  'offers manual copying when clipboard is %s',
  async (failure) => {
    const writeText = vi.fn().mockRejectedValue(new Error('Denied'));
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: failure === 'missing' ? undefined : { writeText },
    });
    render(<ReadDiagnostic result={syntheticProof} />);
    await act(async () =>
      fireEvent.click(
        screen.getByRole('button', { name: 'Copy sanitized read diagnostic' }),
      ),
    );
    expect(screen.getByRole('status')).toHaveTextContent(
      'Clipboard unavailable — select and copy the sanitized diagnostic below.',
    );
    const textbox = screen.getByRole('textbox', {
      name: 'Sanitized read diagnostic',
    });
    expect(textbox).toBeVisible();
    expect(textbox).toHaveAttribute('readonly');
    expect(textbox).toHaveAttribute('spellcheck', 'false');
    const text = (textbox as HTMLTextAreaElement).value;
    expect(text.length).toBeLessThanOrEqual(2000);
    expect(JSON.parse(text).requestId).toBe(syntheticProof.request_id);
    if (failure === 'rejected') expect(text).toBe(writeText.mock.calls[0]![0]);
    fireEvent.focus(textbox);
    (textbox as HTMLTextAreaElement).select();
    expect((textbox as HTMLTextAreaElement).selectionEnd).toBe(text.length);
  },
);

it('clears the manual fallback after a successful copy retry', async () => {
  const writeText = vi
    .fn()
    .mockRejectedValueOnce(new Error('Denied'))
    .mockResolvedValueOnce(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
  render(<ReadDiagnostic result={syntheticProof} />);
  const button = screen.getByRole('button', {
    name: 'Copy sanitized read diagnostic',
  });
  await act(async () => fireEvent.click(button));
  expect(screen.getByRole('textbox')).toBeVisible();
  await act(async () => fireEvent.click(button));
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent(
    'Sanitized read diagnostic copied.',
  );
});

it('renders only the existing fixed projection, excluding unsafe extra fields', async () => {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: undefined,
  });
  const unsafeExtras = {
    raw: { providerResponse: 'synthetic-private-provider-body' },
    access_token: 'synthetic-access-token',
    refresh_token: 'synthetic-refresh-token',
    client_secret: 'synthetic-client-secret',
    documentId: 'a'.repeat(24),
    workspaceId: 'b'.repeat(24),
    elementId: 'c'.repeat(24),
    selectionId: 'synthetic-selection-reference',
    providerUrl: 'https://synthetic-provider.invalid/private',
  };
  render(
    <ReadDiagnostic
      result={{
        ...syntheticProof,
        ...unsafeExtras,
        mass: {
          ...syntheticProof.mass,
          status: 'provider_failure',
          code: 'invalid_response',
          count: null,
          ...unsafeExtras,
        },
      }}
    />,
  );
  await act(async () =>
    fireEvent.click(
      screen.getByRole('button', { name: 'Copy sanitized read diagnostic' }),
    ),
  );
  const text = (screen.getByRole('textbox') as HTMLTextAreaElement).value;
  expect(JSON.parse(text)).toEqual({
    diagnostic: 'forge-rest-diagnostic-v1',
    requestId: syntheticProof.request_id,
    capturedAt: syntheticProof.captured_at,
    consistency: syntheticProof.consistency,
    sections: {
      features: { status: 'success', code: 'ok', retryAfterSeconds: null },
      parts: { status: 'success', code: 'ok', retryAfterSeconds: null },
      bodies: { status: 'success', code: 'ok', retryAfterSeconds: null },
      mass: {
        status: 'provider_failure',
        code: 'invalid_response',
        retryAfterSeconds: null,
      },
    },
  });
  for (const value of Object.values(unsafeExtras)) {
    expect(text).not.toContain(
      typeof value === 'string' ? value : JSON.stringify(value),
    );
  }
});

it('fails closed for a report exceeding the output bound', async () => {
  const writeText = vi.fn();
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
  render(
    <ReadDiagnostic
      result={{ ...syntheticProof, captured_at: 'x'.repeat(2001) }}
    />,
  );
  await act(async () =>
    fireEvent.click(
      screen.getByRole('button', { name: 'Copy sanitized read diagnostic' }),
    ),
  );
  expect(writeText).not.toHaveBeenCalled();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent(
    'Sanitized read diagnostic exceeds the size limit.',
  );
});

it('does not render outside development', () => {
  vi.stubEnv('DEV', false);
  try {
    const { container } = render(
      <ReadDiagnostic
        result={{
          ...syntheticProof,
          massStructure: JSON.stringify(syntheticMassStructure, null, 2),
        }}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  } finally {
    vi.unstubAllEnvs();
  }
});

it('offers the validated mass structure for manual copying without altering the read report', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  });
  const text = JSON.stringify(syntheticMassStructure, null, 2);
  render(
    <ReadDiagnostic result={{ ...syntheticProof, massStructure: text }} />,
  );
  const textbox = screen.getByRole('textbox', {
    name: 'Sanitized mass response structure',
  });
  expect(textbox).toHaveValue(text);
  expect(textbox).toHaveAttribute('readonly');
  expect(textbox).toHaveAttribute('spellcheck', 'false');
  await act(async () =>
    fireEvent.click(
      screen.getByRole('button', { name: 'Copy sanitized read diagnostic' }),
    ),
  );
  expect(writeText.mock.calls[0]![0]).not.toContain('forge-mass-structure-v1');
  expect(textbox).toHaveValue(text);
});
