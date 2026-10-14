import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Button } from '@forge/design-system';
import { useAuth } from '../auth/context';
import type { ClientState, OnshapeClientContext } from '../onshape/model';
import { revisionId } from '../onshape/model';
import { CadReadError, sectionNames } from './api';
import { inspectCad } from './inspector';
import type { Inspector } from './inspector';
import { InspectorView } from './InspectorView';
import { messages } from './messages';

const Diagnostic = import.meta.env.DEV
  ? lazy(() => import('./dev/ReadDiagnostic'))
  : null;

export function ReadCad({ state }: { state: ClientState }) {
  const auth = useAuth();
  const context = state.context;
  if (!context || !auth || auth.me.status !== 'authenticated') return null;
  if (
    context.revision.kind !== 'workspace' ||
    (context.elementType && context.elementType !== 'partStudio')
  )
    return <p className="small muted">{messages.unsupported_context}</p>;
  if (auth.me.connection !== 'connected' || !auth.me.csrf_token)
    return <p className="small muted">{messages.connection_required}</p>;
  if (state.selection.status === 'stale')
    return (
      <p className="small muted">
        Reopen the Forge panel to refresh CAD context.
      </p>
    );
  if (state.selection.status === 'unavailable')
    return (
      <p className="small muted">
        CAD inspection is paused until a valid selection update arrives from
        Onshape. Select or clear a selection to continue.
      </p>
    );
  // Remount immediately on any reference/account change, so old results cannot flash.
  const key = [
    context.documentId,
    context.revision.kind,
    revisionId(context),
    context.elementId,
    context.server,
    context.microversionId ?? '',
    auth.me.csrf_token,
  ].join(':');
  return <ReadCurrent key={key} context={context} csrf={auth.me.csrf_token} />;
}

function ReadCurrent({
  context,
  csrf,
}: {
  context: OnshapeClientContext;
  csrf: string;
}) {
  const [result, setResult] = useState<Inspector | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [cooling, setCooling] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const cooldown = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    const invalidate = () => {
      pending.current?.abort();
      pending.current = null;
      setResult(null);
      setError(null);
      setLoading(false);
    };
    window.addEventListener('pagehide', invalidate);
    return () => {
      pending.current?.abort();
      if (cooldown.current) clearTimeout(cooldown.current);
      window.removeEventListener('pagehide', invalidate);
    };
  }, []);
  const read = async () => {
    if (pending.current || cooling) return;
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setResult(null);
    setError(null);
    let delay = 5;
    const timeout = setTimeout(() => controller.abort(), 100_000);
    try {
      const value = await inspectCad(context, csrf, controller.signal);
      if (controller.signal.aborted || pending.current !== controller) return;
      setResult(value);
      delay = Math.max(
        5,
        ...sectionNames.map(
          (name) =>
            value.source[name].retry_after_seconds ??
            (value.source[name].status === 'rate_limited' ? 60 : 5),
        ),
      );
    } catch (cause) {
      if (pending.current === controller)
        setError(
          messages[
            cause instanceof CadReadError ? cause.code : 'provider_unavailable'
          ],
        );
    } finally {
      clearTimeout(timeout);
      if (pending.current === controller) {
        pending.current = null;
        setLoading(false);
        setCooling(true);
        cooldown.current = setTimeout(() => setCooling(false), delay * 1000);
      }
    }
  };
  return (
    <div className="cad-read" role="group" aria-label="CAD inspector">
      <Button
        variant="secondary"
        onClick={() => {
          void read();
        }}
        disabled={loading || cooling}
      >
        {loading ? 'Reading CAD data…' : 'Refresh CAD'}
      </Button>
      <p className="small muted">
        Read-only · default configuration · no automatic refresh
      </p>
      <div role="status" aria-live="polite" aria-busy={loading}>
        {loading && (
          <p className="small">Reading this Part Studio from Onshape…</p>
        )}
        {error && <p className="small">{error}</p>}
        {result && (
          <p className="small">Inspection captured. Section details below.</p>
        )}
        {cooling && (
          <p className="small muted">Please wait before the next read.</p>
        )}
      </div>
      {!result && !loading && !error && (
        <p className="small muted">
          Refresh CAD to inspect this Part Studio. Previous evidence is cleared
          when the CAD context or account changes.
        </p>
      )}
      {result && (
        <>
          <InspectorView result={result} />
          {Diagnostic && (
            <Suspense fallback={null}>
              <Diagnostic result={result.source} />
            </Suspense>
          )}
        </>
      )}
    </div>
  );
}
