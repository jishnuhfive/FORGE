import { Badge, Button, ErrorState, ProgressStep } from '@forge/design-system';
import { useState } from 'react';
import type { RunStep } from '../lib/types';
import type { ProgressStatus } from '@forge/design-system';

export function AgentProgress({
  steps,
  initial = 'active',
  onReport,
}: {
  steps: RunStep[];
  initial?: ProgressStatus;
  onReport: () => void;
}) {
  const [state, setState] = useState<ProgressStatus>(initial);
  const statuses: ProgressStatus[] = [
    'pending',
    'active',
    'complete',
    'warning',
    'failed',
    'cancelled',
  ];
  const displayed = steps.map((step, index) => ({
    ...step,
    status:
      state === 'complete' || state === 'pending'
        ? state
        : index === 4
          ? state
          : step.status,
  }));
  if (state === 'failed' || state === 'cancelled')
    displayed.forEach((step, index) => {
      if (index > 4)
        step.status = state === 'cancelled' ? 'cancelled' : 'pending';
    });
  const completed = displayed.filter(
    (step) => step.status === 'complete',
  ).length;
  return (
    <div className="feature">
      <div className="section-kicker">
        <span>03 / BUILD PREVIEW</span>
        <Badge tone="accent">No agent executing</Badge>
      </div>
      <div className="feature-heading">
        <h1>Engineering in progress</h1>
        <p>
          Understandable actions and outcomes, with a clear record of each step.
        </p>
      </div>
      <label className="field-label" htmlFor="run-status">
        Preview run state
      </label>
      <select
        className="input"
        id="run-status"
        value={state}
        onChange={(event) => {
          const next = statuses.find((s) => s === event.target.value);
          if (next) setState(next);
        }}
      >
        {statuses.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
      <div className="run-summary" role="status">
        <strong>
          {state === 'active'
            ? 'Previewing motor mount step'
            : `Preview ${state}`}
        </strong>
        <span className="muted small">
          {completed} / {steps.length} sample steps complete
        </span>
      </div>
      <progress
        className="run-progress"
        aria-label="Sample run progress"
        max={steps.length}
        value={completed}
      />
      {state === 'failed' && (
        <ErrorState
          title="Motor mount step failed · preview"
          description="The sample feature could not be verified. No CAD operation was attempted."
        />
      )}
      {state === 'cancelled' && (
        <p className="local-notice" role="status">
          Preview cancelled. No CAD was changed.
        </p>
      )}
      <ol className="progress-list">
        {displayed.map((step, index) => (
          <ProgressStep key={step.id} number={index + 1} {...step} />
        ))}
      </ol>
      <div className="action-bar">
        {state === 'active' && (
          <Button onClick={() => setState('cancelled')}>Cancel preview</Button>
        )}
        {state === 'failed' && (
          <Button onClick={() => setState('active')}>Reset preview</Button>
        )}
        <Button variant="primary" onClick={onReport}>
          Open sample report
        </Button>
      </div>
      <p className="local-notice">
        Statuses are manually selected fixtures. They are not evidence of an
        executed agent run.
      </p>
    </div>
  );
}
