import { useEffect, useRef, useState } from 'react';
import { Button } from '@forge/design-system';

type Context = { documentId: string; workspaceId: string; elementId: string };
type Dimension = { value: number; unit: string };
type Brief = {
  width: Dimension;
  length: Dimension;
  thickness: Dimension;
  holes: unknown[];
};
type Preview = {
  proposal_id: string;
  digest: string;
  brief: Brief;
  operations: string[];
};
const operationLabels: Record<string, string> = {
  CREATE_SKETCH_RECT: 'Top-plane rectangle sketch',
  CREATE_SKETCH_CIRCLE: 'Top-plane circle sketch',
  EXTRUDE_NEW: 'New-body extrusion',
};
const object = (x: unknown): x is Record<string, unknown> =>
  typeof x === 'object' && x !== null && !Array.isArray(x);
function brief(x: unknown): Brief {
  if (
    !object(x) ||
    x.kind !== 'rect_plate_with_through_holes' ||
    !Array.isArray(x.holes) ||
    x.holes.length > 4
  )
    throw Error('invalid');
  for (const key of ['width', 'length', 'thickness']) {
    const d = x[key];
    if (
      !object(d) ||
      typeof d.value !== 'number' ||
      !Number.isFinite(d.value) ||
      d.value <= 0 ||
      !['mm', 'cm', 'm', 'in'].includes(String(d.unit))
    )
      throw Error('invalid');
  }
  return x as unknown as Brief;
}
export function Creation({
  context,
  csrf,
}: {
  context: Context;
  csrf: string;
}) {
  const [text, setText] = useState('');
  const [design, setDesign] = useState<Brief | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState('');
  const used = useRef(false);
  const controller = useRef(new AbortController());
  useEffect(() => {
    const active = new AbortController();
    controller.current = active;
    return () => active.abort();
  }, []);
  async function post(path: string, body: unknown): Promise<unknown> {
    const response = await fetch(path, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify(body),
      signal: controller.current.signal,
    });
    const content = await response.text();
    if (content.length > 65536) throw Error('invalid');
    if (!response.ok)
      throw Error(response.status === 403 ? 'disabled' : 'unavailable');
    return JSON.parse(content) as unknown;
  }
  async function action(run: () => Promise<void>, approval = false) {
    if (busy || (approval && used.current)) return;
    if (approval) {
      used.current = true;
      setSubmitted(true);
    }
    setBusy(true);
    setMessage('');
    try {
      await run();
    } catch {
      if (!controller.current.signal.aborted)
        setMessage(
          approval
            ? 'Completion is unconfirmed. Do not retry. Inspect creation status and CAD; the server retains its write fence when uncertain.'
            : 'Creation is unavailable. This slice requires an empty Part Studio and supports a Top-plane profile with an additive blind extrusion. Cuts and face references are not enabled.',
        );
    } finally {
      if (!controller.current.signal.aborted) setBusy(false);
    }
  }
  const shown = preview?.brief ?? design;
  return (
    <section aria-label="Create editable CAD" className="notice">
      <h2>Create in an empty Part Studio</h2>
      <p>
        Top-plane rectangle or circle and additive blind Extrude. Cuts and face
        references await provider contract validation. CAD writes require this
        environment’s write flag and your explicit approval.
      </p>
      <label>
        Creation request
        <textarea
          value={text}
          maxLength={1024}
          disabled={busy || preview !== null}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      <Button
        disabled={busy || !text.trim() || preview !== null}
        onClick={() => {
          void action(async () => {
            const result = await post('/api/create/interpret', {
              request: text,
            });
            if (!object(result)) throw Error('invalid');
            if (result.status === 'ready') {
              setDesign(brief(result.brief));
              setMessage(
                'Review the normalized dimensions before preparing approval.',
              );
            } else if (result.status === 'needs_clarification') {
              setDesign(null);
              setMessage(
                'More design information is needed. Specify dimensions, units, and hole count and position.',
              );
            } else {
              setDesign(null);
              setMessage(
                'That request is unsupported or invalid. No CAD changed.',
              );
            }
          });
        }}
      >
        Interpret creation request
      </Button>
      {design && shown && (
        <>
          <p>
            Width {shown.width.value} {shown.width.unit}; length{' '}
            {shown.length.value} {shown.length.unit}; thickness{' '}
            {shown.thickness.value} {shown.thickness.unit}; holes{' '}
            {shown.holes.length}.
          </p>
          <Button
            disabled={busy || preview !== null || design.holes.length > 0}
            onClick={() => {
              void action(async () => {
                const result = await post('/api/create/plan', {
                  context,
                  brief: design,
                });
                if (
                  !object(result) ||
                  typeof result.proposal_id !== 'string' ||
                  !/^[A-Za-z0-9_-]{43}$/.test(result.proposal_id) ||
                  typeof result.digest !== 'string' ||
                  !/^[a-f0-9]{64}$/.test(result.digest) ||
                  !object(result.plan) ||
                  !Array.isArray(result.plan.steps) ||
                  result.plan.steps.length < 1 ||
                  result.plan.steps.length > 64
                )
                  throw Error('invalid');
                const operations = result.plan.steps.map((step: unknown) => {
                  if (
                    !object(step) ||
                    !object(step.op) ||
                    ![
                      'CREATE_SKETCH_RECT',
                      'CREATE_SKETCH_CIRCLE',
                      'EXTRUDE_NEW',
                    ].includes(String(step.op.operation))
                  )
                    throw Error('invalid');
                  return String(step.op.operation);
                });
                setPreview({
                  proposal_id: result.proposal_id,
                  digest: result.digest,
                  brief: brief(result.brief),
                  operations,
                });
                used.current = false;
                setSubmitted(false);
                setConfirmed(false);
              });
            }}
          >
            Prepare creation preview
          </Button>
        </>
      )}
      {preview && (
        <>
          <ol>
            {preview.operations.map((operation, i) => (
              <li key={i}>{operationLabels[operation]}</li>
            ))}
          </ol>
          <p>
            Native sketches and feature parameters remain editable. Sketches are
            not fully dimension-constrained. Approval expires after two minutes.
          </p>
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy || submitted}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            I confirm the displayed dimensions and ordered creation plan for
            this disposable empty Part Studio.
          </label>
          <Button
            disabled={busy || !confirmed || submitted}
            onClick={() => {
              void action(async () => {
                const result = await post(
                  `/api/create/plans/${preview.proposal_id}/approve`,
                  { digest: preview.digest, brief_confirmed: true },
                );
                if (
                  !object(result) ||
                  typeof result.state !== 'string' ||
                  ![
                    'verified_success',
                    'execution_uncertain',
                    'rejected',
                    'rejected_stale',
                  ].includes(result.state)
                )
                  throw Error('invalid');
                setMessage(
                  result.state === 'verified_success'
                    ? 'Creation verified by fresh provider evidence. Refresh CAD to inspect the editable feature tree.'
                    : 'Creation did not complete. Stop and inspect CAD. Do not retry an uncertain operation.',
                );
              }, true);
            }}
          >
            Approve creation once
          </Button>
          <Button
            disabled={busy || submitted}
            onClick={() => {
              void action(async () => {
                await post(
                  `/api/create/plans/${preview.proposal_id}/cancel`,
                  {},
                );
                setPreview(null);
                setMessage('Creation cancelled. No write was requested.');
              });
            }}
          >
            Cancel creation
          </Button>
        </>
      )}
      <p role="status" aria-live="polite">
        {busy ? 'Working…' : message}
      </p>
    </section>
  );
}
