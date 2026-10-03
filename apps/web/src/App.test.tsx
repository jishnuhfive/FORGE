import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { App } from './App';

describe('Phase 0 foundation', () => {
  it('renders a main landmark with the Forge title', () => {
    render(<App />);
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Forge' }),
    ).toBeVisible();
  });

  it('identifies the purpose and current development phase', () => {
    render(<App />);
    expect(screen.getByText('AI engineering inside Onshape')).toBeVisible();
    expect(screen.getByText('Phase 0 — Foundation')).toBeVisible();
  });
});
