import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { OnshapeClientContext } from '../onshape/model';
import { Analysis } from './Analysis';
import { parseAnswer } from './api';
import {
  resultStream,
  syntheticAnswer,
  syntheticGuide,
  syntheticGuideAnswer,
} from './__fixtures__/response';

const context: OnshapeClientContext = {
  documentId: 'a'.repeat(24),
  elementId: 'c'.repeat(24),
  revision: { kind: 'workspace', workspaceId: 'b'.repeat(24) },
  server: 'https://cad.onshape.com',
};
const ndjson = { headers: { 'Content-Type': 'application/x-ndjson' } };
function mount() {
  return render(
    <Analysis context={context} csrf={'d'.repeat(64)} selection="none" />,
  );
}
function ask(prompt: string) {
  fireEvent.change(screen.getByLabelText('Design prompt'), {
    target: { value: prompt },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Send prompt' }));
}
function stub(...results: (object | Response)[]) {
  const fetch = vi.fn();
  for (const result of results)
    fetch.mockImplementationOnce(() =>
      Promise.resolve(
        result instanceof Response
          ? result
          : new Response(resultStream(result as never), ndjson),
      ),
    );
  vi.stubGlobal('fetch', fetch);
  return fetch;
}
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('Design → Ask modeling guidance', () => {
  it('renders a numbered guide with controls, checks, mistakes and checklist', async () => {
    stub(syntheticGuideAnswer);
    mount();
    ask('Walk me through making a 60 × 40 × 10 mm plate');
    expect(
      await screen.findByRole('heading', {
        name: 'Rectangular mounting plate',
      }),
    ).toBeVisible();
    const steps = screen.getByRole('list', { name: 'Modeling steps' });
    expect(steps.children).toHaveLength(2);
    expect(screen.getByText('Operation: Remove')).toBeVisible();
    expect(screen.getByText('8 mm diameter')).toBeVisible();
    expect(screen.getAllByText(/Check:/)).toHaveLength(2);
    expect(screen.getByText('Common mistakes')).toBeVisible();
    expect(screen.getByText('Final checklist')).toBeVisible();
    expect(screen.getByText('Assumptions to confirm')).toBeVisible();
    expect(
      screen.getByText('Should the plate have rounded corners?'),
    ).toBeVisible();
    // Labelled as general and never presented as CAD evidence.
    expect(
      screen.getByText('General guidance · not from your model'),
    ).toBeVisible();
    expect(screen.getByText(/made no CAD changes/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Evidence' })).toBeNull();
  });

  it('opens one step first, keeps every step in the document and advances on demand', async () => {
    stub(syntheticGuideAnswer);
    mount();
    ask('Walk me through making a 60 × 40 × 10 mm plate');
    const steps = await screen.findByRole('list', { name: 'Modeling steps' });
    const headers = within(steps)
      .getAllByRole('button')
      .filter((button) => button.hasAttribute('aria-expanded'));
    expect(headers.map((h) => h.getAttribute('aria-expanded'))).toEqual([
      'true',
      'false',
    ]);
    // Collapsed content is inert for every reader but still part of the page.
    const second = headers[1]!.getAttribute('aria-controls')!;
    expect(document.getElementById(second)).toHaveAttribute('inert');
    expect(screen.getByText('0 of 2 done')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: /Done, next step/ }));
    expect(screen.getByText('1 of 2 done')).toBeVisible();
    expect(headers[0]).toHaveAttribute('aria-expanded', 'false');
    expect(headers[1]).toHaveAttribute('aria-expanded', 'true');
    expect(document.getElementById(second)).not.toHaveAttribute('inert');
    // Progress is the reader's own mark, never a CAD verification.
    expect(
      screen.getByRole('progressbar', {
        name: 'Your progress through the steps',
      }),
    ).toHaveAttribute('aria-valuetext', '1 of 2 steps marked done by you');
    fireEvent.click(screen.getByRole('button', { name: 'Show all steps' }));
    expect(
      headers.every((h) => h.getAttribute('aria-expanded') === 'true'),
    ).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Collapse all' }));
    expect(
      headers.some((h) => h.getAttribute('aria-expanded') === 'true'),
    ).toBe(false);
  });
  it('turns follow-up suggestions into one-tap questions that stay in guidance', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetch = stub(syntheticGuideAnswer, syntheticGuideAnswer);
    mount();
    ask('Walk me through making a plate');
    await screen.findByRole('list', { name: 'Modeling steps' });
    const chip = screen.getByRole('button', {
      name: syntheticGuide.follow_ups[0]!,
    });
    // The server's request cooldown disables the chip instead of silently ignoring it.
    expect(chip).toBeDisabled();
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(chip).toBeEnabled();
    fireEvent.click(chip);
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const body = JSON.parse(fetch.mock.calls[1]![1].body as string);
    expect(body.prompt ?? body.message ?? JSON.stringify(body)).toContain(
      syntheticGuide.follow_ups[0]!,
    );
  });
  it('keeps the rationale collapsed until requested', async () => {
    stub(syntheticGuideAnswer);
    mount();
    ask('Walk me through it');
    await screen.findByRole('list', { name: 'Modeling steps' });
    const [first] = screen.getAllByText('Why this matters');
    const details = first!.closest('details')!;
    expect(details.open).toBe(false);
    fireEvent.click(first!);
    details.open = true;
    expect(
      screen.getByText('Full constraints keep later edits predictable.'),
    ).toBeInTheDocument();
  });

  it('shows clarification questions without inventing steps', async () => {
    stub({
      ...syntheticGuideAnswer,
      guide: {
        ...syntheticGuide,
        kind: 'clarification',
        steps: [],
        mistakes: [],
        checklist: [],
        assumptions: [],
        questions: ['Where should the holes be placed?'],
      },
    });
    mount();
    ask('Help me design a bracket');
    expect(
      await screen.findByText('Where should the holes be placed?'),
    ).toBeVisible();
    expect(screen.queryByRole('list', { name: 'Modeling steps' })).toBeNull();
  });

  it('sends the previous guide as history so follow-ups stay in guidance', async () => {
    const fetch = stub(syntheticGuideAnswer, {
      ...syntheticGuideAnswer,
      answer: 'Modeling guide: Remove vs Add',
      guide: {
        ...syntheticGuide,
        kind: 'explanation',
        steps: [],
        mistakes: [],
        checklist: [],
        explanation: 'Remove subtracts material from the existing solid.',
      },
    });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mount();
    ask('Walk me through making a plate');
    await screen.findByRole('list', { name: 'Modeling steps' });
    await vi.advanceTimersByTimeAsync(6000);
    vi.useRealTimers();
    ask('Why Extrude Remove instead of Add for the holes?');
    expect(
      await screen.findByText(
        'Remove subtracts material from the existing solid.',
      ),
    ).toBeVisible();
    const body = JSON.parse(fetch.mock.calls[1]![1].body as string);
    expect(body.history[1].content).toMatch(/^Modeling guide:/);
    expect(Object.keys(body).sort()).toEqual([
      'context',
      'history',
      'prompt',
      'selection',
    ]);
    // Only the explicit read-only ask endpoint is ever called.
    expect(fetch.mock.calls.every(([url]) => url === '/api/ai/ask')).toBe(true);
  });

  it('shows a fixed message when the AI provider is unavailable', async () => {
    stub(new Response('{"detail":"x"}', { status: 500 }));
    mount();
    ask('Walk me through making a plate');
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The AI connection is unavailable.',
    );
    expect(screen.queryByRole('list', { name: 'Modeling steps' })).toBeNull();
  });

  it('keeps model explanations apart from verified evidence', async () => {
    stub({
      ...syntheticAnswer,
      explanation: 'In general, an Extrude adds or removes material.',
      guide: null,
    });
    mount();
    ask('Explain how this existing Part Studio was built');
    expect(
      await screen.findByText('Explanation · general, not verified CAD'),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Evidence' }));
    expect(
      screen.getByText('Extrude 1 is second in the returned feature list.'),
    ).toBeVisible();
    expect(
      screen.getByRole('list', { name: 'Evidence' }),
    ).not.toHaveTextContent('In general, an Extrude');
  });

  it('renders ordinary answers exactly as before', async () => {
    stub(syntheticAnswer);
    mount();
    ask('What is in this model?');
    await screen.findByRole('heading', {
      name: /^(Response|Current model)$/,
    });
    expect(
      screen.queryByText('General guidance · not from your model'),
    ).toBeNull();
    expect(screen.queryByText(/Explanation · general/)).toBeNull();
  });
});

describe('guide contract parsing', () => {
  const base = { ...syntheticGuideAnswer };
  it('accepts a valid guide and legacy answers without the new keys', () => {
    expect(parseAnswer(base).guide?.kind).toBe('guide');
    const legacy: Record<string, unknown> = { ...base };
    delete legacy.explanation;
    delete legacy.guide;
    expect(parseAnswer(legacy).evidence).toEqual([]);
  });
  it.each([
    [
      'unknown guide key',
      { ...base, guide: { ...syntheticGuide, evidence: [] } },
    ],
    ['bad kind', { ...base, guide: { ...syntheticGuide, kind: 'execute' } }],
    [
      'extra step key',
      {
        ...base,
        guide: {
          ...syntheticGuide,
          steps: [{ ...syntheticGuide.steps[0], run: 'x' }],
        },
      },
    ],
    [
      'too many steps',
      {
        ...base,
        guide: {
          ...syntheticGuide,
          steps: Array(13).fill(syntheticGuide.steps[0]),
        },
      },
    ],
    [
      'only one new key',
      Object.fromEntries(
        Object.entries(base).filter(([key]) => key !== 'guide'),
      ),
    ],
  ])('rejects %s', (_name, value) => {
    expect(() => parseAnswer(value)).toThrow();
  });
});
