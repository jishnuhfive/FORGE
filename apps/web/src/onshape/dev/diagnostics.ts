import { sanitizedSelectionStructure } from './structure';

interface DiagnosticState {
  enabled: boolean;
  structure: string | null;
}
const empty: DiagnosticState = { enabled: false, structure: null };
let state = empty;
let lastCapture = -Infinity;
const subscribers = new Set<() => void>();
const publish = (next: DiagnosticState) => {
  state = next;
  for (const notify of subscribers) notify();
};
export const diagnosticSnapshot = () => state;
export const subscribeDiagnostics = (notify: () => void) => {
  subscribers.add(notify);
  return () => {
    subscribers.delete(notify);
  };
};
export function enableDiagnostics() {
  if (import.meta.env.DEV) {
    lastCapture = -Infinity;
    publish({ enabled: true, structure: null });
  }
}
export function clearDiagnostics() {
  lastCapture = -Infinity;
  publish({ ...state, structure: null });
}
export function resetDiagnostics() {
  lastCapture = -Infinity;
  publish(empty);
}

/** Called synchronously only by the bridge AFTER exact-origin/parent validation. */
export function captureSelectionStructure(data: unknown) {
  if (!import.meta.env.DEV || !state.enabled || Date.now() - lastCapture < 100)
    return;
  lastCapture = Date.now();
  const structure = sanitizedSelectionStructure(data);
  if (structure !== null) publish({ enabled: true, structure });
  // Input is not retained, scheduled, logged, transmitted, or attached to state.
}
