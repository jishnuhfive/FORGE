import { useLayoutEffect, useRef } from 'react';
import type { RefObject } from 'react';

type Axis = { position: number; velocity: number; target: number };

// Slightly under-damped (zeta ~0.8): a single small overshoot, then rest.
const STIFFNESS = 560;
const DAMPING = 38;
const REST_DISTANCE = 0.2;
const REST_SPEED = 4;
// Pixels of extra length per px/s of travel, capped. The pill leans into the move.
const STRETCH_PER_SPEED = 0.014;
const STRETCH_MAX = 14;

function motionReduced(node: HTMLElement) {
  return (
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true ||
    node.closest('[data-motion="reduced"]') !== null
  );
}

/**
 * Drives one pill under a segmented control with a velocity-preserving spring.
 * Retargeting mid-flight keeps the current position and velocity, so rapid
 * selection never jumps or queues. Purely presentational: the selected value is
 * owned by the caller and never waits on this animation.
 */
export function useSegmentIndicator(
  list: RefObject<HTMLElement | null>,
  indicator: RefObject<HTMLElement | null>,
  selected: string,
) {
  // Spring state lives for the life of the control, not per selection.
  const retargetRef = useRef<(() => void) | null>(null);
  useLayoutEffect(() => {
    const track = list.current;
    const pill = indicator.current;
    if (!track || !pill) return;
    const x: Axis = { position: 0, velocity: 0, target: 0 };
    const w: Axis = { position: 0, velocity: 0, target: 0 };
    let frame: number | null = null;
    let last = 0;
    let ready = false;

    const paint = () => {
      const stretch = Math.min(
        STRETCH_MAX,
        Math.abs(x.velocity) * STRETCH_PER_SPEED,
      );
      pill.style.width = `${w.position + stretch}px`;
      pill.style.transform = `translate3d(${x.position - stretch / 2}px,0,0)`;
    };
    const measure = () => {
      const tab = [...track.querySelectorAll<HTMLElement>('[role="tab"]')].find(
        (node) => node.dataset.state === 'active',
      );
      if (!tab || tab.offsetWidth === 0) return false;
      x.target = tab.offsetLeft;
      w.target = tab.offsetWidth;
      return true;
    };
    const step = (time: number) => {
      frame = null;
      const dt = Math.min(
        0.032,
        Math.max(0.001, (time - last) / 1000 || 0.016),
      );
      last = time;
      let moving = false;
      for (const axis of [x, w]) {
        const force =
          STIFFNESS * (axis.target - axis.position) - DAMPING * axis.velocity;
        axis.velocity += force * dt;
        axis.position += axis.velocity * dt;
        if (
          Math.abs(axis.target - axis.position) > REST_DISTANCE ||
          Math.abs(axis.velocity) > REST_SPEED
        )
          moving = true;
        else {
          axis.position = axis.target;
          axis.velocity = 0;
        }
      }
      paint();
      if (moving) frame = requestAnimationFrame(step);
    };
    const snap = () => {
      if (frame !== null) cancelAnimationFrame(frame);
      frame = null;
      x.position = x.target;
      w.position = w.target;
      x.velocity = w.velocity = 0;
      paint();
    };
    const retarget = () => {
      if (!measure()) return;
      if (!ready || motionReduced(track)) {
        ready = true;
        snap();
        return;
      }
      if (frame === null) {
        last = performance.now();
        frame = requestAnimationFrame(step);
      }
    };
    retargetRef.current = retarget;
    retarget();

    // Width changes (panel resize, font load) re-aim the pill without animating.
    let observer: ResizeObserver | undefined;
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(() => {
        if (measure()) snap();
      });
      observer.observe(track);
    }

    // Compression is a CSS spring on the pill's child; this only flags the press.
    const press = (event: PointerEvent) => {
      const tab = (event.target as HTMLElement).closest<HTMLElement>(
        '[role="tab"]',
      );
      if (tab && !tab.hasAttribute('disabled'))
        track.dataset.pressed =
          tab.dataset.state === 'active' ? 'selected' : 'other';
    };
    const release = () => {
      delete track.dataset.pressed;
    };
    track.addEventListener('pointerdown', press);
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
    track.addEventListener('pointerleave', release);
    return () => {
      retargetRef.current = null;
      if (frame !== null) cancelAnimationFrame(frame);
      observer?.disconnect();
      track.removeEventListener('pointerdown', press);
      window.removeEventListener('pointerup', release);
      window.removeEventListener('pointercancel', release);
      track.removeEventListener('pointerleave', release);
      delete track.dataset.pressed;
    };
  }, [list, indicator]);
  useLayoutEffect(() => {
    retargetRef.current?.();
  }, [selected]);
}
