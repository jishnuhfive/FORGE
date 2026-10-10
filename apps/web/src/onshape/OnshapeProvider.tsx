import {
  Suspense,
  lazy,
  useEffect,
  useState,
  useSyncExternalStore,
} from 'react';
import type { ReactNode } from 'react';
import { createBridge } from './bridge';
import { OnshapeContext } from './store';

const SelectionDiagnostic = import.meta.env.DEV
  ? lazy(() => import('./dev/SelectionDiagnostic'))
  : null;
const LaunchDiagnostic = import.meta.env.DEV
  ? lazy(() => import('./dev/LaunchDiagnostic'))
  : null;

export function OnshapeProvider({ children }: { children: ReactNode }) {
  const [bridge] = useState(() =>
    createBridge({
      parent: window.parent,
      embedded: window.parent !== window,
      extension: window.location.pathname === '/extension',
      search: window.location.search,
      referrer: document.referrer,
      listen: (listener) => {
        window.addEventListener('message', listener);
        return () => window.removeEventListener('message', listener);
      },
      focus: () => {
        document.getElementById('root')?.focus({ preventScroll: true });
      },
    }),
  );
  const state = useSyncExternalStore(bridge.subscribe, bridge.snapshot);
  useEffect(() => {
    let mounted = true;
    let reset: (() => void) | undefined;
    if (import.meta.env.DEV) {
      void import('./dev/diagnostics').then((diagnostics) => {
        if (!mounted) return;
        reset = diagnostics.resetDiagnostics;
        bridge.setDiagnosticObserver(diagnostics.captureSelectionStructure);
      });
    }
    bridge.start();
    const hidden = () => {
      if (document.hidden) bridge.invalidate();
    };
    const restored = (event: PageTransitionEvent) => {
      if (event.persisted) bridge.invalidate();
    };
    window.addEventListener('pagehide', bridge.invalidate);
    window.addEventListener('pageshow', restored);
    document.addEventListener('visibilitychange', hidden);
    return () => {
      mounted = false;
      reset?.();
      bridge.stop();
      window.removeEventListener('pagehide', bridge.invalidate);
      window.removeEventListener('pageshow', restored);
      document.removeEventListener('visibilitychange', hidden);
    };
  }, [bridge]);
  return (
    <OnshapeContext.Provider value={state}>
      {children}
      {LaunchDiagnostic && (
        <Suspense fallback={null}>
          <LaunchDiagnostic />
        </Suspense>
      )}
      {SelectionDiagnostic && (
        <Suspense fallback={null}>
          <SelectionDiagnostic />
        </Suspense>
      )}
    </OnshapeContext.Provider>
  );
}
