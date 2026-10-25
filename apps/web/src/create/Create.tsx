import { useEffect, useId, useRef, useState } from 'react';
import { Badge, Button } from '@forge/design-system';
import { ModifyError, messages } from '../modify/api';
import type { ErrorCode, OperationState } from '../modify/api';
import type { OnshapeClientContext } from '../onshape/model';
import {
  approveCreation,
  clarifyLabels,
  creationStatus,
  rejectionMessages,
  requestCreation,
} from './api';
import type {
  Brief,
  CreationProposal,
  CreationResponse,
  CreationResult,
  Length,
  PlanStep,
} from './api';

const baseLabels = {
  define_base_profile: 'Create base rectangle sketch',
  form_base_body: 'Extrude base body',
  define_cut_profile: 'Create hole sketch',
  remove_material: 'Remove material',
} as const;
/** Client-owned step names; repeated intents are numbered once there are several. */
function stepLabel(steps: PlanStep[], index: number): string {
  const step = steps[index];
  if (!step) return '';
  const same = steps.filter((s) => s.intent === step.intent);
  return same.length > 1
    ? `${baseLabels[step.intent]} ${same.indexOf(step) + 1}`
    : baseLabels[step.intent];
}
const stateLabels: Record<OperationState, string> = {
  pending: 'Not started',
  checking: 'Checking…',
  executing: 'Building…',
  verifying: 'Verifying…',
  verified_success: 'Verified',
  rejected_stale: 'Model changed',
  write_failed: 'Not applied',
  execution_uncertain: 'Uncertain',
  skipped: 'Not attempted',
};
const length = (l: Length) => `${Number(l.value.toFixed(4))} ${l.unit}`;

type Stage =
  | { name: 'idle' }
  | { name: 'interpreting' }
  | {
      name: 'clarify';
      response: Extract<CreationResponse, { status: 'needs_clarification' }>;
    }
  | { name: 'unsupported'; message: string }
  | { name: 'review'; proposal: CreationProposal; request: string }
  | { name: 'executing'; proposal: CreationProposal; request: string }
  | {
      name: 'finished';
      proposal: CreationProposal;
      request: string;
      result: CreationResult | null;
    };
const stageLabel: Record<Stage['name'], string> = {
  idle: 'Describe a part',
  interpreting: 'Interpreting',
  clarify: 'Needs clarification',
  unsupported: 'Unsupported',
  review: 'Ready for review',
  executing: 'Approved · building',
  finished: 'Finished',
};

