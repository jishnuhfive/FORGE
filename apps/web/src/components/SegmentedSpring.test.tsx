import { act, fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { Tabs } from '@forge/design-system';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

function Example() {
  const [mode, setMode] = useState('design');
  return (
    <Tabs
      label="Engineering mode"
      value={mode}
      onValueChange={setMode}
      items={['design', 'modify', 'learn'].map((id) => ({
        id,
        label: id,
        content: <p>{id} content</p>,
      }))}
    />
  );
}
let frames: Map<number, FrameRequestCallback>;
let serial: number;
let clock: number;
function advance(ms: number) {
  const end = clock + ms;
  act(() => {
    while (clock < end) {
      clock += 16;
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback(clock));
    }
  });
}
const pill = () =>
  screen.getByRole('tablist').querySelector<HTMLElement>('.tabs-indicator')!;
const left = () =>
  Number(/translate3d\(([-\d.]+)px/.exec(pill().style.transform)?.[1]);
const stretch = () => parseFloat(pill().style.width) - 100;

function layout() {
  // jsdom has no layout: three 100px segments laid out left to right.
  const index = (node: HTMLElement) =>
    [...(node.parentElement?.querySelectorAll('[role="tab"]') ?? [])].indexOf(
      node,
    );
  vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.getAttribute('role') === 'tab' ? 100 : 0;
    },
  );
  vi.spyOn(HTMLElement.prototype, 'offsetLeft', 'get').mockImplementation(
    function (this: HTMLElement) {
      return index(this) * 100;
    },
  );
}
function motion(reduce: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: reduce })),
  );
}
beforeEach(() => {
  frames = new Map();
  serial = 0;
  clock = 0;
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
  vi.spyOn(performance, 'now').mockImplementation(() => clock);
  layout();
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
const select = (name: string) =>
  fireEvent.mouseDown(screen.getByRole('tab', { name }), { button: 0 });

describe('spring-driven mode switcher', () => {
  it('keeps the Radix tab semantics and selects immediately, before the pill arrives', () => {
    motion(false);
    render(<Example />);
    expect(left()).toBe(0);
    select('learn');
    // State and content change at once; only the pill is still travelling.
    expect(screen.getByRole('tab', { name: 'learn' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.getByText('learn content')).toBeVisible();
    advance(48);
    expect(left()).toBeGreaterThan(0);
    expect(left()).toBeLessThan(200);
    advance(1500);
    expect(left()).toBe(200);
    expect(parseFloat(pill().style.width)).toBe(100);
  });
  it('leans into the move with a brief stretch that settles to the exact segment width', () => {
    motion(false);
    render(<Example />);
    select('learn');
    let peak = 0;
    for (let i = 0; i < 40; i++) {
      advance(16);
      peak = Math.max(peak, stretch());
    }
    expect(peak).toBeGreaterThan(1);
    expect(peak).toBeLessThanOrEqual(14);
    advance(1500);
    expect(stretch()).toBe(0);
  });
  it('retargets mid-flight without a jump and ends on the last selection', () => {
    motion(false);
    render(<Example />);
    select('learn');
    advance(64);
    const before = left();
    select('design');
    select('modify');
    select('learn');
    select('design');
    // No discontinuity at the moment of interruption.
    advance(16);
    expect(Math.abs(left() - before)).toBeLessThan(60);
    advance(1500);
    expect(screen.getByRole('tab', { name: 'design' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(left()).toBe(0);
  });
  it('snaps without animating when reduced motion is requested', () => {
    motion(true);
    render(<Example />);
    select('modify');
    expect(left()).toBe(100);
    expect(parseFloat(pill().style.width)).toBe(100);
  });
  it('compresses the pill on press of the selected segment and releases after', () => {
    motion(false);
    render(<Example />);
    const list = screen.getByRole('tablist');
    fireEvent.pointerDown(screen.getByRole('tab', { name: 'design' }));
    expect(list).toHaveAttribute('data-pressed', 'selected');
    fireEvent.pointerUp(window);
    expect(list).not.toHaveAttribute('data-pressed');
    fireEvent.pointerDown(screen.getByRole('tab', { name: 'learn' }));
    expect(list).toHaveAttribute('data-pressed', 'other');
    fireEvent.pointerLeave(list);
    expect(list).not.toHaveAttribute('data-pressed');
  });
  it('stays a real tablist: named, one selected tab, panel wired to its tab', () => {
    motion(true);
    render(<Example />);
    expect(
      screen.getByRole('tablist', { name: 'Engineering mode' }),
    ).toBeVisible();
    const tabs = screen.getAllByRole('tab');
    expect(tabs.map((tab) => tab.getAttribute('aria-selected'))).toEqual([
      'true',
      'false',
      'false',
    ]);
    expect(screen.getByRole('tabpanel')).toHaveAttribute(
      'aria-labelledby',
      tabs[0]!.id,
    );
    // The pill is decorative and never exposed to assistive technology.
    expect(pill()).toHaveAttribute('aria-hidden', 'true');
  });
});
