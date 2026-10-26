import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { Workspace } from '../App';
import { isLesson } from './lesson';
import { mountingPlate } from './plate';

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(
    'forge.preferences.v1',
    JSON.stringify({ onboarded: true }),
  );
  window.location.hash = '';
});

describe('mounting plate lesson', () => {
  it('passes the lesson schema and checks nothing deterministically', () => {
    expect(isLesson(mountingPlate)).toBe(true);
    expect(mountingPlate.steps).toHaveLength(6);
    for (const step of mountingPlate.steps) {
      expect(step.check).toBeUndefined();
      expect(step.completion).toBe('learner-reported');
      expect(step.expectation?.choices.length).toBeGreaterThanOrEqual(2);
    }
  });

  it('is reachable from the setup goal and states that nothing is measured', () => {
    render(<Workspace />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Learn' }), {
      key: 'Enter',
    });
    fireEvent.click(screen.getByRole('radio', { name: /^Beginner/ }));
    fireEvent.click(
      screen.getByRole('radio', {
        name: 'Follow a mounting plate from sketch to fillet',
      }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Review lesson' }));
    expect(
      screen.getByRole('heading', { name: 'Mounting plate' }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Begin lesson' }));
    expect(screen.getByText(/Forge does not check your model/)).toBeVisible();
    expect(screen.queryByText(/Verified/)).toBeNull();
  });
});