export function Create({
  context,
  csrf,
  onBusyChange,
}: {
  context: OnshapeClientContext;
  csrf: string;
  onBusyChange?: (busy: boolean) => void;
}) {
  const [stage, setStage] = useState<Stage>({ name: 'idle' });
  const [text, setText] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [code, setCode] = useState<ErrorCode | null>(null);
  const [busyStatus, setBusyStatus] = useState(false);
  const [expired, setExpired] = useState(false);
  const id = useId();
  const controller = useRef<AbortController | null>(null);
  const approvalSent = useRef(false);
  const pending = useRef(false);
  useEffect(() => () => controller.current?.abort(), []);
  const busy = stage.name === 'interpreting' || stage.name === 'executing';
  useEffect(() => {
    onBusyChange?.(busy);
    return () => onBusyChange?.(false);
  }, [busy, onBusyChange]);
  const proposal =
    stage.name === 'review' ||
    stage.name === 'executing' ||
    stage.name === 'finished'
      ? stage.proposal
      : null;
  const reviewing = stage.name === 'review';
  useEffect(() => {
    if (!proposal || !reviewing) return;
    const timer = window.setTimeout(
      () => setExpired(true),
      Math.max(0, proposal.expires_at * 1000 - Date.now()),
    );
    return () => window.clearTimeout(timer);
  }, [proposal, reviewing]);

  function begin(): AbortController | null {
    if (pending.current) return null;
    pending.current = true;
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setCode(null);
    return c;
  }
  function submit() {
    const request = text.trim();
    if (!request || stage.name === 'interpreting') return;
    const c = begin();
    if (!c) return;
    setStage({ name: 'interpreting' });
    const timer = window.setTimeout(() => c.abort('timeout'), 60000);
    void requestCreation(context, request, csrf, c.signal)
      .then((response) => {
        if (c.signal.aborted) return;
        setConfirmed(false);
        setExpired(
          response.status === 'ready' &&
            Date.now() >= response.expires_at * 1000,
        );
        approvalSent.current = false;
        if (response.status === 'ready')
          setStage({ name: 'review', proposal: response, request });
        else if (response.status === 'needs_clarification')
          setStage({ name: 'clarify', response });
        else
          setStage({
            name: 'unsupported',
            message:
              response.status === 'unsupported'
                ? response.message
                : rejectionMessages[response.code],
          });
      })
      .catch((cause: unknown) => {
        if (c.signal.aborted && c.signal.reason !== 'timeout') return;
        setStage({ name: 'idle' });
        setCode(
          c.signal.reason === 'timeout'
            ? 'timeout'
            : cause instanceof ModifyError
              ? cause.code
              : 'invalid_request',
        );
      })
      .finally(() => {
        window.clearTimeout(timer);
        if (!c.signal.aborted || c.signal.reason === 'timeout')
          pending.current = false;
      });
  }
  function approve() {
    if (stage.name !== 'review' || !confirmed || approvalSent.current) return;
    if (Date.now() >= stage.proposal.expires_at * 1000) {
      setExpired(true);
      setCode('proposal_expired');
      return;
    }
    const { proposal, request } = stage;
    const c = begin();
    if (!c) return;
    // Consumed before any async work: an approval is never sent twice.
    approvalSent.current = true;
    setStage({ name: 'executing', proposal, request });
    const timer = window.setTimeout(() => c.abort('timeout'), 120000);
    void approveCreation(proposal, csrf, c.signal)
      .then((result) => {
        if (!c.signal.aborted)
          setStage({ name: 'finished', proposal, request, result });
      })
      .catch((cause: unknown) => {
        if (c.signal.aborted && c.signal.reason !== 'timeout') return;
        setCode(
          cause instanceof ModifyError ? cause.code : 'execution_uncertain',
        );
        setStage({ name: 'finished', proposal, request, result: null });
      })
      .finally(() => {
        window.clearTimeout(timer);
        if (!c.signal.aborted || c.signal.reason === 'timeout')
          pending.current = false;
      });
  }
  function checkStatus() {
    if (stage.name !== 'finished' || busyStatus || pending.current) return;
    const { proposal, request } = stage;
    const c = begin();
    if (!c) return;
    setBusyStatus(true);
    const timer = window.setTimeout(() => c.abort('timeout'), 35000);
    void creationStatus(proposal, csrf, c.signal)
      .then((result) => {
        if (!c.signal.aborted) {
          setStage({ name: 'finished', proposal, request, result });
          setCode(null);
        }
      })
      .catch((cause: unknown) => {
        if (c.signal.aborted && c.signal.reason !== 'timeout') return;
        setCode(cause instanceof ModifyError ? cause.code : 'invalid_request');
      })
      .finally(() => {
        window.clearTimeout(timer);
        pending.current = false;
        setBusyStatus(false);
      });
  }
  function reset(keepText: boolean) {
    if (stage.name === 'executing' || pending.current) return;
    if (!keepText) setText('');
    setStage({ name: 'idle' });
    setConfirmed(false);
    setExpired(false);
    setCode(null);
    approvalSent.current = false;
  }

  const result = stage.name === 'finished' ? stage.result : null;
  const verifiedAll =
    result?.state === 'verified_success' &&
    result.steps.every((s) => s === 'verified_success');
  const inFlight =
    result !== null &&
    ['pending', 'claimed', 'verifying'].includes(result.state);
  const showForm = ['idle', 'interpreting', 'clarify', 'unsupported'].includes(
    stage.name,
  );
  return (
    <div className="feature create-feature">
      <div className="feature-heading">
        <h1>Create a part</h1>
        <p>
          Describe the part. Forge writes a brief and a feature plan for you to
          review before anything is built.
        </p>
      </div>
      <div className="create-stage" role="status" aria-live="polite">
        <Badge tone={stage.name === 'review' ? 'accent' : 'neutral'}>
          {stageLabel[stage.name]}
        </Badge>
        {stage.name === 'interpreting' && (
          <span className="muted small">Reading your request…</span>
        )}
      </div>
      {showForm && (
        <form
          className="create-form"
          aria-busy={stage.name === 'interpreting'}
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <label className="field-label" htmlFor={`${id}-request`}>
            Part request
          </label>
          <textarea
            id={`${id}-request`}
            className="textarea"
            rows={3}
            maxLength={1000}
            value={text}
            disabled={stage.name === 'interpreting'}
            placeholder="Make a 60 by 40 by 10 mm plate."
            aria-describedby={`${id}-hint`}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === 'Enter' &&
                !event.shiftKey &&
                !event.nativeEvent.isComposing
              ) {
                event.preventDefault();
                submit();
              }
            }}
          />
          <p id={`${id}-hint`} className="muted small">
            Include every dimension with units. Enter prepares a brief;
            Shift+Enter adds a line. Nothing is built yet.
          </p>
          <div>
            <Button
              type="submit"
              variant="primary"
              disabled={stage.name === 'interpreting' || !text.trim()}
            >
              Prepare brief
            </Button>
          </div>
        </form>
      )}
      {stage.name === 'clarify' && (
        <section className="create-block" aria-label="Clarification needed">
          <h2>Forge needs a bit more</h2>
          <p className="muted small">
            Add the missing details to your request above and prepare it again.
          </p>
          <ul className="compact-list">
            {stage.response.fields.map((field, i) => (
              <li key={field}>
                <strong>{clarifyLabels[field]}</strong>
                <span className="muted"> · {stage.response.questions[i]}</span>
              </li>
            ))}
          </ul>
          <p className="muted small">Nothing was built.</p>
        </section>
      )}
      {stage.name === 'unsupported' && (
        <section className="create-block" aria-label="Unsupported request">
          <h2>Forge can’t build that yet</h2>
          <p>{stage.message}</p>
          <p className="muted small">
            Today Forge builds plain rectangular plates (sketch and extrude).
            Holes and cuts are not enabled yet. Nothing was built.
          </p>
        </section>
      )}
      {proposal && (
        <>
          <p className="create-request">
            <span className="eyebrow">Your request</span>
            <q>{(stage as { request: string }).request}</q>
          </p>
          <BriefReview
            brief={proposal.brief}
            confirmed={confirmed}
            locked={stage.name !== 'review'}
            onConfirm={setConfirmed}
          />
          <FeaturePlan
            proposal={proposal}
            states={
              result?.steps ?? proposal.steps.map(() => 'pending' as const)
            }
            showState={stage.name !== 'review'}
            executing={stage.name === 'executing'}
          />
          {stage.name === 'review' && proposal.limitations.length > 0 && (
            <ul className="muted small">
              {proposal.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          )}
        </>
      )}
      {stage.name === 'review' && (
        <div className="create-approve">
          {expired && (
            <p className="notice" role="alert">
              This plan expired. Prepare a fresh brief before approval.
            </p>
          )}
          {!confirmed && (
            <p className="muted small" id={`${id}-need`}>
              Confirm the engineering brief above to enable the build.
            </p>
          )}
          <p className="muted small">
            Approval applies only to this exact brief and plan. Forge checks
            each step in Onshape and reports only what it verifies. Geometry and
            engineering suitability are not certified.
          </p>
          <div className="action-bar">
            <Button onClick={() => reset(true)}>Edit request</Button>
            <Button
              variant="primary"
              disabled={!confirmed || expired}
              aria-describedby={confirmed ? undefined : `${id}-need`}
              onClick={approve}
            >
              Approve and build {stage.proposal.steps.length} steps
            </Button>
          </div>
        </div>
      )}
      <div role="status" aria-live="polite" aria-atomic="true">
        {stage.name === 'executing' && (
          <p>
            Building and verifying in Onshape… Forge reports success only after
            every step is verified.
          </p>
        )}
        {verifiedAll && (
          <section className="create-block create-result" aria-label="Result">
            <h2>Verified</h2>
            <p>
              {result.steps.length} of {result.steps.length} steps verified in
              Onshape.
            </p>
          </section>
        )}
        {stage.name === 'finished' && !verifiedAll && (
          <section className="create-block create-result" aria-label="Result">
            <h2>
              {result?.state === 'rejected_stale'
                ? 'Model changed'
                : result?.state === 'write_failed' ||
                    result?.state === 'partial_failure'
                  ? 'Build stopped'
                  : inFlight
                    ? 'Still being checked'
                    : 'Forge could not confirm the result'}
            </h2>
            <p>
              {result
                ? `${result.steps.filter((s) => s === 'verified_success').length} of ${result.steps.length} steps verified.`
                : 'No step is confirmed.'}{' '}
              {result?.state === 'rejected_stale'
                ? 'The model changed before building; nothing was applied. Prepare a fresh brief.'
                : result?.state === 'partial_failure'
                  ? 'Earlier verified steps remain in the Part Studio. Remaining steps were not attempted.'
                  : result?.state === 'write_failed'
                    ? 'No steps were applied.'
                    : 'Inspect the Part Studio in Onshape before trying again. Forge will not retry this approval.'}
            </p>
            {code && code !== 'execution_uncertain' && (
              <p className="notice">{messages[code]}</p>
            )}
          </section>
        )}
        {code && stage.name !== 'finished' && (
          <p className="notice">{messages[code]}</p>
        )}
      </div>
      {stage.name === 'finished' && (
        <div className="action-bar">
          {(!result || inFlight || result.state === 'execution_uncertain') && (
            <Button disabled={busyStatus} onClick={checkStatus}>
              Check status
            </Button>
          )}
          {(verifiedAll ||
            (result &&
              !inFlight &&
              result.state !== 'execution_uncertain')) && (
            <Button onClick={() => reset(false)}>Create another part</Button>
          )}
        </div>
      )}
      {verifiedAll && proposal && <LearnBuild proposal={proposal} />}
    </div>
  );
}

