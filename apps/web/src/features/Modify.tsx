import { useEffect, useRef, useState } from 'react';
import { Button, Badge } from '@forge/design-system';
import { useAuth } from '../auth/context';
import { useOnshapeContext } from '../onshape/store';
import { revisionId } from '../onshape/model';
import type { OnshapeClientContext } from '../onshape/model';
import { ModifyPreview } from '../preview/ModifyPreview';
import {
  approve,
  capabilities,
  cancelPlan,
  createPlan,
  planStatus,
  recovery as discoverRecovery,
  reconcile,
  messages,
  clarificationMessages,
  ModifyError,
} from '../modify/api';
import type {
  ErrorCode,
  Recovery,
  OperationState,
  PlanPreview,
  PlanResult,
  PlannerResponse,
} from '../modify/api';

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
      ].join(':')}
      context={context}
      csrf={auth.me.csrf_token}
      onAvailabilityChange={onAvailabilityChange}
    />
  );
}
// How a planned change is framed beside its before/after values. Presentation only:
// "verified" appears solely for a server-reported verified_success.
function outcomeOf(
  state: OperationState | undefined,
  uncertain: boolean | undefined,
  finished: boolean,
) {
  if (state === 'verified_success') return 'verified';
  if (state === 'execution_uncertain' || (uncertain && state === 'pending'))
    return 'uncertain';
  if (
    state === 'write_failed' ||
    state === 'rejected_stale' ||
    (finished && state === 'skipped')
  )
    return 'not-applied';
  return 'review';
}
const stateLabels: Record<OperationState, string> = {
  pending: 'Awaiting execution',
  checking: 'Checking…',
  executing: 'Applying…',
  verifying: 'Verifying…',
  verified_success: 'Verified',
  rejected_stale: 'Model changed',
  write_failed: 'Not applied',
  execution_uncertain: 'Uncertain',
  skipped: 'Not attempted',
};
type Busy =
  '' | 'planning' | 'approving' | 'cancelling' | 'status' | 'reconciling';
