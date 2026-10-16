import { Badge, Button, Card } from '@forge/design-system';
import { ArrowRight, PencilRuler } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../auth/context';
import { Analysis } from '../ai/Analysis';
import { PromptComposer } from '../components/PromptComposer';
import { MechanismDrawing } from '../components/MechanismDrawing';
import { useOnshapeContext } from '../onshape/store';
import { revisionId } from '../onshape/model';

export function Design({
  preview = false,
  onSubmit,
}: {
  preview?: boolean;
  onSubmit?: (text: string) => void;
}) {
  const [draft, setDraft] = useState('');
  const client = useOnshapeContext();
  const auth = useAuth();
  const contextLabel = client.context
    ? client.context.revision.kind === 'workspace'
      ? 'Onshape workspace context'
      : 'Onshape version context · messaging unverified'
    : client.status === 'STANDALONE'
      ? 'Not inside Onshape'
      : client.status === 'UNTRUSTED_ORIGIN'
        ? 'Onshape origin could not be verified'
        : client.status === 'EMBEDDED_CONTEXT_ERROR'
          ? 'Document context unavailable'
          : 'Waiting for document context';
  if (auth && !preview && client.status !== 'STANDALONE') {
    const context = client.context;
    const available =
      ['EMBEDDED_CONNECTED', 'EMBEDDED_INITIALIZING'].includes(client.status) &&
      context?.revision.kind === 'workspace' &&
      context.server === 'https://cad.onshape.com' &&
      (!context.elementType || context.elementType === 'partStudio') &&
      auth.me.connection === 'connected' &&
      auth.me.csrf_token &&
      !['stale', 'unavailable'].includes(client.selection.status);
    const selection =
      client.selection.status !== 'available'
        ? 'unknown'
        : client.selection.entities.length === 0
          ? 'none'
          : client.selection.entities[0]?.type === 'face'
            ? 'FACE'
            : client.selection.entities[0]?.type === 'edge'
              ? 'EDGE'
              : 'unknown';
    return (
      <div className="feature design-feature">
        <div className="section-kicker">
          <span>
            <PencilRuler size={14} aria-hidden="true" />
            DESIGN WORKSPACE
          </span>
          <Badge>Read-only AI</Badge>
        </div>
        <div className="feature-heading">
          <span className="eyebrow">Understand your current design</span>
          <h1>What do you want to engineer?</h1>
          <p>
            Ask Forge about this Part Studio, inspect the evidence, or explore a
            design approach. CAD changes are unavailable.
          </p>
        </div>
        <p className="small muted">{contextLabel}</p>
        {available && context && auth.me.csrf_token ? (
          <Analysis
            key={[
              context.documentId,
              context.revision.kind,
              revisionId(context),
              context.elementId,
              context.server,
              context.microversionId ?? '',
              auth.me.csrf_token,
            ].join(':')}
            context={context}
            csrf={auth.me.csrf_token}
            selection={selection}
          />
        ) : (
          <p role="status" className="notice">
            Open a current workspace Part Studio inside Onshape with a connected
            account to ask Forge.
          </p>
        )}
      </div>
    );
  }
  return (
    <div className="feature design-feature">
      <div className="section-kicker">
        <span>
          <PencilRuler size={14} aria-hidden="true" />
          DESIGN WORKSPACE
        </span>
        <Badge>{preview ? 'Mock preview' : 'Local design draft'}</Badge>
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
        context={preview ? 'Mock context · 1 face' : contextLabel}
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
          : 'Local draft only. Open Forge inside Onshape to use read-only AI.'}
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