function BriefReview({
  brief,
  confirmed,
  locked,
  onConfirm,
}: {
  brief: Brief;
  confirmed: boolean;
  locked: boolean;
  onConfirm: (value: boolean) => void;
}) {
  const id = useId();
  return (
    <section className="create-block create-brief" aria-labelledby={`${id}-h`}>
      <div className="create-block-heading">
        <h2 id={`${id}-h`}>Engineering brief</h2>
        <Badge tone={confirmed ? 'accent' : 'neutral'}>
          {confirmed ? 'Reviewed' : 'Needs your review'}
        </Badge>
      </div>
      <dl className="context-list">
        <div>
          <dt>Part</dt>
          <dd>Rectangular plate with through-holes</dd>
        </div>
        <div>
          <dt>Width</dt>
          <dd>{length(brief.width)}</dd>
        </div>
        <div>
          <dt>Length (depth)</dt>
          <dd>{length(brief.length)}</dd>
        </div>
        <div>
          <dt>Thickness</dt>
          <dd>{length(brief.thickness)}</dd>
        </div>
        <div>
          <dt>Holes</dt>
          <dd>
            {brief.holes.length === 0
              ? 'None'
              : `${brief.holes.length} through-${brief.holes.length === 1 ? 'hole' : 'holes'}`}
          </dd>
        </div>
      </dl>
      {brief.holes.length > 0 && (
        <ol className="create-holes" aria-label="Holes">
          {brief.holes.map((hole, i) => (
            <li key={i}>
              <strong>Hole {i + 1}</strong>
              <span>
                Ø {length(hole.diameter)} ·{' '}
                {hole.center_x.value === 0 && hole.center_y.value === 0
                  ? 'centered'
                  : `X ${length(hole.center_x)}, Y ${length(hole.center_y)} from center`}
              </span>
            </li>
          ))}
        </ol>
      )}
      <label className="create-confirm">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={locked}
          onChange={(event) => onConfirm(event.target.checked)}
        />
        <span>
          I checked these dimensions and units against my request.
          <span className="muted small create-confirm-note">
            Forge cannot yet prove the AI read your numbers correctly, so you
            confirm them.
          </span>
        </span>
      </label>
    </section>
  );
}

