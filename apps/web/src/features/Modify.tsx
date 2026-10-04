import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
} from '@forge/design-system';
import { MousePointer2 } from 'lucide-react';
import { useState } from 'react';
import { PromptComposer } from '../components/PromptComposer';
import type { SelectionState } from '../lib/types';

const selections: Record<SelectionState, { label: string; detail: string }> = {
  none: {
    label: 'No selection',
    detail:
      'Select a supported face or feature when Onshape integration is available.',
  },
  face: { label: '1 face selected', detail: 'Top face of Motor Bracket' },
  edges: {
    label: '2 edges selected',
    detail: 'Multiple selections · choose one supported face for this preview.',
  },
  ambiguous: {
    label: 'Ambiguous selection',
    detail:
      'The target is unclear. Select one specific face before applying a change.',
  },
  unsupported: {
    label: 'Selection unsupported',
    detail:
      'This sample entity cannot be modified. Choose a supported planar face.',
  },
  stale: {
    label: 'Selection changed / stale',
    detail:
      'The document context changed. Reselect the target and review a fresh proposal.',
  },
};
export function Modify({ preview = false }: { preview?: boolean }) {
  const [selection, setSelection] = useState<SelectionState>('none');
  const [request, setRequest] = useState('');
  const [applied, setApplied] = useState(false);
  const context = selections[selection];
  return (
    <div className="feature">
      <div className="section-kicker">
        <span>MODIFY WORKSPACE</span>
        <Badge>{preview ? 'Mock selection' : 'Integration planned'}</Badge>
      </div>
      <div className="feature-heading">
        <h1>Refine with intention.</h1>
        <p>
          Choose a part of your design, describe the change, and review its
          impact before applying.
        </p>
      </div>
      {preview && (
        <>
          <label className="field-label" htmlFor="selection-state">
            Preview selection
          </label>
          <select
            id="selection-state"
            className="input"
            value={selection}
            onChange={(event) => {
              const next = (Object.keys(selections) as SelectionState[]).find(
                (key) => key === event.target.value,
              );
              if (next) {
                setSelection(next);
                setRequest('');
                setApplied(false);
              }
            }}
          >
            {Object.entries(selections).map(([key, value]) => (
              <option key={key} value={key}>
                {value.label}
              </option>
            ))}
          </select>
        </>
      )}
      <Card className="selection-card">
        <MousePointer2 size={19} aria-hidden="true" />
        <div>
          <strong>{context.label}</strong>
          <p>{context.detail}</p>
        </div>
      </Card>
      {['ambiguous', 'unsupported', 'stale', 'edges'].includes(selection) && (
        <ErrorState title={context.label} description={context.detail} />
      )}
      {selection === 'none' && (
        <EmptyState
          title="A precise change starts with a selection"
          description={
            preview
              ? 'Choose a sample selection above to explore a modification proposal.'
              : 'Onshape is not connected. Selection and modification will be available in a future phase.'
          }
        />
      )}
      <PromptComposer
        label="Modification prompt"
        placeholder="What would you like to change? e.g. Make this 5 mm thicker."
        context={selection === 'face' ? context.detail : context.label}
        disabled={selection !== 'face'}
        onSubmit={(text) => {
          setRequest(text);
          setApplied(false);
        }}
      />
      {request && selection === 'face' && (
        <Card className="modification-preview">
          <div className="row-between">
            <h2>Modification preview</h2>
            <Badge tone="accent">Local mock</Badge>
          </div>
          <dl className="context-list">
            <div>
              <dt>Selected object</dt>
              <dd>{context.detail}</dd>
            </div>
            <div>
              <dt>Your request</dt>
              <dd>{request}</dd>
            </div>
            <div>
              <dt>Current thickness</dt>
              <dd>4 mm · sample</dd>
            </div>
            <div>
              <dt>Proposed thickness</dt>
              <dd>9 mm · sample</dd>
            </div>
            <div>
              <dt>Affected features</dt>
              <dd>Base extrusion · mounting holes</dd>
            </div>
          </dl>
          <p className="muted small">
            Fixed example for “Make this 5 mm thicker.” Your text is not
            interpreted by AI.
          </p>
          <div className="action-bar">
            <Button
              variant="primary"
              disabled={applied}
              onClick={() => setApplied(true)}
            >
              Apply<span className="button-note">preview</span>
            </Button>
            <Button
              onClick={() => {
                setRequest('');
                setApplied(false);
              }}
            >
              Cancel
            </Button>
          </div>
          {applied && (
            <p role="status" className="notice">
              Local preview accepted. No CAD was modified.
            </p>
          )}
        </Card>
      )}
      <p className="local-notice">
        {preview
          ? 'Sample context and proposed values only. No real CAD writes occur.'
          : 'No live Onshape connection or CAD operations exist yet.'}
      </p>
    </div>
  );
}
