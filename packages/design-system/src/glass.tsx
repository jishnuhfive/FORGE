import { useEffect, useRef } from 'react';
import type { ComponentPropsWithRef, PointerEvent } from 'react';

/** A single shared map. Neutral center; opposing x/y edge vectors bend backdrop light. */
const edgeMap = `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><defs><linearGradient id="x"><stop stop-color="#000080"/><stop offset=".08" stop-color="#800080"/><stop offset=".92" stop-color="#800080"/><stop offset="1" stop-color="#ff0080"/></linearGradient><linearGradient id="y" x2="0" y2="1"><stop stop-color="#000000"/><stop offset=".08" stop-color="#008000"/><stop offset=".92" stop-color="#008000"/><stop offset="1" stop-color="#00ff00"/></linearGradient></defs><rect width="128" height="128" fill="url(#x)"/><rect width="128" height="128" fill="url(#y)" style="mix-blend-mode:screen"/></svg>`)}`;

export function GlassDefinitions() {
  return (
    <svg className="glass-definitions" aria-hidden="true" focusable="false">
      <defs>
        <filter
          id="forge-glass-refraction"
          colorInterpolationFilters="sRGB"
          x="0"
          y="0"
          width="100%"
          height="100%"
        >
          <feImage
            href={edgeMap}
            x="0"
            y="0"
            width="100%"
            height="100%"
            preserveAspectRatio="none"
            result="edge-map"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="edge-map"
            scale="6"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  );
}

/** Event-driven illumination, never a render loop. No geometry reads in rAF. */
export function GlassSurface({
  className = '',
  children,
  ...props
}: ComponentPropsWithRef<'div'>) {
  const frame = useRef<number | null>(null);
  const bounds = useRef<DOMRect | null>(null);
  const surface = useRef<HTMLDivElement | null>(null);
  const stop = () => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
    bounds.current = null;
    surface.current?.style.removeProperty('--light-x');
    surface.current?.style.removeProperty('--light-y');
  };
  useEffect(() => {
    const hidden = () => {
      if (document.hidden) stop();
    };
    document.addEventListener('visibilitychange', hidden);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', hidden);
    };
  }, []);
  const move = (event: PointerEvent<HTMLDivElement>) => {
    const rect = bounds.current;
    if (!rect || frame.current !== null || document.hidden) return;
    const target = event.currentTarget;
    const x = Math.max(
      0,
      Math.min(100, ((event.clientX - rect.left) / rect.width) * 100),
    );
    const y = Math.max(
      0,
      Math.min(100, ((event.clientY - rect.top) / rect.height) * 100),
    );
    frame.current = requestAnimationFrame(() => {
      target.style.setProperty('--light-x', `${x}%`);
      target.style.setProperty('--light-y', `${y}%`);
      frame.current = null;
    });
  };
  return (
    <div
      {...props}
      className={`glass ${className}`}
      onPointerEnter={(event) => {
        const connection = (
          navigator as Navigator & { connection?: { saveData?: boolean } }
        ).connection;
        if (
          event.pointerType === 'touch' ||
          document.hidden ||
          connection?.saveData ||
          window.matchMedia(
            '(prefers-reduced-motion: reduce), (prefers-reduced-transparency: reduce), (prefers-contrast: more), (forced-colors: active)',
          ).matches ||
          event.currentTarget.closest(
            '[data-transparency="reduced"], [data-motion="reduced"], [data-contrast="more"]',
          )
        )
          return;
        surface.current = event.currentTarget;
        bounds.current = event.currentTarget.getBoundingClientRect();
      }}
      onPointerMove={move}
      onPointerLeave={stop}
      onPointerCancel={stop}
    >
      {children}
    </div>
  );
}

export function ForgeMark({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`forge-mark ${className}`}
      viewBox="0 0 32 32"
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="mark-plane mark-plane--sketch"
        d="M4 8 21 3 28 9 11 14Z"
      />
      <path
        className="mark-plane mark-plane--extrude"
        d="M4 12 11 17 11 29 4 24Z"
      />
      <path
        className="mark-plane mark-plane--object"
        d="M13 17 22 14 27 19 13 23Z"
      />
    </svg>
  );
}
