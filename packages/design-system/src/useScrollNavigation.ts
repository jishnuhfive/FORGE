import { useEffect } from 'react';
import type { RefObject } from 'react';

/** One passive listener, bounded rAF work, no layout measurements or render loop. */
export function useScrollNavigation(
  scrollRef: RefObject<HTMLElement | null> | undefined,
  navigationRef: RefObject<HTMLElement | null>,
  value: string,
) {
  useEffect(() => {
    const scroll = scrollRef?.current;
    const navigation = navigationRef.current;
    if (!scroll || !navigation) return;
    let frame: number | null = null;
    let last = Math.max(0, scroll.scrollTop);
    let direction = 0;
    let travel = 0;
    let hidden = false;
    navigation.dataset.scrollHidden = 'false';
    const show = () => {
      if (hidden) {
        hidden = false;
        navigation.dataset.scrollHidden = 'false';
      }
      last = Math.max(0, scroll.scrollTop);
      travel = 0;
      direction = 0;
    };
    const update = () => {
      frame = null;
      const y = Math.max(0, scroll.scrollTop);
      const delta = y - last;
      last = y;
      if (y <= 24 || navigation.contains(document.activeElement)) {
        if (hidden) show();
        travel = 0;
        direction = 0;
        return;
      }
      if (!delta) return;
      const nextDirection = Math.sign(delta);
      if (direction !== nextDirection) travel = 0;
      direction = nextDirection;
      travel += Math.abs(delta);
      const shouldHide =
        direction > 0 && travel >= 48
          ? true
          : direction < 0 && travel >= 16
            ? false
            : hidden;
      if (shouldHide !== hidden) {
        hidden = shouldHide;
        navigation.dataset.scrollHidden = String(hidden);
      }
    };
    const onScroll = () => {
      if (frame === null) frame = requestAnimationFrame(update);
    };
    scroll.addEventListener('scroll', onScroll, { passive: true });
    navigation.addEventListener('focusin', show);
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      scroll.removeEventListener('scroll', onScroll);
      navigation.removeEventListener('focusin', show);
      delete navigation.dataset.scrollHidden;
    };
  }, [scrollRef, navigationRef, value]);
}
