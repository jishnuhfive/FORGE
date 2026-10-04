import { Badge, Button, Card, Panel } from '@forge/design-system';
import { Box, Layers3 } from 'lucide-react';

export function DesignPlan({
  onApprove,
  onRevise,
  onCancel,
}: {
  onApprove: () => void;
  onRevise: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="feature">
      <div className="section-kicker">
        <span>02 / REVIEW</span>
        <Badge tone="accent">Mock proposed plan</Badge>
      </div>
      <div className="feature-heading">
        <h1>A plan before a part</h1>
        <p>
          Review the architecture, operations and limits before previewing a
          build.
        </p>
      </div>
      <Card className="architecture-card">
        <Layers3 size={22} aria-hidden="true" />
        <div>
          <span className="eyebrow">Design architecture</span>
          <h2>Belt-driven rail carriage</h2>
          <p>
            Two parallel 8 mm rails guide a PETG carriage. A NEMA 17 drives a
            GT2 belt between end supports.
          </p>
        </div>
      </Card>
      <Panel title="Parts to create">
        <div className="parts-grid">
          {['Carriage', 'Motor mount', 'Rail support', 'End support'].map(
            (part, index) => (
              <div key={part}>
                <Box size={17} aria-hidden="true" />
                <strong>{part}</strong>
                <span className="mono muted">0{index + 1}</span>
              </div>
            ),
          )}
        </div>
      </Panel>
      <Panel title="CAD operations">
        <ol className="compact-list">
          <li>Sketch constrained mounting profiles</li>
          <li>Extrude the carriage and support bodies</li>
          <li>Add rail bores and M4 mounting holes</li>
          <li>Place components in a sample assembly</li>
        </ol>
      </Panel>
      <Panel title="Validation checks">
        <div className="chip-list">
          {[
            'Travel ≥ 400 mm',
            'Printer fit',
            'Required inventory',
            'Basic clearance',
            'Assembly completeness',
          ].map((check) => (
            <Badge key={check}>{check}</Badge>
          ))}
        </div>
      </Panel>
      <Panel title="Assumptions & risks">
        <ul className="compact-list">
          <li>Horizontal operation; 500 mm rails assumed.</li>
          <li>Bearing model and belt profile need confirmation.</li>
          <li>Strength, dynamics and load safety are unverified.</li>
        </ul>
      </Panel>
      <p className="local-notice">
        Approval advances a local development preview. It authorizes no real
        operation and modifies no CAD.
      </p>
      <div className="action-bar">
        <Button variant="primary" onClick={onApprove}>
          Approve and Build<span className="button-note">preview</span>
        </Button>
        <Button onClick={onRevise}>Revise</Button>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
