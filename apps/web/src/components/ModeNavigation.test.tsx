import { act, fireEvent, render, screen } from '@testing-library/react';
import { useRef, useState } from 'react';
import { Tabs } from '@forge/design-system';
import { beforeEach, describe, expect, it, vi } from 'vitest';

function Example() {
  const scroll = useRef<HTMLDivElement | null>(null);
  const [mode, setMode] = useState('design');
  return (
    <div ref={scroll} data-testid="scroller" tabIndex={0}>
      <Tabs
        label="Engineering mode"
        value={mode}
        onValueChange={setMode}
        scrollContainerRef={scroll}
        items={['design', 'modify', 'learn'].map((id) => ({
          id,
          label: id,
          content: <p>{id} content</p>,
        }))}
      />
    </div>
  );
}
let frames: Map<number, FrameRequestCallback>;
let serial: number;
beforeEach(() => {
  frames = new Map();
  serial = 0;
  vi.stubGlobal(
    'requestAnimationFrame',
    vi.fn((callback: FrameRequestCallback) => {
      frames.set(++serial, callback);
      return serial;
    }),
  );
  vi.stubGlobal(
    'cancelAnimationFrame',
    vi.fn((id: number) => frames.delete(id)),
  );
});
function flush() {
  act(() => {
    const pending = [...frames.values()];
    frames.clear();
    pending.forEach((callback) => callback(0));
  });
}
function scroll(y: number, run = true) {
  const pane = screen.getByTestId('scroller');
  pane.scrollTop = y;
  fireEvent.scroll(pane);
  if (run) flush();
}
const navigation = () =>
  screen.getByRole('tablist', { name: 'Engineering mode' });

describe('auto-hiding mode navigation', () => {
  it('starts visible, hides after deliberate travel and returns on upward travel or near top', () => {
    render(<Example />);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
    scroll(32);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
    scroll(80);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'true');
    scroll(160);
    scroll(152);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'true');
    scroll(140);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
    scroll(220);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'true');
    scroll(20);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
  });
  it('does not flicker on tiny alternating trackpad movement', () => {
    render(<Example />);
    scroll(100);
    for (const y of [99, 101, 98, 100, 99, 101]) scroll(y);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'true');
    scroll(70);
    for (const y of [71, 69, 72, 70, 71, 69]) scroll(y);
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
  });
  for (const mode of ['design', 'modify', 'learn']) {
    it(`immediately reveals on ${mode} focus and preserves keyboard access`, () => {
      render(<Example />);
      scroll(100);
      const tab = screen.getByRole('tab', { name: mode });
      act(() => tab.focus());
      expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
      scroll(200);
      expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
      expect(navigation()).not.toHaveAttribute('aria-hidden');
      expect(tab).toHaveFocus();
    });
  }
  it('shows navigation when the active mode changes', () => {
    render(<Example />);
    scroll(100);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'modify' }), {
      key: 'Enter',
    });
    expect(navigation()).toHaveAttribute('data-scroll-hidden', 'false');
    expect(screen.getByText('modify content')).toBeVisible();
  });
  it('does not rewrite visibility while scrolling in the same state', () => {
    render(<Example />);
    const observer = new MutationObserver(() => {});
    observer.observe(navigation(), {
      attributes: true,
      attributeFilter: ['data-scroll-hidden'],
    });
    scroll(100);
    expect(observer.takeRecords()).toHaveLength(1);
    scroll(180);
    scroll(240);
    expect(observer.takeRecords()).toHaveLength(0);
    observer.disconnect();
  });
  it('batches scrolls into one frame, reads no geometry and cancels pending work on cleanup', () => {
    const view = render(<Example />);
    const measure = vi.spyOn(navigation(), 'getBoundingClientRect');
    const initialFrames = frames.size;
    scroll(60, false);
    scroll(90, false);
    scroll(120, false);
    expect(frames.size).toBe(initialFrames + 1);
    flush();
    expect(measure).not.toHaveBeenCalled();
    scroll(150, false);
    const pendingNavigationFrame = serial;
    view.unmount();
    expect(frames.has(pendingNavigationFrame)).toBe(false);
    expect(cancelAnimationFrame).toHaveBeenCalledWith(pendingNavigationFrame);
  });
});
