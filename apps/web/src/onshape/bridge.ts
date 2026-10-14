import { parseLaunch } from './context';
import type { ClientState } from './model';
import { parseSelection } from './selection';

export interface BridgeHost {
  parent: Pick<Window, 'postMessage'>;
  embedded: boolean;
  extension: boolean;
  search: string;
  /** A browser-supplied referrer may reject a mismatch; it never grants trust. */
  referrer: string;
  listen: (listener: (event: MessageEvent<unknown>) => void) => () => void;
  focus: () => void;
}
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
/** One bridge per mounted frame. No raw payloads or URLs are retained or logged. */
export function createBridge(host: BridgeHost) {
  let state = parseLaunch(host.search, host.embedded, host.extension);
  const subscribers = new Set<() => void>();
  let stop: (() => void) | undefined;
  let initialized = false;
  let active = true;
  let diagnosticObserver: ((data: unknown) => void) | undefined;
  const publish = (next: ClientState) => {
    state = next;
    subscribers.forEach((notify) => notify());
  };
  if (state.context && host.referrer) {
    try {
      if (new URL(host.referrer).origin !== state.context.server) {
        state = {
          status: 'UNTRUSTED_ORIGIN',
          context: null,
          selection: { status: 'waiting', entities: [] },
          issue: 'untrusted-parent',
        };
      }
    } catch {
      state = {
        status: 'UNTRUSTED_ORIGIN',
        context: null,
        selection: { status: 'waiting', entities: [] },
        issue: 'untrusted-parent',
      };
    }
  }
  function receive(event: MessageEvent<unknown>) {
    const context = state.context;
    // Check source and exact browser origin BEFORE inspecting attacker data.
    if (
      !context ||
      !event ||
      event.origin !== context.server ||
      event.source !== host.parent
    )
      return;
    const data = event.data;
    if (!record(data) || typeof data.messageName !== 'string') return;
    if (import.meta.env.DEV && data.messageName === 'SELECTION') {
      diagnosticObserver?.(data);
    }
    if (data.messageName === 'show' && Object.keys(data).length === 1) {
      host.focus();
      // show requests focus, not a new CAD context or a selection reset. It has
      // no identity evidence with which to revive a genuinely suspended frame.
      if (active) publish({ ...state, status: 'EMBEDDED_CONNECTED' });
    }
    if (data.messageName === 'SELECTION' && active) {
      // Incoming selection envelopes need not carry context IDs. When the
      // documented envelope fields are supplied, they must match this launch.
      const expected = {
        documentId: context.documentId,
        workspaceId:
          context.revision.kind === 'workspace'
            ? context.revision.workspaceId
            : undefined,
        elementId: context.elementId,
      };
      if (
        Object.entries(expected).some(
          ([key, value]) => Object.hasOwn(data, key) && data[key] !== value,
        )
      ) {
        active = false;
        publish({
          status: 'EMBEDDED_CONTEXT_ERROR',
          context: null,
          selection: { status: 'waiting', entities: [] },
          issue: 'invalid-context',
        });
        return;
      }
      const entities = parseSelection(data);
      publish({
        ...state,
        status: 'EMBEDDED_CONNECTED',
        selection: entities
          ? {
              status: 'available',
              entities,
              sourceElementId: context.elementId,
            }
          : { status: 'unavailable', entities: [] },
      });
    }
  }
  return {
    setDiagnosticObserver: (
      observer: ((data: unknown) => void) | undefined,
    ) => {
      if (import.meta.env.DEV) diagnosticObserver = observer;
    },
    snapshot: () => state,
    subscribe: (notify: () => void) => {
      subscribers.add(notify);
      return () => {
        subscribers.delete(notify);
      };
    },
    start: () => {
      const context = state.context;
      if (stop || !context || context.revision.kind !== 'workspace') return;
      stop = host.listen(receive); // Install before initialization; no response race.
      if (!initialized) {
        // The documented right-panel envelope requires a workspaceId. Do not
        // send a versionId under that name while version messaging is unverified.
        host.parent.postMessage(
          {
            messageName: 'applicationInit',
            documentId: context.documentId,
            workspaceId: context.revision.workspaceId,
            elementId: context.elementId,
          },
          context.server,
        );
        initialized = true;
        host.focus();
      }
    },
    stop: () => {
      stop?.();
      stop = undefined;
      diagnosticObserver = undefined;
    },
    invalidate: () => {
      // Navigation/bfcache suspension is distinct from ordinary tab visibility.
      // A show without context IDs cannot revive it; a fresh launch is required.
      active = false;
      if (state.context)
        publish({
          ...state,
          status: 'EMBEDDED_INITIALIZING',
          selection: { status: 'stale', entities: [] },
        });
    },
  };
}
