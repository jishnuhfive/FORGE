import { useEffect, useRef, useState } from 'react';
import { Button, Badge } from '@forge/design-system';
import { useAuth } from '../auth/context';
import { useOnshapeContext } from '../onshape/store';
import { revisionId } from '../onshape/model';
import type { OnshapeClientContext } from '../onshape/model';
import { ModifyPreview } from '../preview/ModifyPreview';
import {
  approve,
  call,
  contextBody,
  messages,
  ModifyError,
  parseCandidate,
  parseProposal,
} from '../modify/api';
import type { Candidate, ErrorCode, Proposal } from '../modify/api';
import { object } from '../cad/api';

const noAvailabilityChange = () => {};
export function Modify({
  preview = false,
  onAvailabilityChange = noAvailabilityChange,
}: {
  preview?: boolean;
  onAvailabilityChange?: (ready: boolean) => void;
}) {
  const auth = useAuth();
  const client = useOnshapeContext();
  if (preview) return <ModifyPreview preview />;
  const context = client.context;
  if (
    !auth?.me.csrf_token ||
    auth.me.connection !== 'connected' ||
    !context ||
    context.revision.kind !== 'workspace' ||
    !['EMBEDDED_CONNECTED', 'EMBEDDED_INITIALIZING'].includes(client.status)
  )
    return (
      <div className="feature">
        <h1>Modify</h1>
        <p>
          Open a current workspace Part Studio in Onshape with a connected
          account to prepare a supported change.
        </p>
        <p>
          Safe CAD editing is disabled until this environment and your
          authorization permit it.
        </p>
      </div>
    );
  return (
    <ModifyFlow
      key={[
        auth.me.csrf_token,
        auth.me.connection,
        context.documentId,
        revisionId(context),
        context.elementId,
        context.microversionId ?? '',
        client.status === 'EMBEDDED_CONTEXT_ERROR',
      ].join(':')}
      context={context}
      csrf={auth.me.csrf_token}
      onAvailabilityChange={onAvailabilityChange}
    />
  );
}
function ModifyFlow({
  context,
  csrf,
  onAvailabilityChange,
}: {
  context: OnshapeClientContext;
  csrf: string;
  onAvailabilityChange: (ready: boolean) => void;
}) {
  const [available, setAvailable] = useState(false);
  const [intent, setIntent] = useState('');
  const [code, setCode] = useState<ErrorCode | null>(null);
  const [busy, setBusy] = useState('');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [result, setResult] = useState('');
  const pending = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const c = new AbortController();
    controller.current = c;
    void call('capabilities', csrf, c.signal)
      .then((raw) => {
        const v = object(raw, ['state']);
        if (v.state === 'available' && !c.signal.aborted) {
          setAvailable(true);
          onAvailabilityChange(true);
        } else if (
          typeof v.state === 'string' &&
          Object.hasOwn(messages, v.state)
        )
          setCode(v.state as ErrorCode);
        else setCode('invalid_request');
      })
      .catch(() => {
        if (!c.signal.aborted) setCode('invalid_request');
      });
    return () => {
      c.abort();
      onAvailabilityChange(false);
    };
  }, [csrf, onAvailabilityChange]);
  useEffect(() => () => controller.current?.abort(), []);
  async function run(
    stage: string,
    action: (signal: AbortSignal) => Promise<void>,
  ) {
    if (pending.current) return;
    pending.current = true;
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(stage);
    setCode(null);
    const timeout = window.setTimeout(() => c.abort('timeout'), 35000);
    try {
      await action(c.signal);
    } catch (cause) {
      if (c.signal.reason === 'timeout')
        setCode(
          stage === 'checking' ? 'execution_uncertain' : 'onshape_unavailable',
        );
      else if (!c.signal.aborted)
        setCode(
          cause instanceof ModifyError
            ? cause.code
            : stage === 'checking'
              ? 'execution_uncertain'
              : 'invalid_request',
        );
    } finally {
      window.clearTimeout(timeout);
      if (!c.signal.aborted || c.signal.reason === 'timeout') {
        pending.current = false;
        setBusy('');
      }
    }
  }
  const uncertain =
    code === 'execution_uncertain' ||
    [
      'claimed',
      'verifying',
      'execution_uncertain',
      'unverified_result',
      'recovery_required',
    ].includes(result);
  const terminalFailure = [
    'write_failed',
    'rejected_stale',
    'expired',
    'invalidated',
    'cancelled',
  ].includes(result);
  return (
    <div className="feature modify-feature">
      <h1>Modify</h1>
      <p>
        Suppress one eligible final Fillet. You review the exact change before
        Forge can apply it.
      </p>
      <p className="muted small">
        Face or edge selection does not identify a feature. Forge uses an
        authorized feature inventory.
      </p>
      {available && !proposal && !uncertain && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void run('inspecting', async (signal) => {
              setResult('');
              setCandidates([]);
              const raw = await call('targets', csrf, signal, {
                intent,
                context: contextBody(context),
              });
              const v = object(raw, ['candidates']);
              if (
                !Array.isArray(v.candidates) ||
                v.candidates.length < 1 ||
                v.candidates.length > 20
              )
                throw new ModifyError('invalid_request');
              setCandidates(v.candidates.map(parseCandidate));
            });
          }}
        >
          <label className="field-label" htmlFor="modify-intent">
            Modification request
          </label>
          <textarea
            id="modify-intent"
            className="textarea"
            maxLength={256}
            value={intent}
            disabled={!!busy}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="Suppress the final fillet."
          />
          <Button type="submit" disabled={!!busy || !intent.trim()}>
            Find supported target
          </Button>
        </form>
      )}
      {candidates.length > 0 && !proposal && (
        <section aria-label="Choose target">
          <h2>Review the target</h2>
          <p>Choose the eligible feature you intend to suppress.</p>
          {candidates.map((c) => (
            <div key={c.handle}>
              <p>
                {c.label} · final feature, position {c.position}
              </p>
              <Button
                disabled={!!busy}
                onClick={() =>
                  void run('inspecting', async (signal) => {
                    const raw = await call('proposals', csrf, signal, {
                      candidate: c.handle,
                      context: contextBody(context),
                    });
                    const v = object(raw, ['proposal']);
                    setProposal(parseProposal(v.proposal));
                    setCandidates([]);
                  })
                }
              >
                Prepare change for {c.label}
              </Button>
            </div>
          ))}
        </section>
      )}
      {proposal && (
        <section
          className="modification-review"
          aria-label="CAD change proposal"
        >
          <h2>Suppress {proposal.label}</h2>
          <p className="modify-state">
            <strong>Active → Suppressed</strong>
          </p>
          <dl className="context-list">
            <div>
              <dt>Target</dt>
              <dd>
                {proposal.label}, final feature at position {proposal.position}
              </dd>
            </div>
            <div>
              <dt>Current state</dt>
              <dd>Active</dd>
            </div>
            <div>
              <dt>Proposed state</dt>
              <dd>Suppressed</dd>
            </div>
          </dl>
          <p>
            The Fillet will be skipped during regeneration while its feature
            remains in the feature tree.
          </p>
          <p className="muted">
            Forge found one solid-body result and an unsuppressed final Fillet.
            Overall feature health is not established.
          </p>
          <p className="muted">
            Suppressing geometry can affect dependent models. Geometry and
            engineering suitability are not validated.
          </p>
          <p className="small">
            This proposal expires two minutes after creation. Approval applies
            only to this inspected model state.
          </p>
          <div className="action-bar">
            <Button
              disabled={!!busy}
              onClick={() =>
                void run('cancelling', async (signal) => {
                  await call(
                    'proposals/' + proposal.proposal_id + '/cancel',
                    csrf,
                    signal,
                    {},
                  );
                  setProposal(null);
                  setResult('cancelled');
                })
              }
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!!busy || !!result || !!code || uncertain}
              onClick={() =>
                void run('checking', async (signal) => {
                  const state = await approve(proposal, csrf, signal, setBusy);
                  setResult(state);
                  if (state === 'verified_success') setProposal(null);
                })
              }
            >
              Approve change
            </Button>
          </div>
        </section>
      )}
      <div role="status" aria-live="polite" aria-atomic="true">
        {busy && (
          <p>
            {
              (
                {
                  inspecting: 'Inspecting current model…',
                  checking: 'Checking the approved model state…',
                  conformance_wait:
                    'Controlled validation pause. Make the planned test edit in Onshape now.',
                  executing: 'Applying the approved change…',
                  verifying: 'Verifying fresh model evidence…',
                  cancelling: 'Cancelling proposal…',
                } as Record<string, string>
              )[busy]
            }
          </p>
        )}
        {code && <p>{messages[code]}</p>}
        {result === 'cancelled' && (
          <p>Proposal cancelled. Forge made no CAD change.</p>
        )}
        {result === 'verified_success' && (
          <p>
            Change verified. Forge confirmed that the selected Fillet is now
            suppressed. The feature remains in the tree and can be manually
            re-enabled in Onshape.
          </p>
        )}
        {['claimed', 'verifying'].includes(result) && (
          <p>
            The approved operation is still being checked. Check status again
            before taking another action.
          </p>
        )}
        {result === 'write_failed' && (
          <p>
            The operation failed before a CAD write was dispatched. Discard this
            preview and prepare a fresh proposal.
          </p>
        )}
        {result === 'rejected_stale' && <p>{messages.model_changed}</p>}
        {result === 'expired' && <p>{messages.proposal_expired}</p>}
        {result === 'invalidated' && <p>{messages.context_changed}</p>}
        {uncertain && <p>{messages.execution_uncertain}</p>}
      </div>
      {proposal && uncertain && (
        <div className="action-bar">
          <Button
            disabled={!!busy}
            onClick={() =>
              void run('verifying', async (signal) => {
                const raw = await call(
                  'proposals/' + proposal.proposal_id,
                  csrf,
                  signal,
                );
                const v = object(raw, ['state']);
                if (typeof v.state !== 'string')
                  throw new ModifyError('invalid_request');
                setResult(v.state);
              })
            }
          >
            Check operation status
          </Button>
          <Button
            disabled={!!busy}
            onClick={() =>
              void run('verifying', async (signal) => {
                await call(
                  'proposals/' + proposal.proposal_id + '/reconcile',
                  csrf,
                  signal,
                  {},
                );
                setResult('recovery_required');
              })
            }
          >
            Inspect current feature state
          </Button>
        </div>
      )}
      {proposal && uncertain && (
        <details>
          <summary>Recovery reference</summary>
          <p className="small">{proposal.proposal_id}</p>
        </details>
      )}
      {result === 'recovery_required' && <p>{messages.recovery_required}</p>}
      {(code || terminalFailure) && proposal && !busy && !uncertain && (
        <Button
          onClick={() => {
            setProposal(null);
            setCandidates([]);
            setResult('');
            setCode(null);
          }}
        >
          Discard preview
        </Button>
      )}
      {!available && <Badge>CAD writes unavailable</Badge>}
    </div>
  );
}