const busyLabels = {
  reconciling: 'Inspecting current CAD…',
  planning: 'Preparing a plan…',
  approving: 'Applying approved plan…',
  cancelling: 'Cancelling plan…',
  status: 'Checking plan status…',
};
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
  const [recoveryChecked, setRecoveryChecked] = useState(false);
  const [recovery, setRecovery] = useState<Recovery>({ state: 'none' });
  const [reconciled, setReconciled] = useState(false);
  const [intent, setIntent] = useState('');
  const [code, setCode] = useState<ErrorCode | null>(null);
  const [busy, setBusy] = useState<Busy>('');
  const [preview, setPreview] = useState<PlanPreview | null>(null);
  const [clarification, setClarification] = useState<Extract<
    PlannerResponse,
    { outcome: 'clarification' }
  > | null>(null);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [states, setStates] = useState<OperationState[]>([]);
  const [attempted, setAttempted] = useState(false);
  const [expired, setExpired] = useState(false);
  const pending = useRef(false);
  const approvalSent = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const c = new AbortController();
    controller.current = c;
    void capabilities(csrf, c.signal)
      .then(() => {
        if (!c.signal.aborted) {
          setAvailable(true);
        }
      })
      .catch((cause: unknown) => {
        if (!c.signal.aborted)
          setCode(
            cause instanceof ModifyError ? cause.code : 'invalid_request',
          );
      });
    void discoverRecovery(context, csrf, c.signal)
      .then((value) => {
        if (!c.signal.aborted) {
          setRecovery(value);
          setRecoveryChecked(true);
        }
      })
      .catch((cause: unknown) => {
        if (!c.signal.aborted)
          setCode(
            cause instanceof ModifyError ? cause.code : 'invalid_request',
          );
      });
    return () => {
      c.abort();
      onAvailabilityChange(false);
    };
  }, [context, csrf, onAvailabilityChange]);
  useEffect(() => {
    onAvailabilityChange(
      available &&
        recoveryChecked &&
        recovery.state === 'none' &&
        code !== 'workspace_fenced',
    );
  }, [available, recoveryChecked, recovery.state, code, onAvailabilityChange]);
  useEffect(() => {
    if (
      result?.state !== 'execution_uncertain' &&
      code !== 'workspace_fenced' &&
      code !== 'execution_uncertain'
    )
      return;
    const c = new AbortController();
    void discoverRecovery(context, csrf, c.signal)
      .then((value) => {
        if (!c.signal.aborted) setRecovery(value);
      })
      .catch(() => {
        /* Existing unresolved state remains closed. */
      });
    return () => c.abort();
  }, [result?.state, code, context, csrf]);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (!preview || attempted) return;
    const timer = window.setTimeout(
      () => setExpired(true),
      Math.max(0, preview.expires_at * 1000 - Date.now()),
    );
    return () => window.clearTimeout(timer);
  }, [preview, attempted]);

  async function run(
    stage: Exclude<Busy, ''>,
    action: (signal: AbortSignal) => Promise<void>,
  ) {
    if (pending.current) return;
    pending.current = true;
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(stage);
    setCode(null);
    const timer = window.setTimeout(
      () => c.abort('timeout'),
      stage === 'planning' ? 60000 : 35000,
    );
    try {
      await action(c.signal);
    } catch (cause) {
      if (!c.signal.aborted || c.signal.reason === 'timeout') {
        if (stage === 'approving') {
          setStates((previous) =>
            previous.map((state) =>
              ['checking', 'executing', 'verifying'].includes(state)
                ? 'execution_uncertain'
                : state,
            ),
          );
        }
        setCode(
          stage === 'approving'
            ? cause instanceof ModifyError
              ? cause.code
              : 'execution_uncertain'
            : c.signal.reason === 'timeout'
              ? 'timeout'
              : cause instanceof ModifyError
                ? cause.code
                : 'invalid_request',
        );
      }
    } finally {
      window.clearTimeout(timer);
      if (!c.signal.aborted || c.signal.reason === 'timeout') {
        pending.current = false;
        setBusy('');
      }
    }
  }
  function requestPlan() {
    if (
      !available ||
      !recoveryChecked ||
      recovery.state !== 'none' ||
      code === 'workspace_fenced' ||
      preview ||
      !intent.trim()
    )
      return;
    void run('planning', async (signal) => {
      const response = await createPlan(context, intent.trim(), csrf, signal);
      if (signal.aborted) return;
      setClarification(null);
      setResult(null);
      if (response.outcome === 'clarification') {
        setClarification(response);
        return;
      }
      setPreview(response.preview);
      setStates(response.preview.operations.map(() => 'pending'));
      setExpired(Date.now() >= response.preview.expires_at * 1000);
      approvalSent.current = false;
      setAttempted(false);
    });
  }
  function approveClick() {
    if (!preview || pending.current || approvalSent.current) return;
    if (Date.now() >= preview.expires_at * 1000) {
      setExpired(true);
      setCode('proposal_expired');
      return;
    }
    // Consumed locally before any asynchronous work. No effect/status/render can
    // reach this handler, and even a failed approval is never sent again.
    approvalSent.current = true;
    setAttempted(true);
    void run('approving', async (signal) => {
      const final = await approve(preview, csrf, signal, (event) => {
        if (!signal.aborted)
          setStates((previous) =>
            previous.map((state, i) =>
              i === event.operation - 1
                ? event.type === 'progress'
                  ? event.stage
                  : event.state
                : state,
            ),
          );
      });
      if (!signal.aborted) {
        setResult(final);
        setStates(final.operations);
      }
    });
  }
  function clearPlan() {
    if (pending.current) return;
    setPreview(null);
    setResult(null);
    setStates([]);
    setCode(null);
    setExpired(false);
    setAttempted(false);
    approvalSent.current = false;
  }
  const verified = states.filter(
    (state) => state === 'verified_success',
  ).length;
  const total = preview?.operations.length ?? 0;
  const uncertain =
    result?.state === 'execution_uncertain' || (attempted && !busy && !result);
  const inFlight =
    result && ['pending', 'claimed', 'verifying'].includes(result.state);
  const canCheck =
    attempted &&
    busy !== 'approving' &&
    (!result || inFlight || result.state === 'execution_uncertain');
  const completed =
    result &&
    [
      'verified_success',
      'partial_failure',
      'rejected_stale',
      'write_failed',
      'cancelled',
    ].includes(result.state);
  // Presentation only: where the learner is in Request → Plan → Review →
  // Approve → Verify. Nothing here gates or triggers an action.
  const phase =
    busy === 'planning'
      ? 1
      : !preview
        ? 0
        : result?.state === 'verified_success'
          ? 4
          : result || attempted
            ? busy === 'approving' || inFlight || uncertain
              ? 3
              : 4
            : busy === 'approving'
              ? 3
              : 2;
  const tone =
    busy || inFlight
      ? 'progress'
      : uncertain
        ? 'uncertain'
        : result?.state === 'verified_success'
          ? 'success'
          : result?.state === 'rejected_stale'
            ? 'stale'
            : result?.state === 'cancelled'
              ? 'neutral'
              : result?.state === 'write_failed' ||
                  result?.state === 'partial_failure'
                ? 'failed'
                : undefined;
  return (
    <div className="feature modify-feature">
      <div className="feature-heading">
        <h1>Modify</h1>
        <p>Describe a change. Review the exact plan before Forge applies it.</p>
      </div>
      <ol className="modify-flow" aria-label="Modify progress">
        {['Request', 'Plan', 'Review', 'Approve', 'Verify'].map(
          (label, index) => (
            <li
              key={label}
              data-state={
                index < phase ? 'done' : index === phase ? 'current' : 'todo'
              }
              aria-current={index === phase ? 'step' : undefined}
            >
              {label}
            </li>
          ),
        )}
      </ol>
      <p className="muted small">
        Rename supported features, change an Extrude depth or Fillet radius, or
        suppress or unsuppress the final Fillet. Up to five changes per plan.
      </p>
      {reconciled && (
        <p role="status">
          Fresh current CAD evidence matches the intended final state. The
          previous provider write's outcome remains unproven.
        </p>
      )}
      {recovery.state !== 'none' && (
        <section className="modification-review" aria-label="Unresolved change">
          <h2>Unresolved change</h2>
          <p>
            Forge could not verify a previous approved change. Further Forge
            writes are blocked until its current state is inspected.
          </p>
          <ol>
            {recovery.operations.map((operation, i) => (
              <li key={i}>
                {operation.label}: {operation.field} · {operation.current} →{' '}
                {operation.proposed}
              </li>
            ))}
          </ol>
          {recovery.reconciliation === 'manual_required' ? (
            <p>{messages.recovery_required}</p>
          ) : (
            <Button
              disabled={!!busy}
              onClick={() => {
                if (!recovery.plan) return;
                const handle = recovery.plan;
                const total = recovery.operations.length;
                void run('reconciling', async (signal) => {
                  await reconcile(handle, total, csrf, signal);
                  if (!signal.aborted) {
                    setRecovery({ state: 'none' });
                    setPreview(null);
                    setResult(null);
                    setStates([]);
                    setAttempted(false);
                    approvalSent.current = false;
                    setReconciled(true);
                  }
                });
              }}
            >
              Inspect current CAD
            </Button>
          )}
        </section>
      )}
      {available &&
        recoveryChecked &&
        recovery.state === 'none' &&
        code !== 'workspace_fenced' &&
        !preview && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              requestPlan();
            }}
            aria-busy={busy === 'planning'}
          >
            <label className="field-label" htmlFor="modify-request">
              Modification request
            </label>
            <textarea
              id="modify-request"
              className="textarea"
              rows={3}
              maxLength={512}
              value={intent}
              disabled={!!busy}
              placeholder="Make the extrude 30 mm deep and the fillet radius 4 mm."
              aria-describedby="modify-request-hint"
              onChange={(event) => setIntent(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault();
                  requestPlan();
                }
              }}
            />
            <p id="modify-request-hint" className="muted small">
              Include a feature name or position and explicit units. Enter
              prepares a plan; Shift+Enter adds a line.
            </p>
            <div>
              <Button
                type="submit"
                variant="primary"
                disabled={!!busy || !intent.trim()}
              >
                Prepare plan
              </Button>
            </div>
          </form>
        )}
      {clarification && !preview && (
        <section
          className="modification-review"
          aria-label="Clarify your request"
        >
          <h2>Make the request more specific</h2>
          <p>{clarificationMessages[clarification.reason]}</p>
          {clarification.choices.length > 0 && (
            <ul>
              {clarification.choices.map((choice, i) => (
                <li key={i}>
                  {choice.label} ·{' '}
                  {choice.feature_type === 'extrude' ? 'Extrude' : 'Fillet'} ·
                  position {choice.position}
                </li>
              ))}
            </ul>
          )}
          <p className="muted small">
            Rewrite your request above. No changes have been approved.
          </p>
        </section>
      )}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="modify-summary"
        data-tone={tone}
      >
        {busy && <p>{busyLabels[busy]}</p>}
        {result?.state === 'verified_success' && (
          <>
            <h2>Plan verified</h2>
            <p>
              {verified} of {total} changes verified.
            </p>
          </>
        )}
        {result?.state === 'partial_failure' && (
          <>
            <h2>Plan partially completed</h2>
            <p>
              {verified} of {total} changes verified. Earlier verified changes
              remain applied.
            </p>
            <p>
              Forge stopped at the failed change. Remaining changes were not
              attempted.
            </p>
          </>
        )}
        {result?.state === 'rejected_stale' && (
          <>
            <h2>Model changed</h2>
            <p>
              The plan was stopped before its first change. Review a fresh plan.
            </p>
          </>
        )}
        {result?.state === 'write_failed' && (
          <>
            <h2>Plan stopped</h2>
            <p>No changes were applied by this plan.</p>
          </>
        )}
        {result?.state === 'cancelled' && (
          <>
            <h2>Plan cancelled</h2>
            <p>Forge made no CAD changes for this plan.</p>
          </>
        )}
        {uncertain && (
          <>
            <h2>Forge could not confirm the final result.</h2>
            <p>
              {verified} of {total} changes verified so far. Inspect Onshape and
              check status before another plan. Forge will not retry this
              approval.
            </p>
          </>
        )}
        {inFlight && !busy && (
          <p>
            The approved plan is still being checked. {verified} of {total}{' '}
            changes verified so far.
          </p>
        )}
        {code && code !== 'execution_uncertain' && (
          <p className="notice">{messages[code]}</p>
        )}
      </div>
      {recovery.state === 'none' && preview && (
        <section className="modification-review" aria-label="CAD change plan">
          <h2>
            {attempted || result ? 'Reviewed changes' : 'Plan ready for review'}
          </h2>
          {intent.trim() && (
            <p className="modify-asked">
              <span className="muted small">You asked</span>
              {intent.trim()}
            </p>
          )}
          <ol className="modify-operations" aria-label="Planned changes">
            {preview.operations.map((operation, i) => (
              <li key={i}>
                <div className="modify-operation-heading">
                  <h3>
                    {i + 1}. {operation.label}
                  </h3>
                  {(attempted || result) && (
                    <Badge
                      tone={
                        states[i] === 'verified_success' ? 'accent' : 'neutral'
                      }
                    >
                      {states[i] === 'pending' && uncertain
                        ? 'Awaiting status'
                        : stateLabels[states[i] ?? 'pending']}
                    </Badge>
                  )}
                </div>
                <p className="muted small">
                  {operation.feature_type === 'extrude' ? 'Extrude' : 'Fillet'}{' '}
                  · position {operation.position}
                </p>
                <dl
                  className="context-list modify-change"
                  data-outcome={outcomeOf(states[i], uncertain, !!result)}
                >
                  <div>
                    <dt>{operation.field}</dt>
                    <dd>
                      <span>{operation.current}</span>
                      <span aria-hidden="true"> → </span>
                      <span className="sr-only"> changes to </span>
                      <strong>{operation.proposed}</strong>
                    </dd>
                  </div>
                </dl>
              </li>
            ))}
          </ol>
          {!attempted && !result && (
            <>
              <p className="muted small">
                Approval applies only to this exact ordered plan and inspected
                model state. The plan expires two minutes after creation.
                Geometry and engineering suitability are not certified.
              </p>
              {expired && (
                <p className="notice">
                  This plan expired. Prepare a fresh plan before approval.
                </p>
              )}
              <div className="action-bar">
                <Button
                  disabled={!!busy}
                  onClick={() =>
                    void run('cancelling', async (signal) => {
                      const final = await cancelPlan(preview, csrf, signal);
                      if (!signal.aborted) {
                        setResult(final);
                        setStates(final.operations);
                      }
                    })
                  }
                >
                  Cancel plan
                </Button>
                <Button
                  variant="primary"
                  disabled={!!busy || expired || attempted}
                  onClick={approveClick}
                >
                  Approve {total} {total === 1 ? 'change' : 'changes'}
                </Button>
              </div>
            </>
          )}
          {canCheck && (
            <div>
              <Button
                disabled={!!busy}
                onClick={() =>
                  void run('status', async (signal) => {
                    const final = await planStatus(preview, csrf, signal);
                    if (!signal.aborted) {
                      setResult(final);
                      setStates(final.operations);
                    }
                  })
                }
              >
                Check status
              </Button>
            </div>
          )}
          {(completed || (expired && !attempted)) && (
            <div>
              <Button disabled={!!busy} onClick={clearPlan}>
                Plan another change
              </Button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