function FeaturePlan({
  proposal,
  states,
  showState,
  executing,
}: {
  proposal: CreationProposal;
  states: OperationState[];
  showState: boolean;
  executing: boolean;
}) {
  const id = useId();
  return (
    <section className="create-block" aria-labelledby={`${id}-h`}>
      <div className="create-block-heading">
        <h2 id={`${id}-h`}>Feature plan</h2>
        <Badge>Parametric</Badge>
      </div>
      <p className="muted small">
        Planned as ordinary sketches and features, built in this order. Each
        step stays editable in the Onshape feature tree.
      </p>
      <ol className="create-steps" aria-label="Planned features">
        {proposal.steps.map((step, i) => {
          const state = states[i] ?? 'pending';
          const explanation = proposal.explanations[i];
          return (
            <li key={step.id} data-state={showState ? state : undefined}>
              <span className="create-step-index" aria-hidden="true">
                {i + 1}
              </span>
              <div className="create-step-body">
                <div className="create-step-heading">
                  <h3>{stepLabel(proposal.steps, i)}</h3>
                  {showState && (
                    <Badge
                      tone={state === 'verified_success' ? 'accent' : 'neutral'}
                    >
                      {executing ? 'Building…' : stateLabels[state]}
                    </Badge>
                  )}
                </div>
                <p className="mono small">{step.detail}</p>
                {explanation && (
                  <details className="create-why">
                    <summary>Why this step</summary>
                    <p>{explanation.text}</p>
                  </details>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/** Read-only walkthrough of the verified plan; it holds no execution authority. */
function LearnBuild({ proposal }: { proposal: CreationProposal }) {
  const [index, setIndex] = useState(0);
  const total = proposal.steps.length;
  const step = proposal.steps[index];
  const explanation = proposal.explanations[index];
  const id = useId();
  if (!step || !explanation) return null;
  return (
    <section className="create-block create-learn" aria-labelledby={`${id}-h`}>
      <div className="create-block-heading">
        <h2 id={`${id}-h`}>Learn how FORGE built this</h2>
        <Badge>Read-only</Badge>
      </div>
      <div aria-live="polite" className="create-learn-step">
        <span className="eyebrow">
          Step {index + 1} of {total}
        </span>
        <h3>{stepLabel(proposal.steps, index)}</h3>
        <dl className="context-list">
          <div>
            <dt>What it does</dt>
            <dd>{step.detail}</dd>
          </div>
          <div>
            <dt>Why it’s here</dt>
            <dd>{explanation.text}</dd>
          </div>
        </dl>
      </div>
      <div className="action-bar">
        <Button disabled={index === 0} onClick={() => setIndex(index - 1)}>
          Previous step
        </Button>
        <Button
          disabled={index === total - 1}
          onClick={() => setIndex(index + 1)}
        >
          Next step
        </Button>
      </div>
      {index === total - 1 && (
        <p className="muted small">
          Each step above was verified against the model. Learn explains the
          plan; it never changes your CAD.
        </p>
      )}
    </section>
  );
}
