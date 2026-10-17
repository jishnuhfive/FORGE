import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AnswerContent } from './Analysis';
import type { Answer } from './api';
import { syntheticAnswer, syntheticOverview } from './__fixtures__/response';

const smallTalk: Answer = {
  answer:
    'Hi! I am Forge, a read-only engineering assistant for this Part Studio.',
  evidence: [],
  uncertainties: [],
  discussion: '',
  assumptions: [],
  follow_up_questions: [
    'What features does my model have?',
    'Explain my model.',
  ],
  capability_state: 'read_only',
  captured_at: null,
};

describe('conversational framing', () => {
  it('leads a model summary with a friendly line, and adds nothing about the model', () => {
    render(<AnswerContent result={syntheticOverview} />);
    expect(
      screen.getByText('Here’s what I can see in your Part Studio.'),
    ).toBeVisible();
    expect(
      screen.getByText('Ask me about any feature, or what to check next.'),
    ).toBeVisible();
  });
  it('leads other grounded answers too', () => {
    render(<AnswerContent result={syntheticAnswer} />);
    expect(screen.getByText('Here’s what I found.')).toBeVisible();
  });
  it('shows a greeting reply as plain text with example questions and no report', () => {
    render(<AnswerContent result={smallTalk} />);
    expect(
      screen.getByText(/I am Forge, a read-only engineering/),
    ).toBeVisible();
    expect(screen.getByText('What features does my model have?')).toBeVisible();
    expect(screen.queryByText(/Here’s what I/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Ask me about any feature/),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('Uncertainties')).not.toBeInTheDocument();
  });
  it('never adds lead-in text to a refusal', () => {
    render(
      <AnswerContent
        result={{
          ...smallTalk,
          answer: 'Forge cannot provide that.',
          follow_up_questions: [],
        }}
      />,
    );
    expect(screen.queryByText(/Here’s what I/)).not.toBeInTheDocument();
  });
});
