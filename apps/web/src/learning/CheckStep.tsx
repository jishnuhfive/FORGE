import { useEffect, useId, useRef, useState } from 'react';
import type { Dispatch } from 'react';
import { Button, StatusBadge } from '@forge/design-system';
import { ChevronRight } from 'lucide-react';
import { useAuth } from '../auth/context';
import { useOnshapeContext } from '../onshape/store';
import { CheckError, checkErrors, checkStep } from './check';
import type { RequirementResult, Status, StepCheck } from './check';
import type { LearningAction } from './session';

const tone = {
  PASS: 'pass',
  FAIL: 'fail',
  WARNING: 'warning',
  UNVERIFIED: 'unverified',
} as const;
const label: Record<Status, string> = {
  PASS: 'Verified',
  FAIL: 'Not yet',
  WARNING: 'Worth a look',
  UNVERIFIED: 'Can’t verify',
};
const headline = {
  verified: 'Forge verified what it can read for this step.',
  not_met: 'Forge can see something this step still needs.',
  unverified: 'Forge can’t fully verify this step yet.',
} as const;
type State =
  | { phase: 'idle' }
  | { phase: 'checking' }
  | { phase: 'done'; result: StepCheck }
  | { phase: 'error'; code: keyof typeof checkErrors };

function Findings({
  title,
  items,
}: {
  title: string;
  items: RequirementResult[];
}) {
  if (items.length === 0) return null;
  return (
    <section className="check-findings" aria-label={title}>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item.requirement_id}>
            <StatusBadge
              status={tone[item.outcome.status]}
              label={label[item.outcome.status]}
            />
            <span>
              <span className="check-label">{item.description}</span>
              {' — '}
              {item.outcome.finding}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function CheckStep({
  stepId,
  dispatch,
}: {
  stepId: string;
  dispatch: Dispatch<LearningAction>;
}) {
  const auth = useAuth();
  const client = useOnshapeContext();
  const [state, setState] = useState<State>({ phase: 'idle' });
  const [open, setOpen] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const detail = useId();
  useEffect(
    () => () => {
      controller.current?.abort();
      window.clearTimeout(timer.current);
    },
    [],
  );
  const busy = state.phase === 'checking' || waiting;
  async function run() {
    if (busy) return;
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setState({ phase: 'checking' });
    setOpen(false);
    try {
      const result = await checkStep(
        client.context,
        auth?.me.csrf_token ?? null,
        stepId,
        current.signal,
      );
      if (current.signal.aborted) return;
      // Only the server's latest deterministic outcome sets Forge verification;
      // request errors say nothing about the model, so they change nothing.
      if (result.step_id === stepId)
        dispatch({
          type: 'check-result',
          stepId,
          outcome: result.outcome,
          findings: result.results.map((item) => ({
            requirementId: item.requirement_id,
            blocking: item.blocking,
            status: item.outcome.status,
            reason: item.outcome.reason,
            finding: item.outcome.finding,
          })),
        });
      setState({ phase: 'done', result });
    } catch (cause) {
      if (current.signal.aborted) return;
      const error =
        cause instanceof CheckError ? cause : new CheckError('unavailable');
      setState({ phase: 'error', code: error.code });
      if (error.code === 'cooldown' || error.code === 'running') {
        // One timed re-enable; never an automatic retry of the request.
        setWaiting(true);
        timer.current = window.setTimeout(
          () => setWaiting(false),
          error.retryAfter * 1000,
        );
      }
    }
  }
  const result = state.phase === 'done' ? state.result : null;
  const blocking = result?.results.filter((item) => item.blocking) ?? [];
  const other = result?.results.filter((item) => !item.blocking) ?? [];
  return (
    <section className="learning-check" aria-label="Check my step">
      <h2>Step check</h2>
      <p className="muted small">
        Forge reads your current model and checks only what it can prove. It
        never changes your model.
      </p>
      <Button
        tabIndex={0}
        variant="primary"
        className="check-action"
        aria-disabled={busy}
        onClick={() => void run()}
      >
        {result || state.phase === 'error' ? 'Check again' : 'Check my step'}
      </Button>
      <div role="status" aria-live="polite" aria-atomic="true">
        {state.phase === 'checking' && <p>Checking current model…</p>}
        {state.phase === 'error' && <p>{checkErrors[state.code]}</p>}
        {result && <p className="check-headline">{headline[result.outcome]}</p>}
      </div>
      {result && (
        <>
          <Findings title="What Forge found" items={blocking} />
          <Findings title="What Forge can’t verify" items={other} />
          {result.outcome === 'not_met' && (
            <p className="muted small">
              Stuck? Ask for help below. Hints open one level at a time.
            </p>
          )}
          {result.consistency === 'mismatch' && (
            <p className="muted small">
              Your model changed while it was being read. Check again.
            </p>
          )}
          <Button
            tabIndex={0}
            variant="ghost"
            className="glass-action"
            aria-expanded={open}
            aria-controls={open ? detail : undefined}
            onClick={() => setOpen((value) => !value)}
          >
            How Forge checked this
            <ChevronRight
              size={14}
              className={`disclosure-icon ${open ? 'is-open' : ''}`}
              aria-hidden="true"
            />
          </Button>
          {open && (
            <div id={detail} className="learning-reveal">
              <p>
                Forge read your Part Studio’s feature list and bodies at{' '}
                {new Date(result.captured_at).toLocaleTimeString()}. The rules
                are fixed and run on Forge’s server, with no AI involved. The
                separate reads are not guaranteed to match one instant.
              </p>
              <p>
                Evidence used:{' '}
                {[...new Set(result.results.flatMap((item) => item.evidence))]
                  .join(', ')
                  .replaceAll('none', 'nothing readable')}
                .
              </p>
              <p>
                Feature names are never used as proof, so you can name things
                however you like.
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
