import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Badge, Button } from '@forge/design-system';
import { useAuth } from '../auth/context';
import type { ClientState, OnshapeClientContext } from '../onshape/model';
import { revisionId } from '../onshape/model';
import { CadReadError, readCad, sectionNames } from './api';
import type { ReadCode, ReadProof, SectionName } from './api';

const Diagnostic = import.meta.env.DEV
  ? lazy(() => import('./dev/ReadDiagnostic'))
  : null;
const labels: Record<SectionName, string> = {
  features: 'Features',
  parts: 'Parts',
  bodies: 'Body details',
  mass: 'Mass properties',
};
const messages: Record<
  ReadCode | 'session_check_required' | 'unsupported_context',
  string
> = {
  ok: 'Available',
  connection_required:
    'Onshape connection required. Reconnect in account settings.',
  read_permission_required:
    'Additional Onshape read permission required. Update the app permissions, then reconnect.',
  permission_or_access_required:
    'Onshape denied this read. Check the app’s document-read permission and your access to this document.',
  document_forbidden: 'Access to this document is forbidden.',
  not_found: 'Document or element not found.',
  rate_limited: 'Onshape API rate limit reached. Wait before reading again.',
  quota_exceeded:
    'Onshape API allowance reached. Check usage in Onshape Developer settings.',
  provider_unavailable: 'Onshape temporarily unavailable. Try again later.',
  provider_timeout: 'Onshape took too long to respond. Try again later.',
  invalid_response: 'Onshape returned data Forge could not verify.',
  response_too_large: 'This Part Studio exceeds the current read size limit.',
  redirect_rejected:
    'Onshape requested a redirect that Forge does not support.',
  unsupported_provider:
    'This Onshape server is not supported for CAD reads yet.',
  request_in_progress:
    'A CAD read is already in progress. Wait before reading again.',
  session_check_required:
    'Your Forge session needs to be checked. Reload the panel.',
  unsupported_context:
    'CAD reads currently support workspace Part Studios only.',
};

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
  // Remount immediately on any reference/account change, so old results cannot flash.
  const key = [
    context.documentId,
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
  const [result, setResult] = useState<ReadProof | null>(null);
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
    const visibility = () => {
      if (document.hidden) invalidate();
    };
    window.addEventListener('pagehide', invalidate);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      pending.current?.abort();
      if (cooldown.current) clearTimeout(cooldown.current);
      window.removeEventListener('pagehide', invalidate);
      document.removeEventListener('visibilitychange', visibility);
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
      const value = await readCad(context, csrf, controller.signal);
      if (controller.signal.aborted || pending.current !== controller) return;
      setResult(value);
      delay = Math.max(
        5,
        ...sectionNames.map(
          (name) =>
            value[name].retry_after_seconds ??
            (value[name].status === 'rate_limited' ? 60 : 5),
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
  const connected =
    result?.features.status === 'success' && result.parts.status === 'success';
  return (
    <div className="cad-read" role="group" aria-label="Read CAD data">
      <Button
        variant="secondary"
        onClick={() => {
          void read();
        }}
        disabled={loading || cooling}
      >
        {loading ? 'Reading CAD data…' : 'Read CAD data'}
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
          <>
            {connected && <Badge tone="accent">Onshape data connected</Badge>}
            <ul className="cad-read-summary small">
              {sectionNames.map((name) => {
                const section = result[name];
                return (
                  <li key={name}>
                    {section.status !== 'success'
                      ? `${labels[name]}: ${messages[section.code]}`
                      : name === 'mass'
                        ? section.count === 0
                          ? 'No mass-property bodies returned'
                          : result.has_mass === true
                            ? 'Mass properties available'
                            : result.has_mass === false
                              ? 'Mass unavailable; material/density may be missing'
                              : 'Mass data read; assigned mass is unavailable or unverified'
                        : section.count === null
                          ? `${labels[name]} read; total count unverified`
                          : `${section.count} ${name === 'features' ? (section.count === 1 ? 'feature' : 'features') : name === 'parts' ? (section.count === 1 ? 'part' : 'parts') : section.count === 1 ? 'body' : 'bodies'}`}
                  </li>
                );
              })}
            </ul>
            <p className="small muted">
              Read at {new Date(result.captured_at).toLocaleTimeString()}.{' '}
              {result.consistency === 'mismatch'
                ? 'CAD changed during this read. Read again before using these results.'
                : 'Separate reads; a single consistent CAD version is unverified.'}
            </p>
            {Diagnostic && (
              <Suspense fallback={null}>
                <Diagnostic result={result} />
              </Suspense>
            )}
          </>
        )}
        {cooling && (
          <p className="small muted">Please wait before the next read.</p>
        )}
      </div>
    </div>
  );
}
