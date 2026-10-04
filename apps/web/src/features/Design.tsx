import { Badge, Button, Card } from '@forge/design-system';
import { ArrowRight, PencilRuler } from 'lucide-react';
import { useState } from 'react';
import { PromptComposer } from '../components/PromptComposer';
import { MechanismDrawing } from '../components/MechanismDrawing';

export function Design({
  preview = false,
  onSubmit,
}: {
  preview?: boolean;
  onSubmit?: (text: string) => void;
}) {
  const [draft, setDraft] = useState('');
  return (
    <div className="feature design-feature">
      <div className="section-kicker">
        <span>
          <PencilRuler size={14} aria-hidden="true" />
          DESIGN WORKSPACE
        </span>
        <Badge>{preview ? 'Mock preview' : 'Phase 1 · UI foundation'}</Badge>
      </div>
      <div className="design-intro">
        <MechanismDrawing />
        <span className="eyebrow">From function to form</span>
        <h1>What do you want to engineer?</h1>
        <p>
          Describe what your mechanism needs to accomplish. Forge will turn
          functional requirements into an engineering plan and editable Onshape
          CAD when live integration is available.
        </p>
      </div>
      <PromptComposer
        context={preview ? 'Mock context · 1 face' : undefined}
        label="Design prompt"
        placeholder="A camera slider with 400 mm travel, carrying a 0.30 kg camera…"
        onSubmit={(text) => {
          setDraft(text);
          onSubmit?.(text);
        }}
        showSuggestions
      />
      <p className="local-notice">
        {preview
          ? 'Development sample only. No AI runs and no CAD changes.'
          : 'Local draft only. AI and Onshape integration are not available yet.'}
      </p>
      {draft && (
        <Card className="draft-card">
          <span className="eyebrow">Your local draft</span>
          <p className="draft-text">{draft}</p>
          <p className="muted small">
            This text has not been sent to a service or converted into
            requirements.
          </p>
          <Button onClick={() => setDraft('')}>Dismiss draft</Button>
        </Card>
      )}
      <div className="workflow-overview">
        <span className="eyebrow">An engineering workflow you can review</span>
        <ol>
          <li>
            <span>01</span>
            <strong>Define</strong>
            <p>Capture requirements</p>
          </li>
          <li>
            <span>02</span>
            <strong>Review</strong>
            <p>Approve a clear plan</p>
          </li>
          <li>
            <span>03</span>
            <strong>Validate</strong>
            <p>See the evidence</p>
          </li>
        </ol>
      </div>
      {import.meta.env.DEV && !preview && (
        <a className="text-link preview-entry" href="#/lab">
          Explore the development preview
          <ArrowRight size={14} aria-hidden="true" />
        </a>
      )}
    </div>
  );
}
